"""Every write of the teacher's workspace. Limits are checked under a lock on the workspace,
so two requests at once can't pass a plan's limit."""

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.classroom import exams
from apps.classroom.exceptions import (
    AiExamQuotaReached,
    AiQuotaReached,
    InputRejected,
    PlanLimitReached,
    ProRequired,
    RegenerateLimitReached,
    ServiceUnavailable,
)
from apps.classroom.models import (
    AIGeneration,
    Assessment,
    AttendanceRecord,
    Classroom,
    Exam,
    ExamDraft,
    ExamPattern,
    ExamQuestion,
    LessonPlan,
    Mark,
    PaperDesign,
    ParentMessage,
    PresentationExport,
    SourceDocument,
    Student,
    TeacherProfile,
    UpgradeRequest,
)
from apps.classroom.selectors import (
    count_exams_in_progress,
    find_source_document,
    get_paper_design,
    get_workspace_usage,
    list_parent_emails,
)
from apps.classroom.tasks import generate_exam_draft_task, send_parent_message_task
from apps.integrations.ai.exam_provider import ExamAiUnavailable, list_topics, write_questions
from apps.integrations.ai.lesson_provider import LessonAiUnavailable, generate_lesson_content
from apps.integrations.pdf.text_extractor import (
    PdfReaderUnavailable,
    PdfTextError,
    read_pdf_pages,
)
from apps.tenancy.models import School

logger = logging.getLogger(__name__)

NAME_TAKEN = "You already have this class for this subject."
NUMBER_TAKEN = "Another student in this class has this ID."


def _lock_workspace(school):
    School.objects.select_for_update().get(pk=school.pk)


def _check_limit(limit, used, adding=1):
    if limit is not None and used + adding > limit:
        raise PlanLimitReached()


def _require_pro(access):
    if not access.limits.pro_features:
        raise ProRequired()


def delete_record(record):
    record.delete()


# --- Setup


@transaction.atomic
def complete_setup(school, user, *, subject, grade_levels):
    profile, _ = TeacherProfile.objects.update_or_create(
        user=user,
        defaults={"school": school, "subject": subject, "grade_levels": grade_levels},
    )
    return profile


# --- Classes and students


def _class_taken(school, name, subject, exclude=None):
    classes = Classroom.objects.filter(school=school, name__iexact=name, subject__iexact=subject)
    if exclude is not None:
        classes = classes.exclude(pk=exclude.pk)
    return classes.exists()


@transaction.atomic
def create_classroom(school, access, **fields):
    _lock_workspace(school)
    _check_limit(access.limits.classes, get_workspace_usage(school)["classes"])
    if _class_taken(school, fields["name"], fields.get("subject", "")):
        raise ValidationError({"name": NAME_TAKEN})
    return Classroom.objects.create(school=school, **fields)


def update_classroom(school, classroom, **fields):
    name = fields.get("name", classroom.name)
    subject = fields.get("subject", classroom.subject)
    if _class_taken(school, name, subject, exclude=classroom):
        raise ValidationError({"name": NAME_TAKEN})
    for field, value in fields.items():
        setattr(classroom, field, value)
    try:
        with transaction.atomic():
            classroom.save(update_fields=[*fields, "updated_at"])
    except IntegrityError as error:
        raise ValidationError({"name": NAME_TAKEN}) from error
    return classroom


@transaction.atomic
def add_students(school, access, classroom, rows):
    _lock_workspace(school)
    _check_limit(access.limits.students, get_workspace_usage(school)["students"], len(rows))
    numbers = [row.get("student_number", "") for row in rows]
    taken = set(
        Student.objects.filter(
            school=school, classroom=classroom, student_number__in=[n for n in numbers if n]
        ).values_list("student_number", flat=True)
    )
    if taken:
        raise ValidationError(
            {
                "students": [
                    {"student_number": [NUMBER_TAKEN]} if number in taken else {}
                    for number in numbers
                ]
            }
        )
    return Student.objects.bulk_create(
        [Student(school=school, classroom=classroom, **row) for row in rows]
    )


def update_student(student, **fields):
    number = fields.get("student_number")
    if (
        number
        and Student.objects.filter(
            school_id=student.school_id,
            classroom_id=student.classroom_id,
            student_number=number,
        )
        .exclude(pk=student.pk)
        .exists()
    ):
        raise ValidationError({"student_number": NUMBER_TAKEN})
    for field, value in fields.items():
        setattr(student, field, value)
    try:
        with transaction.atomic():
            student.save(update_fields=[*fields, "updated_at"])
    except IntegrityError as error:
        raise ValidationError({"student_number": NUMBER_TAKEN}) from error
    return student


# --- Attendance


def save_attendance(school, classroom, day, records):
    student_ids = {record["student"] for record in records}
    known = set(
        Student.objects.filter(school=school, classroom=classroom, id__in=student_ids).values_list(
            "id", flat=True
        )
    )
    if known != student_ids:
        raise ValidationError({"records": "Some students are not in this class."})

    AttendanceRecord.objects.bulk_create(
        [
            AttendanceRecord(
                school=school,
                classroom=classroom,
                student_id=record["student"],
                date=day,
                status=record["status"],
            )
            for record in records
        ],
        update_conflicts=True,
        unique_fields=["student", "date"],
        update_fields=["status", "updated_at"],
    )


# --- Lesson plans


def _check_plan_classroom(school, classroom):
    if classroom is not None and classroom.school_id != school.id:
        raise ValidationError({"classroom": "Class not found."})


@transaction.atomic
def create_lesson_plan(school, access, **fields):
    _lock_workspace(school)
    _check_plan_classroom(school, fields.get("classroom"))
    _check_limit(access.limits.lesson_plans, get_workspace_usage(school)["lesson_plans"])
    return LessonPlan.objects.create(school=school, **fields)


def update_lesson_plan(school, plan, **fields):
    _check_plan_classroom(school, fields.get("classroom"))
    for field, value in fields.items():
        setattr(plan, field, value)
    plan.save(update_fields=[*fields, "updated_at"])
    return plan


@transaction.atomic
def record_presentation_export(school, access, plan):
    _lock_workspace(school)
    _check_limit(
        access.limits.presentation_exports, get_workspace_usage(school)["presentation_exports"]
    )
    return PresentationExport.objects.create(school=school, lesson_plan=plan)


def _check_ai_allowance(school, access):
    usage = get_workspace_usage(school, ai_since=access.ai_since)
    if usage["ai_used"] >= access.limits.ai_lessons:
        raise AiQuotaReached()
    # No point making a draft that could never be saved.
    _check_limit(access.limits.lesson_plans, usage["lesson_plans"])


def generate_lesson_draft(school, access, *, topic, subject, grade, language, classroom=None):
    """Returns a draft for the teacher to read and edit. Nothing is saved but the count.

    Only the topic, subject and grade go to the AI provider, never any student data.
    """
    _check_plan_classroom(school, classroom)
    _check_ai_allowance(school, access)

    # Outside any transaction: the provider can take many seconds to answer.
    try:
        content = generate_lesson_content(
            topic=topic, subject=subject, grade=grade, language=language
        )
    except LessonAiUnavailable as error:
        raise ServiceUnavailable() from error

    with transaction.atomic():
        _lock_workspace(school)
        _check_ai_allowance(school, access)
        AIGeneration.objects.create(school=school, kind=AIGeneration.Kind.LESSON)
    return {
        **content,
        "classroom": classroom.pk if classroom else None,
        "subject": subject,
        "grade": grade,
    }


# --- Assessments and marks


def create_assessment(school, classroom, **fields):
    return Assessment.objects.create(school=school, classroom=classroom, **fields)


@transaction.atomic
def update_assessment(school, assessment, **fields):
    new_max = fields.get("max_marks")
    if (
        new_max is not None
        and Mark.objects.filter(school=school, assessment=assessment, value__gt=new_max).exists()
    ):
        raise ValidationError({"max_marks": "Some marks are higher than this."})
    for field, value in fields.items():
        setattr(assessment, field, value)
    assessment.save(update_fields=[*fields, "updated_at"])
    return assessment


@transaction.atomic
def save_marks(school, assessment, rows):
    """A blank value clears that student's mark."""
    student_ids = {row["student"] for row in rows}
    known = set(
        Student.objects.filter(
            school=school, classroom_id=assessment.classroom_id, id__in=student_ids
        ).values_list("id", flat=True)
    )
    if known != student_ids:
        raise ValidationError({"marks": "Some students are not in this class."})
    if any(row["value"] is not None and row["value"] > assessment.max_marks for row in rows):
        raise ValidationError({"marks": "A mark can't be higher than the maximum."})

    cleared = [row["student"] for row in rows if row["value"] is None]
    if cleared:
        Mark.objects.filter(school=school, assessment=assessment, student_id__in=cleared).delete()

    Mark.objects.bulk_create(
        [
            Mark(
                school=school,
                assessment=assessment,
                student_id=row["student"],
                value=row["value"],
            )
            for row in rows
            if row["value"] is not None
        ],
        update_conflicts=True,
        unique_fields=["assessment", "student"],
        update_fields=["value", "updated_at"],
    )


# --- Tests made from a PDF


def save_exam_source(school, *, upload):
    """Keeps only the text of the PDF, never the file. The same file again isn't read twice."""
    if upload.size > exams.MAX_PDF_BYTES:
        raise InputRejected("pdf_too_large", "This PDF is larger than 8 MB.")
    if not upload.name.lower().endswith(".pdf"):
        raise InputRejected("not_pdf", "This file is not a PDF.")

    data = upload.read()
    digest = hashlib.sha256(data).hexdigest()
    existing = find_source_document(school, digest)
    if existing is not None:
        # Kept for another day from now.
        existing.save(update_fields=["updated_at"])
        return existing

    try:
        pages = read_pdf_pages(data, max_pages=exams.MAX_PDF_PAGES)
    except PdfTextError as error:
        raise InputRejected(error.code, str(error)) from error
    except PdfReaderUnavailable as error:
        raise ServiceUnavailable() from error

    try:
        with transaction.atomic():
            return SourceDocument.objects.create(
                school=school,
                sha256=digest,
                filename=upload.name[:255],
                page_count=len(pages),
                pages=pages,
            )
    except IntegrityError:
        # The same file uploaded twice at once: the first one is kept.
        return find_source_document(school, digest)


def _stored_sections(sections):
    """Sections as JSON can hold them: marks become text, so no Decimal is lost."""
    return [{**section, "marks": str(section["marks"])} for section in sections]


PATTERN_NAME_TAKEN = "You already have a pattern with this name."


def _pattern_taken(school, name, exclude=None):
    patterns = ExamPattern.objects.filter(school=school, name__iexact=name)
    if exclude is not None:
        patterns = patterns.exclude(pk=exclude.pk)
    return patterns.exists()


@transaction.atomic
def create_exam_pattern(school, *, name, sections):
    _lock_workspace(school)
    if ExamPattern.objects.filter(school=school).count() >= exams.MAX_PATTERNS:
        raise ValidationError({"name": f"You can keep up to {exams.MAX_PATTERNS} patterns."})
    if _pattern_taken(school, name):
        raise ValidationError({"name": PATTERN_NAME_TAKEN})
    return ExamPattern.objects.create(school=school, name=name, sections=_stored_sections(sections))


def update_exam_pattern(school, pattern, **fields):
    if "name" in fields and _pattern_taken(school, fields["name"], exclude=pattern):
        raise ValidationError({"name": PATTERN_NAME_TAKEN})
    if "sections" in fields:
        fields["sections"] = _stored_sections(fields["sections"])
    for field, value in fields.items():
        setattr(pattern, field, value)
    try:
        with transaction.atomic():
            pattern.save(update_fields=[*fields, "updated_at"])
    except IntegrityError as error:
        raise ValidationError({"name": PATTERN_NAME_TAKEN}) from error
    return pattern


def _check_exam_allowance(school, access):
    """Tests still being written count too, so many at once can't pass the allowance."""
    used = get_workspace_usage(school, ai_since=access.ai_since)["ai_exams_used"]
    if used + count_exams_in_progress(school) >= access.limits.ai_exams:
        raise AiExamQuotaReached()


def start_exam_draft(
    school, access, *, document, page_from, page_to, sections, classroom=None, **details
):
    """Starts writing a test in the background, and returns the draft to wait on.

    `details` are the title, subject, grade and language. Only the chosen pages' text,
    the subject, grade and language go to the AI provider."""
    _check_plan_classroom(school, classroom)
    if page_to > document.page_count:
        raise ValidationError({"page_to": f"This PDF has {document.page_count} pages."})
    selected = exams.selected_pages(document.pages, page_from, page_to)
    if exams.content_length(selected) < exams.MIN_CONTENT_CHARS:
        raise InputRejected("too_little_text", "These pages have too little text for a test.")

    with transaction.atomic():
        _lock_workspace(school)
        _check_exam_allowance(school, access)
        draft = ExamDraft.objects.create(
            school=school,
            document=document,
            settings={
                **details,
                "classroom": classroom.pk if classroom else None,
                "page_from": page_from,
                "page_to": page_to,
                "sections": _stored_sections(sections),
            },
            requested=exams.total_questions(sections),
        )
        # The PDF's text is kept for as long as a draft may still need it.
        SourceDocument.objects.filter(pk=document.pk).update(updated_at=timezone.now())
        transaction.on_commit(
            lambda: generate_exam_draft_task.delay(school.id, draft.id), robust=True
        )
    return draft


def _about(settings):
    return {
        "subject": settings.get("subject", ""),
        "grade": settings.get("grade", ""),
        "language": settings["language"],
    }


def write_exam_draft(school_id, draft_id):
    """Runs in Celery. Asks for every section at once, then keeps only the questions that
    pass every check. Only a draft with questions uses the allowance."""
    draft = (
        ExamDraft.objects.filter(school_id=school_id, pk=draft_id, status=ExamDraft.Status.PENDING)
        .select_related("document", "school")
        .first()
    )
    if draft is None:
        return

    settings = draft.settings
    sections = settings["sections"]
    selected = exams.selected_pages(
        draft.document.pages, settings["page_from"], settings["page_to"]
    )
    content = exams.content_for_ai(selected)
    about = _about(settings)

    try:
        topics = list_topics(content=content, **about)
    except ExamAiUnavailable:
        # Questions can still be written without the topic list.
        logger.warning("exam_topics_failed", extra={"draft": draft_id})
        topics = []
    topic_groups = exams.assign_topics(topics, sections)

    def write(index):
        section = sections[index]
        try:
            return write_questions(
                content=content,
                kind=section["kind"],
                count=section["count"],
                difficulty=section["difficulty"],
                topics=topic_groups[index],
                **about,
            )
        except ExamAiUnavailable:
            logger.warning("exam_section_failed", extra={"draft": draft_id, "section": index})
            return None

    # The calls wait on the network, so threads run them side by side.
    workers = min(len(sections), exams.MAX_PARALLEL_CALLS)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        replies = list(pool.map(write, range(len(sections))))

    if all(reply is None for reply in replies):
        fail_exam_draft(school_id, draft_id, "service_unavailable")
        return
    questions = exams.build_questions(sections, replies, selected)
    if not questions:
        fail_exam_draft(school_id, draft_id, "no_questions")
        return

    with transaction.atomic():
        _lock_workspace(draft.school)
        finished = ExamDraft.objects.filter(pk=draft_id, status=ExamDraft.Status.PENDING).update(
            status=ExamDraft.Status.READY, questions=questions, updated_at=timezone.now()
        )
        # A draft given up on meanwhile (timed out) isn't counted.
        if finished:
            AIGeneration.objects.create(school_id=school_id, kind=AIGeneration.Kind.EXAM)


def fail_exam_draft(school_id, draft_id, error):
    ExamDraft.objects.filter(
        school_id=school_id, pk=draft_id, status=ExamDraft.Status.PENDING
    ).update(status=ExamDraft.Status.FAILED, error=error, updated_at=timezone.now())


# Two are asked for, so one still comes back if the other fails a check.
REGENERATE_ASK = 2


def regenerate_exam_question(school, draft, *, kind, difficulty, source_page=None, avoid=()):
    """One new question in place of one the teacher didn't like. A few per draft, not
    counted against the allowance. Returns the question and how many are left."""
    if draft.status != ExamDraft.Status.READY:
        raise InputRejected("draft_not_ready", "This draft isn't ready yet.")

    # The place is taken first, so requests at once can't pass the limit.
    with transaction.atomic():
        locked = ExamDraft.objects.select_for_update().get(pk=draft.pk)
        if locked.regenerations >= exams.MAX_REGENERATIONS:
            raise RegenerateLimitReached()
        locked.regenerations += 1
        locked.save(update_fields=["regenerations", "updated_at"])

    settings = draft.settings
    selected = exams.selected_pages(
        draft.document.pages, settings["page_from"], settings["page_to"]
    )
    # The old question's own page, when it has enough text, keeps the new one on that part.
    page = [(number, text) for number, text in selected if number == source_page]
    material = page if exams.content_length(page) >= exams.MIN_CONTENT_CHARS else selected
    section = {"kind": kind, "count": 1, "marks": "1", "difficulty": difficulty}
    try:
        reply = write_questions(
            content=exams.content_for_ai(material),
            kind=kind,
            count=REGENERATE_ASK,
            difficulty=difficulty,
            topics=[],
            avoid=avoid,
            **_about(settings),
        )
    except ExamAiUnavailable:
        reply = None
    questions = exams.build_questions([section], [reply], selected) if reply else []

    if not questions:
        # Nothing came back, so the attempt is given back.
        with transaction.atomic():
            locked = ExamDraft.objects.select_for_update().get(pk=draft.pk)
            locked.regenerations = max(locked.regenerations - 1, 0)
            locked.save(update_fields=["regenerations", "updated_at"])
        raise ServiceUnavailable()

    question = {key: value for key, value in questions[0].items() if key != "marks"}
    return {
        "question": question,
        "regenerations_left": exams.MAX_REGENERATIONS - locked.regenerations,
    }


def save_paper_design(school, theme):
    """The look of every paper the workspace downloads. Fields not given keep their value."""
    stored = {**get_paper_design(school), **theme}
    PaperDesign.objects.update_or_create(school=school, defaults={"theme": stored})
    return stored


def _stored_theme(theme):
    return {**exams.DEFAULT_THEME, **(theme or {})}


def _question_rows(school, exam, questions):
    return [
        ExamQuestion(school=school, exam=exam, position=position, **question)
        for position, question in enumerate(questions, start=1)
    ]


@transaction.atomic
def create_exam(school, *, questions, draft=None, classroom=None, theme=None, **fields):
    """Saves a test. One saved from an AI draft is marked as AI, and the draft is removed."""
    _check_plan_classroom(school, classroom)
    exam = Exam.objects.create(
        school=school,
        classroom=classroom,
        # Without a theme of its own, a test takes the workspace's paper design.
        theme=_stored_theme(theme or get_paper_design(school)),
        source=Exam.Source.AI if draft is not None else Exam.Source.MANUAL,
        **fields,
    )
    ExamQuestion.objects.bulk_create(_question_rows(school, exam, questions))
    if draft is not None:
        draft.delete()
    return exam


@transaction.atomic
def update_exam(school, exam, *, questions=None, **fields):
    """Questions, when given, replace the old ones in the new order."""
    _check_plan_classroom(school, fields.get("classroom"))
    if "theme" in fields:
        # A partial theme changes only what it names.
        fields["theme"] = {**_stored_theme(exam.theme), **fields["theme"]}
    for field, value in fields.items():
        setattr(exam, field, value)
    exam.save(update_fields=[*fields, "updated_at"])
    if questions is not None:
        ExamQuestion.objects.filter(school=school, exam=exam).delete()
        ExamQuestion.objects.bulk_create(_question_rows(school, exam, questions))
    return exam


COPY_SUFFIX = {"en": " (copy)", "ar": " (نسخة)"}
QUESTION_FIELDS = (
    "kind",
    "text",
    "options",
    "correct_option",
    "answer",
    "explanation",
    "marks",
    "difficulty",
    "source_page",
)


@transaction.atomic
def duplicate_exam(school, exam):
    suffix = COPY_SUFFIX.get(exam.language, COPY_SUFFIX["en"])
    copy = Exam.objects.create(
        school=school,
        classroom=exam.classroom,
        title=exam.title[: 200 - len(suffix)] + suffix,
        subject=exam.subject,
        grade=exam.grade,
        language=exam.language,
        exam_date=exam.exam_date,
        duration_minutes=exam.duration_minutes,
        instructions=exam.instructions,
        theme=exam.theme,
        source=exam.source,
    )
    questions = [
        {field: getattr(question, field) for field in QUESTION_FIELDS}
        for question in exam.questions.all()
    ]
    ExamQuestion.objects.bulk_create(_question_rows(school, copy, questions))
    return copy


def clean_up_exam_drafts():
    """Every hour: gives up on lost drafts, and removes drafts and PDF text over a day old."""
    now = timezone.now()
    ExamDraft.objects.filter(
        status=ExamDraft.Status.PENDING, created_at__lt=now - exams.PENDING_TIMEOUT
    ).update(status=ExamDraft.Status.FAILED, error="timed_out", updated_at=now)
    ExamDraft.objects.filter(created_at__lt=now - exams.DRAFT_LIFETIME).delete()
    # A draft touches its PDF text when made, so no draft under a day old loses it.
    SourceDocument.objects.filter(updated_at__lt=now - exams.DRAFT_LIFETIME).delete()


# --- Teacher Pro


@transaction.atomic
def send_parent_message(school, access, classroom, *, subject, body):
    _require_pro(access)
    recipients = list_parent_emails(school, classroom)
    if not recipients:
        raise ValidationError({"classroom": "No student in this class has a parent email."})

    message = ParentMessage.objects.create(
        school=school,
        classroom=classroom,
        subject=subject,
        body=body,
        recipient_count=len(recipients),
    )
    transaction.on_commit(
        lambda: send_parent_message_task.delay(school.id, message.id), robust=True
    )
    return message


# --- Upgrade


@transaction.atomic
def request_upgrade(school, *, plan, note=""):
    _lock_workspace(school)
    pending = UpgradeRequest.objects.filter(
        school=school, status=UpgradeRequest.Status.PENDING
    ).first()
    if pending:
        pending.plan = plan
        pending.note = note
        pending.save(update_fields=["plan", "note", "updated_at"])
        return pending
    return UpgradeRequest.objects.create(school=school, plan=plan, note=note)


def complete_upgrade_requests(school):
    UpgradeRequest.objects.filter(school=school, status=UpgradeRequest.Status.PENDING).update(
        status=UpgradeRequest.Status.COMPLETED,
        completed_at=timezone.now(),
        updated_at=timezone.now(),
    )
