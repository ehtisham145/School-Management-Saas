"""AI tests made from a PDF: upload, patterns, drafts, saved tests and their files."""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from itertools import count
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.classroom import exams
from apps.classroom.exam_documents import build_paper
from apps.classroom.models import (
    AIGeneration,
    Classroom,
    Exam,
    ExamDraft,
    ExamPattern,
    ExamQuestion,
    PaperDesign,
    SourceDocument,
)
from apps.classroom.services import clean_up_exam_drafts
from apps.integrations.ai.exam_provider import ExamAiUnavailable
from apps.integrations.pdf.renderer import PdfUnavailable
from apps.integrations.pdf.text_extractor import PdfTextError

pytestmark = pytest.mark.django_db

BASE = "/api/classroom"
QUOTES = [
    "Photosynthesis is the process by which green plants make their own food.",
    "Plants use sunlight, water and carbon dioxide to make glucose and oxygen.",
    "The green pigment chlorophyll absorbs the light energy needed for this process.",
    "Respiration releases energy from glucose inside the cells of living things.",
    "Oxygen is used and carbon dioxide and water are given out as waste products.",
    "Animals and plants both respire all the time, during the day and at night.",
]
PAGE_ONE = " ".join(QUOTES[:3]) + " " + " ".join(QUOTES[:3])
PAGE_TWO = " ".join(QUOTES[3:]) + " " + " ".join(QUOTES[3:])
PAGES = [PAGE_ONE, PAGE_TWO, ""]
SECTIONS = [
    {"kind": "mcq", "count": 3, "marks": "1", "difficulty": "medium"},
    {"kind": "true_false", "count": 2, "marks": "0.5", "difficulty": "easy"},
]

READ_PDF = "apps.classroom.services.read_pdf_pages"
LIST_TOPICS = "apps.classroom.services.list_topics"
WRITE_QUESTIONS = "apps.classroom.services.write_questions"


# --- Helpers


def _upload(content=b"%PDF-1.7 test file", name="biology.pdf"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


_file_numbers = count(1)


def _source(workspace, pages=PAGES):
    return SourceDocument.objects.create(
        school=workspace.school,
        # Each one a different file, as one file is kept once per workspace.
        sha256=f"{next(_file_numbers):064d}",
        filename="biology.pdf",
        page_count=len(pages),
        pages=list(pages),
    )


def _mcq(n, quote=QUOTES[1], **changes):
    return {
        "text": f"Question {n}: what do plants make?",
        "options": [f"Right {n}", f"Wrong {n} one", f"Wrong {n} two", f"Wrong {n} three"],
        "correct_option": 0,
        "answer": "",
        "explanation": "The text says so.",
        "quote": quote,
        **changes,
    }


def _true_false(n, quote=QUOTES[4], **changes):
    return {
        "text": f"Statement {n}: cells give out oxygen.",
        "options": [],
        "correct_option": -1,
        "answer": "false",
        "explanation": "Oxygen is used, not given out.",
        "quote": quote,
        **changes,
    }


def _good_reply(**kwargs):
    """What a well-behaved AI sends back for any section."""
    maker = _mcq if kwargs["kind"] == "mcq" else _true_false
    return [maker(f"{kwargs['kind']}-{index}") for index in range(kwargs["count"])]


def _draft_body(source, **changes):
    return {
        "source": source.id,
        "page_from": 1,
        "page_to": 2,
        "title": "Plants",
        "subject": "Science",
        "grade": "7",
        "language": "en",
        "sections": SECTIONS,
        **changes,
    }


def _start_draft(workspace, capture, source=None, **changes):
    source = source or _source(workspace)
    with capture(execute=True):
        response = workspace.client.post(
            f"{BASE}/exam-drafts/", _draft_body(source, **changes), format="json"
        )
    return response


def _ready_draft(workspace, questions=None, **fields):
    fields.setdefault("status", ExamDraft.Status.READY)
    return ExamDraft.objects.create(
        school=workspace.school,
        document=_source(workspace),
        settings={
            "title": "Plants",
            "subject": "Science",
            "grade": "7",
            "language": "en",
            "classroom": None,
            "page_from": 1,
            "page_to": 2,
            "sections": SECTIONS,
        },
        questions=questions or [],
        requested=5,
        **fields,
    )


def _question(**changes):
    return {
        "kind": "mcq",
        "text": "What do plants make?",
        "options": ["Glucose", "Salt", "Iron"],
        "correct_option": 0,
        "marks": "2",
        **changes,
    }


def _other(kind, text, **fields):
    """A question that isn't multiple choice."""
    return {"kind": kind, "text": text, "marks": "1", **fields}


def _exam(workspace, title="Plants quiz", language="en", questions=None, **fields):
    exam = Exam.objects.create(school=workspace.school, title=title, language=language, **fields)
    for position, question in enumerate(questions or [_question()], start=1):
        ExamQuestion.objects.create(
            school=workspace.school, exam=exam, position=position, **question
        )
    return exam


# --- Who can use it


@pytest.mark.parametrize(
    "path", ["exam-options/", "exam-patterns/", "exams/", "exam-drafts/1/", "exams/1/"]
)
def test_signed_out_visitors_are_denied(api_client, path):
    assert api_client.get(f"{BASE}/{path}").status_code == 403


def test_signed_out_visitors_cannot_upload(api_client):
    response = api_client.post(f"{BASE}/exam-sources/", {"file": _upload()}, format="multipart")

    assert response.status_code == 403


def test_options_list_the_ready_patterns_and_paper_colors(teacher):
    response = teacher.client.get(f"{BASE}/exam-options/")

    assert response.status_code == 200
    assert [preset["key"] for preset in response.data["presets"]] == [
        "quick_quiz",
        "mixed",
        "exam",
    ]
    assert {"key": "navy", **exams.THEMES["navy"]} in response.data["themes"]
    assert response.data["limits"]["max_pdf_pages"] == exams.MAX_PDF_PAGES


# --- Another teacher's tests are never reachable


def test_other_teachers_tests_are_not_found(trial, other):
    exam = _exam(other)
    pattern = ExamPattern.objects.create(school=other.school, name="Theirs", sections=SECTIONS)
    draft = _ready_draft(other, questions=[{"kind": "mcq"}])
    client = trial.client

    assert client.get(f"{BASE}/exams/{exam.id}/").status_code == 404
    assert client.patch(f"{BASE}/exams/{exam.id}/", {"title": "X"}).status_code == 404
    assert client.delete(f"{BASE}/exams/{exam.id}/").status_code == 404
    assert client.post(f"{BASE}/exams/{exam.id}/duplicate/").status_code == 404
    assert client.get(f"{BASE}/exams/{exam.id}/download/").status_code == 404
    assert (
        client.patch(f"{BASE}/exam-patterns/{pattern.id}/", {"name": "X"}, format="json")
    ).status_code == 404
    assert client.delete(f"{BASE}/exam-patterns/{pattern.id}/").status_code == 404
    assert client.get(f"{BASE}/exam-drafts/{draft.id}/").status_code == 404
    assert (
        client.post(
            f"{BASE}/exam-drafts/{draft.id}/regenerate/", {"kind": "mcq"}, format="json"
        ).status_code
        == 404
    )
    assert Exam.objects.filter(pk=exam.pk, title="Plants quiz").exists()
    assert ExamPattern.objects.filter(pk=pattern.pk).exists()


def test_lists_show_only_your_own_tests_and_patterns(trial, other):
    _exam(trial, "Mine")
    _exam(other, "Theirs")
    ExamPattern.objects.create(school=other.school, name="Theirs", sections=SECTIONS)

    exams_list = trial.client.get(f"{BASE}/exams/").data
    assert [row["title"] for row in exams_list["results"]] == ["Mine"]
    assert trial.client.get(f"{BASE}/exam-patterns/").data == []


@patch(WRITE_QUESTIONS, side_effect=_good_reply)
@patch(LIST_TOPICS, return_value=[])
def test_another_teachers_pdf_cannot_be_used(_topics, write, trial, other):
    theirs = _source(other)

    response = trial.client.post(f"{BASE}/exam-drafts/", _draft_body(theirs), format="json")

    assert response.status_code == 400
    assert "source" in response.data["error"]["fields"]
    write.assert_not_called()


def test_another_teachers_class_or_draft_cannot_be_linked(trial, other):
    theirs = Classroom.objects.create(school=other.school, name="5A")
    their_draft = _ready_draft(other)

    with_class = trial.client.post(
        f"{BASE}/exams/",
        {"title": "Quiz", "classroom": theirs.id, "questions": [_question()]},
        format="json",
    )
    with_draft = trial.client.post(
        f"{BASE}/exams/",
        {"title": "Quiz", "draft": their_draft.id, "questions": [_question()]},
        format="json",
    )

    assert with_class.status_code == 400
    assert with_draft.status_code == 400
    assert ExamDraft.objects.filter(pk=their_draft.pk).exists()


def test_the_same_pdf_in_two_workspaces_is_kept_apart(trial, other):
    with patch(READ_PDF, return_value=PAGES):
        mine = trial.client.post(f"{BASE}/exam-sources/", {"file": _upload()}, format="multipart")
        theirs = other.client.post(f"{BASE}/exam-sources/", {"file": _upload()}, format="multipart")

    assert mine.data["id"] != theirs.data["id"]
    assert SourceDocument.objects.count() == 2


# --- An ended plan


def test_an_ended_trial_cannot_make_tests_but_can_still_download(expired):
    exam = _exam(expired)
    source = _source(expired)
    client = expired.client

    blocked = [
        client.post(f"{BASE}/exam-sources/", {"file": _upload()}, format="multipart"),
        client.post(f"{BASE}/exam-drafts/", _draft_body(source), format="json"),
        client.post(f"{BASE}/exams/", {"title": "X", "questions": [_question()]}, format="json"),
        client.patch(f"{BASE}/exams/{exam.id}/", {"title": "X"}, format="json"),
        client.post(f"{BASE}/exam-patterns/", {"name": "X", "sections": SECTIONS}, format="json"),
    ]

    assert all(response.status_code == 403 for response in blocked)
    assert blocked[0].data["error"]["code"] == "workspace_read_only"
    assert client.get(f"{BASE}/exams/").status_code == 200
    with patch("apps.classroom.exam_documents.html_to_pdf", return_value=b"%PDF-1.7"):
        assert client.get(f"{BASE}/exams/{exam.id}/download/").status_code == 200


# --- Uploading a PDF


def test_a_pdf_is_read_and_only_its_text_is_kept(teacher):
    with patch(READ_PDF, return_value=PAGES) as read:
        response = teacher.client.post(
            f"{BASE}/exam-sources/", {"file": _upload()}, format="multipart"
        )

    assert response.status_code == 201
    assert response.data["page_count"] == 3
    # The third page has no text, so it can't be chosen.
    assert response.data["text_pages"] == [1, 2]
    assert response.data["preview"].startswith("Photosynthesis")
    assert read.call_args.kwargs == {"max_pages": exams.MAX_PDF_PAGES}
    document = SourceDocument.objects.get()
    assert document.pages == PAGES
    assert len(document.sha256) == 64


def test_the_same_pdf_again_is_not_read_twice(teacher):
    with patch(READ_PDF, return_value=PAGES) as read:
        first = teacher.client.post(
            f"{BASE}/exam-sources/", {"file": _upload()}, format="multipart"
        )
        second = teacher.client.post(
            f"{BASE}/exam-sources/", {"file": _upload()}, format="multipart"
        )

    assert first.data["id"] == second.data["id"]
    read.assert_called_once()


@pytest.mark.parametrize(
    "code",
    ["not_pdf", "pdf_locked", "pdf_too_many_pages", "pdf_unreadable", "pdf_no_text"],
)
def test_a_pdf_that_cant_be_used_says_why(teacher, code):
    with patch(READ_PDF, side_effect=PdfTextError(code, "No.")):
        response = teacher.client.post(
            f"{BASE}/exam-sources/", {"file": _upload()}, format="multipart"
        )

    assert response.status_code == 400
    assert response.data["error"]["code"] == code
    assert not SourceDocument.objects.exists()


def test_a_file_that_is_not_named_pdf_is_refused(teacher):
    with patch(READ_PDF) as read:
        response = teacher.client.post(
            f"{BASE}/exam-sources/", {"file": _upload(name="notes.docx")}, format="multipart"
        )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "not_pdf"
    read.assert_not_called()


def test_a_pdf_over_the_size_limit_is_refused(teacher):
    too_big = b"%PDF-1.7" + b"0" * exams.MAX_PDF_BYTES

    with patch(READ_PDF) as read:
        response = teacher.client.post(
            f"{BASE}/exam-sources/", {"file": _upload(too_big)}, format="multipart"
        )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "pdf_too_large"
    read.assert_not_called()


def test_an_upload_needs_a_file(teacher):
    response = teacher.client.post(f"{BASE}/exam-sources/", {}, format="multipart")

    assert response.status_code == 400
    assert "file" in response.data["error"]["fields"]


# --- Patterns


def test_a_teacher_can_save_edit_and_delete_a_pattern(teacher):
    created = teacher.client.post(
        f"{BASE}/exam-patterns/", {"name": "  Weekly   quiz ", "sections": SECTIONS}, format="json"
    )
    pattern_id = created.data["id"]
    renamed = teacher.client.patch(
        f"{BASE}/exam-patterns/{pattern_id}/", {"name": "Friday quiz"}, format="json"
    )
    resized = teacher.client.patch(
        f"{BASE}/exam-patterns/{pattern_id}/",
        {"sections": [{"kind": "short_answer", "count": 4, "marks": "2.5"}]},
        format="json",
    )
    deleted = teacher.client.delete(f"{BASE}/exam-patterns/{pattern_id}/")

    assert created.status_code == 201
    assert created.data["name"] == "Weekly quiz"
    assert created.data["sections"][1]["marks"] == "0.50"
    assert renamed.data["name"] == "Friday quiz"
    # Changing only the name keeps the sections.
    assert len(renamed.data["sections"]) == 2
    assert resized.data["sections"] == [
        {"kind": "short_answer", "count": 4, "marks": "2.50", "difficulty": "medium"}
    ]
    assert deleted.status_code == 204
    assert not ExamPattern.objects.exists()


def test_pattern_names_are_unique_whatever_the_case(teacher):
    ExamPattern.objects.create(school=teacher.school, name="Weekly quiz", sections=SECTIONS)

    response = teacher.client.post(
        f"{BASE}/exam-patterns/", {"name": "WEEKLY QUIZ", "sections": SECTIONS}, format="json"
    )

    assert response.status_code == 400
    assert "name" in response.data["error"]["fields"]


@pytest.mark.parametrize(
    "sections",
    [
        [],
        [{"kind": "essay", "count": 2, "marks": "1"}],
        [{"kind": "mcq", "count": 0, "marks": "1"}],
        [{"kind": "mcq", "count": 31, "marks": "1"}],
        [{"kind": "mcq", "count": 2, "marks": "0"}],
        [{"kind": "mcq", "count": 2, "marks": "101"}],
        [{"kind": "mcq", "count": 2}],
        [{"kind": "mcq", "count": 30, "marks": "1"}, {"kind": "mcq", "count": 21, "marks": "1"}],
        [{"kind": "mcq", "count": 1, "marks": "1"}] * (exams.MAX_SECTIONS + 1),
    ],
)
def test_a_pattern_needs_sensible_sections(teacher, sections):
    response = teacher.client.post(
        f"{BASE}/exam-patterns/", {"name": "Quiz", "sections": sections}, format="json"
    )

    assert response.status_code == 400
    assert "sections" in response.data["error"]["fields"]


def test_a_partial_section_cannot_sneak_in_through_an_edit(teacher):
    pattern = ExamPattern.objects.create(school=teacher.school, name="Quiz", sections=SECTIONS)

    response = teacher.client.patch(
        f"{BASE}/exam-patterns/{pattern.id}/", {"sections": [{"kind": "mcq"}]}, format="json"
    )

    assert response.status_code == 400
    pattern.refresh_from_db()
    assert pattern.sections == SECTIONS


def test_a_workspace_keeps_a_limited_number_of_patterns(teacher):
    ExamPattern.objects.bulk_create(
        ExamPattern(school=teacher.school, name=f"P{index}", sections=SECTIONS)
        for index in range(exams.MAX_PATTERNS)
    )

    response = teacher.client.post(
        f"{BASE}/exam-patterns/", {"name": "One more", "sections": SECTIONS}, format="json"
    )

    assert response.status_code == 400
    assert ExamPattern.objects.count() == exams.MAX_PATTERNS


# --- AI drafts


@patch(WRITE_QUESTIONS, side_effect=_good_reply)
@patch(LIST_TOPICS, return_value=["Photosynthesis", "Respiration", "Chlorophyll"])
@pytest.mark.parametrize("workspace", ["trial", "teacher", "pro"])
def test_every_plan_can_make_an_ai_test(
    topics, write, workspace, request, django_capture_on_commit_callbacks
):
    chosen = request.getfixturevalue(workspace)

    started = _start_draft(chosen, django_capture_on_commit_callbacks)
    draft = chosen.client.get(f"{BASE}/exam-drafts/{started.data['id']}/").data

    assert started.status_code == 202
    assert started.data["status"] == "pending"
    assert draft["status"] == "ready"
    assert draft["requested"] == 5
    assert [question["kind"] for question in draft["questions"]] == ["mcq"] * 3 + ["true_false"] * 2
    first = draft["questions"][0]
    assert first["marks"] == "1.00"
    assert first["correct_option"] == 0
    assert first["source_page"] == 1
    assert draft["questions"][3]["source_page"] == 2
    assert draft["questions"][3]["marks"] == "0.50"
    assert draft["regenerations_left"] == exams.MAX_REGENERATIONS
    # Counted once, as a test, not as a lesson plan.
    assert AIGeneration.objects.get().kind == "exam"
    usage = chosen.client.get(f"{BASE}/workspace/").data["usage"]
    assert usage["ai_exams_used"] == 1
    assert usage["ai_used"] == 0
    # A draft only: nothing is saved as a test until the teacher saves it.
    assert not Exam.objects.exists()


@patch(WRITE_QUESTIONS, side_effect=_good_reply)
@patch(LIST_TOPICS, return_value=["A", "B", "C"])
def test_only_the_chosen_pages_go_to_the_ai(
    topics, write, teacher, django_capture_on_commit_callbacks
):
    _start_draft(
        teacher,
        django_capture_on_commit_callbacks,
        page_from=2,
        page_to=2,
        sections=[{"kind": "true_false", "count": 2, "marks": "1"}],
    )

    content = write.call_args.kwargs["content"]
    assert "[Page 2]" in content
    assert "Respiration" in content
    assert "Photosynthesis" not in content
    assert topics.call_args.kwargs["content"] == content
    assert write.call_args.kwargs["language"] == "en"
    assert write.call_args.kwargs["topics"] == ["A", "B", "C"]


@patch(WRITE_QUESTIONS, side_effect=_good_reply)
@patch(LIST_TOPICS, return_value=["A", "B", "C"])
def test_each_section_gets_its_own_call_and_share_of_topics(
    topics, write, teacher, django_capture_on_commit_callbacks
):
    _start_draft(teacher, django_capture_on_commit_callbacks)

    calls = sorted(write.call_args_list, key=lambda call: call.kwargs["kind"])
    assert [(call.kwargs["kind"], call.kwargs["count"]) for call in calls] == [
        ("mcq", 3),
        ("true_false", 2),
    ]
    assert calls[0].kwargs["topics"] == ["A", "C"]
    assert calls[1].kwargs["topics"] == ["B"]
    assert calls[0].kwargs["difficulty"] == "medium"


@patch(WRITE_QUESTIONS, side_effect=_good_reply)
@patch(LIST_TOPICS, side_effect=ExamAiUnavailable("down"))
def test_a_failed_topic_list_does_not_stop_the_test(
    _topics, write, teacher, django_capture_on_commit_callbacks
):
    started = _start_draft(teacher, django_capture_on_commit_callbacks)

    draft = ExamDraft.objects.get(pk=started.data["id"])
    assert draft.status == "ready"
    assert all(call.kwargs["topics"] == [] for call in write.call_args_list)


def _bad_reply(**kwargs):
    if kwargs["kind"] != "mcq":
        return [_true_false(1), _true_false(2, answer="maybe")]
    return [
        _mcq(1),
        _mcq(2, correct_option=7),  # No such option.
        _mcq(3, options=["Same", "same", "Other", "More"]),  # Repeated option.
        _mcq(4, options=["A cell", "A leaf", "A root", "All of the above"]),
        _mcq(5, quote="The moon is made of cheese and orbits the planet Jupiter."),  # Made up.
        _mcq(1),  # The same question again.
        _mcq(6, options=["Only one", "Two"]),  # Too few options.
        _mcq(7, text=""),
        _mcq(8),
        _mcq(9),  # One more than asked for.
    ]


@patch(WRITE_QUESTIONS, side_effect=_bad_reply)
@patch(LIST_TOPICS, return_value=[])
def test_questions_that_break_a_rule_are_dropped(
    _topics, _write, teacher, django_capture_on_commit_callbacks
):
    started = _start_draft(teacher, django_capture_on_commit_callbacks)

    draft = ExamDraft.objects.get(pk=started.data["id"])
    texts = [question["text"] for question in draft.questions]
    assert texts == [
        "Question 1: what do plants make?",
        "Question 8: what do plants make?",
        "Question 9: what do plants make?",
        "Statement 1: cells give out oxygen.",
    ]
    assert draft.requested == 5


@patch(WRITE_QUESTIONS, side_effect=ExamAiUnavailable("down"))
@patch(LIST_TOPICS, return_value=[])
def test_an_ai_failure_uses_no_allowance(_topics, _write, pro, django_capture_on_commit_callbacks):
    started = _start_draft(pro, django_capture_on_commit_callbacks)

    draft = pro.client.get(f"{BASE}/exam-drafts/{started.data['id']}/").data
    assert draft["status"] == "failed"
    assert draft["error"] == "service_unavailable"
    assert not AIGeneration.objects.exists()


@patch(WRITE_QUESTIONS, return_value=[_mcq(1, quote="Nothing like this is in the material.")])
@patch(LIST_TOPICS, return_value=[])
def test_a_draft_with_no_good_question_fails_and_is_not_counted(
    _topics, _write, pro, django_capture_on_commit_callbacks
):
    started = _start_draft(pro, django_capture_on_commit_callbacks)

    draft = ExamDraft.objects.get(pk=started.data["id"])
    assert draft.status == "failed"
    assert draft.error == "no_questions"
    assert not AIGeneration.objects.exists()


@patch(WRITE_QUESTIONS, side_effect=_good_reply)
@patch(LIST_TOPICS, return_value=[])
@pytest.mark.parametrize(("workspace", "allowance"), [("trial", 5), ("teacher", 20), ("pro", 60)])
def test_each_plan_has_an_ai_test_allowance(_topics, write, workspace, allowance, request):
    chosen = request.getfixturevalue(workspace)
    AIGeneration.objects.bulk_create(
        AIGeneration(school=chosen.school, kind="exam") for _ in range(allowance)
    )

    response = chosen.client.post(
        f"{BASE}/exam-drafts/", _draft_body(_source(chosen)), format="json"
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "ai_exam_quota_reached"
    assert not ExamDraft.objects.exists()
    write.assert_not_called()


@patch(WRITE_QUESTIONS, side_effect=_good_reply)
@patch(LIST_TOPICS, return_value=[])
def test_ai_lesson_plans_do_not_use_the_test_allowance(
    _topics, _write, trial, django_capture_on_commit_callbacks
):
    AIGeneration.objects.bulk_create(AIGeneration(school=trial.school) for _ in range(10))

    response = _start_draft(trial, django_capture_on_commit_callbacks)

    assert response.status_code == 202


def test_tests_being_written_hold_a_place_in_the_allowance(trial):
    source = _source(trial)
    ExamDraft.objects.bulk_create(
        ExamDraft(school=trial.school, document=source, settings={}, requested=5) for _ in range(5)
    )

    response = trial.client.post(f"{BASE}/exam-drafts/", _draft_body(source), format="json")

    assert response.status_code == 403
    assert response.data["error"]["code"] == "ai_exam_quota_reached"


def test_a_lost_draft_stops_holding_a_place(trial, django_capture_on_commit_callbacks):
    source = _source(trial)
    ExamDraft.objects.bulk_create(
        ExamDraft(school=trial.school, document=source, settings={}, requested=5) for _ in range(5)
    )
    ExamDraft.objects.update(created_at=timezone.now() - exams.PENDING_TIMEOUT * 2)

    with patch(LIST_TOPICS, return_value=[]), patch(WRITE_QUESTIONS, side_effect=_good_reply):
        response = _start_draft(trial, django_capture_on_commit_callbacks, source=source)

    assert response.status_code == 202


@patch(WRITE_QUESTIONS)
def test_last_months_ai_tests_do_not_count_on_a_paid_plan(
    write, teacher, django_capture_on_commit_callbacks
):
    write.side_effect = _good_reply
    AIGeneration.objects.bulk_create(
        AIGeneration(school=teacher.school, kind="exam") for _ in range(20)
    )
    AIGeneration.objects.update(created_at=timezone.now() - timedelta(days=40))

    with patch(LIST_TOPICS, return_value=[]):
        response = _start_draft(teacher, django_capture_on_commit_callbacks)

    assert response.status_code == 202


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"page_from": 2, "page_to": 1}, "page_to"),
        ({"page_to": 4}, "page_to"),
        ({"page_from": 0}, "page_from"),
        ({"title": ""}, "title"),
        ({"language": "fr"}, "language"),
        ({"sections": []}, "sections"),
        ({"sections": [{"kind": "mcq", "count": 30, "marks": "1"}] * 2}, "sections"),
    ],
)
def test_a_draft_request_is_checked(pro, changes, field):
    with patch(WRITE_QUESTIONS) as write:
        response = pro.client.post(
            f"{BASE}/exam-drafts/", _draft_body(_source(pro), **changes), format="json"
        )

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]
    write.assert_not_called()


def test_pages_with_too_little_text_are_refused(pro):
    source = _source(pro, pages=["Short page.", "Another short page.", ""])

    response = pro.client.post(f"{BASE}/exam-drafts/", _draft_body(source), format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "too_little_text"
    assert not ExamDraft.objects.exists()


def test_a_draft_over_a_day_old_is_gone(teacher):
    draft = _ready_draft(teacher)
    ExamDraft.objects.filter(pk=draft.pk).update(
        created_at=timezone.now() - exams.DRAFT_LIFETIME - timedelta(minutes=1)
    )

    assert teacher.client.get(f"{BASE}/exam-drafts/{draft.id}/").status_code == 404


# --- Writing one question again


def test_a_question_can_be_written_again(teacher):
    draft = _ready_draft(teacher)

    with patch(WRITE_QUESTIONS, return_value=[_mcq(99, quote=QUOTES[3])]) as write:
        response = teacher.client.post(
            f"{BASE}/exam-drafts/{draft.id}/regenerate/",
            {"kind": "mcq", "difficulty": "hard", "source_page": 2, "avoid": ["Old question?"]},
            format="json",
        )

    assert response.status_code == 200
    assert response.data["question"]["text"] == "Question 99: what do plants make?"
    assert response.data["question"]["source_page"] == 2
    assert "marks" not in response.data["question"]
    assert response.data["regenerations_left"] == exams.MAX_REGENERATIONS - 1
    assert write.call_args.kwargs["avoid"] == ["Old question?"]
    assert write.call_args.kwargs["difficulty"] == "hard"
    # Only the old question's page is sent, as it has enough text.
    assert "Photosynthesis" not in write.call_args.kwargs["content"]
    # Not counted against the AI test allowance.
    assert not AIGeneration.objects.exists()


def test_writing_again_is_limited_per_draft(teacher):
    draft = _ready_draft(teacher, regenerations=exams.MAX_REGENERATIONS)

    with patch(WRITE_QUESTIONS) as write:
        response = teacher.client.post(
            f"{BASE}/exam-drafts/{draft.id}/regenerate/", {"kind": "mcq"}, format="json"
        )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "regenerate_limit_reached"
    write.assert_not_called()


@pytest.mark.parametrize(
    "reply",
    [ExamAiUnavailable("down"), [_mcq(1, quote="Words that are nowhere in the material here.")]],
)
def test_a_failed_rewrite_gives_the_attempt_back(teacher, reply):
    draft = _ready_draft(teacher, regenerations=2)
    effect = {"side_effect": reply} if isinstance(reply, Exception) else {"return_value": reply}

    with patch(WRITE_QUESTIONS, **effect):
        response = teacher.client.post(
            f"{BASE}/exam-drafts/{draft.id}/regenerate/", {"kind": "mcq"}, format="json"
        )

    assert response.status_code == 503
    draft.refresh_from_db()
    assert draft.regenerations == 2


def test_a_draft_still_being_written_cannot_be_rewritten(teacher):
    draft = _ready_draft(teacher, status=ExamDraft.Status.PENDING)

    response = teacher.client.post(
        f"{BASE}/exam-drafts/{draft.id}/regenerate/", {"kind": "mcq"}, format="json"
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "draft_not_ready"


# --- Saved tests


def test_a_reviewed_draft_is_saved_as_an_ai_test(teacher):
    draft = _ready_draft(teacher)
    classroom = Classroom.objects.create(school=teacher.school, name="7B")

    response = teacher.client.post(
        f"{BASE}/exams/",
        {
            "title": "Plants, checked",
            "subject": "Science",
            "language": "en",
            "classroom": classroom.id,
            "duration_minutes": 40,
            "draft": draft.id,
            "theme": {"color": "green", "columns": 2},
            "questions": [
                _question(),
                {"kind": "true_false", "text": "Plants respire.", "answer": "true", "marks": "1"},
                {
                    "kind": "fill_blank",
                    "text": "Plants make ___ in light.",
                    "answer": "glucose",
                    "marks": "1.5",
                    "options": ["ignored"],
                },
                {"kind": "short_answer", "text": "Explain respiration.", "marks": "3"},
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["source"] == "ai"
    assert response.data["classroom_name"] == "7B"
    assert response.data["question_count"] == 4
    assert response.data["total_marks"] == "7.50"
    assert response.data["theme"] == {
        "color": "green",
        "font_size": "normal",
        "columns": 2,
        "name_line": True,
    }
    blank = response.data["questions"][2]
    assert blank["text"] == "Plants make _____ in light."
    assert blank["options"] == []
    assert [question.position for question in ExamQuestion.objects.all()] == [1, 2, 3, 4]
    # The draft's work is saved, so the draft itself goes.
    assert not ExamDraft.objects.exists()


def test_a_test_written_by_hand_is_marked_manual(teacher):
    response = teacher.client.post(
        f"{BASE}/exams/", {"title": "Quiz", "questions": [_question()]}, format="json"
    )

    assert response.status_code == 201
    assert response.data["source"] == "manual"


@pytest.mark.parametrize(
    ("question", "field"),
    [
        (_question(correct_option=3), "correct_option"),
        (_question(correct_option=None), "correct_option"),
        (_question(options=["Only one"]), "options"),
        (_question(options=["Glucose", "glucose."]), "options"),
        (_question(text=""), "text"),
        (_question(marks="0"), "marks"),
        (_question(kind="essay"), "kind"),
        (_other("true_false", "Plants respire.", answer="maybe"), "answer"),
        (_other("fill_blank", "No blank here.", answer="x"), "text"),
        (_other("fill_blank", "Two ___ and ___.", answer="x"), "text"),
        (_other("fill_blank", "One ___ here.", answer=" "), "answer"),
    ],
)
def test_each_question_is_checked(teacher, question, field):
    response = teacher.client.post(
        f"{BASE}/exams/", {"title": "Quiz", "questions": [question]}, format="json"
    )

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]["questions"][0]
    assert not Exam.objects.exists()


@pytest.mark.parametrize("count", [0, exams.MAX_EXAM_QUESTIONS + 1])
def test_a_test_needs_a_sensible_number_of_questions(teacher, count):
    response = teacher.client.post(
        f"{BASE}/exams/", {"title": "Quiz", "questions": [_question()] * count}, format="json"
    )

    assert response.status_code == 400
    assert "questions" in response.data["error"]["fields"]


def test_a_test_comes_back_with_its_questions_in_order(teacher):
    exam = _exam(
        teacher,
        questions=[_question(text="First?"), _question(text="Second?", marks="1.5")],
    )

    response = teacher.client.get(f"{BASE}/exams/{exam.id}/")

    assert [question["text"] for question in response.data["questions"]] == [
        "First?",
        "Second?",
    ]
    assert response.data["total_marks"] == "3.50"


def test_editing_a_test_replaces_its_questions_only_when_given(teacher):
    exam = _exam(teacher, theme={"color": "green", "font_size": "large", "columns": 2})

    renamed = teacher.client.patch(
        f"{BASE}/exams/{exam.id}/",
        {"title": "Renamed", "theme": {"color": "purple"}},
        format="json",
    )
    replaced = teacher.client.patch(
        f"{BASE}/exams/{exam.id}/",
        {"questions": [_question(text="New one?"), _question(text="Another?")]},
        format="json",
    )

    assert renamed.status_code == 200
    assert renamed.data["question_count"] == 1
    # A partial theme changes only what it names.
    assert renamed.data["theme"]["color"] == "purple"
    assert renamed.data["theme"]["font_size"] == "large"
    assert [question["text"] for question in replaced.data["questions"]] == [
        "New one?",
        "Another?",
    ]
    assert ExamQuestion.objects.count() == 2


def test_a_half_written_question_cannot_sneak_in_through_an_edit(teacher):
    exam = _exam(teacher)

    response = teacher.client.patch(
        f"{BASE}/exams/{exam.id}/", {"questions": [{"kind": "mcq"}]}, format="json"
    )

    assert response.status_code == 400
    assert ExamQuestion.objects.get().text == "What do plants make?"


@pytest.mark.parametrize(("language", "title"), [("en", "Quiz (copy)"), ("ar", "Quiz (نسخة)")])
def test_a_test_can_be_copied(teacher, language, title):
    exam = _exam(teacher, title="Quiz", language=language)

    response = teacher.client.post(f"{BASE}/exams/{exam.id}/duplicate/")

    assert response.status_code == 201
    assert response.data["title"] == title
    assert response.data["question_count"] == 1
    assert Exam.objects.count() == 2
    assert ExamQuestion.objects.count() == 2


def test_a_test_can_be_deleted(teacher):
    exam = _exam(teacher)

    assert teacher.client.delete(f"{BASE}/exams/{exam.id}/").status_code == 204
    assert not ExamQuestion.objects.exists()


def test_tests_can_be_searched_and_filtered_by_class(teacher):
    classroom = Classroom.objects.create(school=teacher.school, name="7B")
    _exam(teacher, "Plants quiz", classroom=classroom)
    _exam(teacher, "Fractions test")

    found = teacher.client.get(f"{BASE}/exams/", {"search": "plant"}).data
    by_class = teacher.client.get(f"{BASE}/exams/", {"classroom": classroom.id}).data

    assert [row["title"] for row in found["results"]] == ["Plants quiz"]
    assert [row["title"] for row in by_class["results"]] == ["Plants quiz"]
    assert found["results"][0]["question_count"] == 1


def test_the_test_list_takes_a_fixed_number_of_queries(teacher, django_assert_max_num_queries):
    for index in range(15):
        _exam(teacher, f"Quiz {index}", questions=[_question(), _question(text="Two?")])

    with django_assert_max_num_queries(10):
        response = teacher.client.get(f"{BASE}/exams/")

    assert response.data["count"] == 15


# --- Downloads


@patch("apps.classroom.exam_documents.html_to_pdf", return_value=b"%PDF-1.7")
def test_the_paper_has_no_answers_and_the_key_has_them(to_pdf, teacher):
    exam = _exam(
        teacher,
        title="Plants <quiz>",
        questions=[
            _question(explanation="Glucose is the food.", source_page=3),
            {"kind": "true_false", "text": "Plants respire.", "answer": "true", "marks": "1"},
        ],
    )

    paper = teacher.client.get(f"{BASE}/exams/{exam.id}/download/")
    paper_html = to_pdf.call_args.args[0]
    key = teacher.client.get(f"{BASE}/exams/{exam.id}/download/", {"answers": "true"})
    key_html = to_pdf.call_args.args[0]

    assert paper.status_code == 200
    assert paper["Content-Type"] == "application/pdf"
    assert 'filename="plants-quiz.pdf"' in paper["Content-Disposition"]
    assert "Plants &lt;quiz&gt;" in paper_html
    assert "(A) Glucose" in paper_html
    assert "Glucose is the food." not in paper_html
    assert 'filename="plants-quiz-answers.pdf"' in key["Content-Disposition"]
    assert "Answer: (A) Glucose" in key_html
    assert "Glucose is the food. · Page 3" in key_html
    assert "Answer: True" in key_html


@patch("apps.classroom.exam_documents.html_to_pdf", return_value=b"%PDF-1.7")
@pytest.mark.parametrize(("workspace", "marked"), [("trial", True), ("teacher", False)])
def test_only_the_trial_paper_carries_the_lesson_lab_mark(to_pdf, workspace, marked, request):
    chosen = request.getfixturevalue(workspace)
    exam = _exam(chosen)

    chosen.client.get(f"{BASE}/exams/{exam.id}/download/")

    assert ("Made with Lesson Lab" in to_pdf.call_args.args[0]) is marked


@patch("apps.classroom.exam_documents.html_to_pdf", side_effect=PdfUnavailable("no pango"))
def test_the_paper_says_when_pdf_is_unavailable(_to_pdf, teacher):
    exam = _exam(teacher)

    assert teacher.client.get(f"{BASE}/exams/{exam.id}/download/").status_code == 503


def test_the_paper_can_be_downloaded_as_word(teacher):
    docx = pytest.importorskip("docx")
    exam = _exam(teacher)
    teacher.client.put(f"{BASE}/paper-design/", {"columns": 2}, format="json")

    response = teacher.client.get(f"{BASE}/exams/{exam.id}/download/", {"type": "docx"})

    assert response.status_code == 200
    assert response["Content-Disposition"].endswith('.docx"')
    document = docx.Document(BytesIO(response.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "What do plants make?" in text
    assert "(A) Glucose" in text
    assert 'w:num="2"' in document.element.body.xml


def test_an_arabic_word_paper_is_right_to_left(teacher):
    docx = pytest.importorskip("docx")
    exam = _exam(
        teacher,
        title="اختبار النبات",
        language="ar",
        questions=[_question(text="ماذا يصنع النبات؟", options=["الجلوكوز", "الملح"])],
    )

    response = teacher.client.get(f"{BASE}/exams/{exam.id}/download/", {"type": "docx"})

    document = docx.Document(BytesIO(response.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "(أ) الجلوكوز" in text
    assert "اختيار من متعدد" in text
    assert "<w:bidi/>" in document.element.body.xml


def test_an_unknown_file_type_is_refused(teacher):
    exam = _exam(teacher)

    response = teacher.client.get(f"{BASE}/exams/{exam.id}/download/", {"type": "exe"})

    assert response.status_code == 400


def test_the_paper_groups_questions_by_kind_and_numbers_them_through(teacher):
    exam = _exam(
        teacher,
        language="ar",
        exam_date=timezone.localdate().replace(day=1),
        duration_minutes=45,
        questions=[
            _question(),
            _question(text="Second?"),
            {"kind": "short_answer", "text": "Explain.", "marks": "3"},
        ],
    )
    exam = Exam.objects.prefetch_related("questions").get(pk=exam.pk)

    paper = build_paper(exam, teacher_name="Tariq")

    assert paper["rtl"] is True
    assert [section["heading"] for section in paper["sections"]] == [
        "اختيار من متعدد (الدرجة: 4)",
        "أجب باختصار (الدرجة: 3)",
    ]
    assert [item["number"] for section in paper["sections"] for item in section["questions"]] == [
        1,
        2,
        3,
    ]
    assert paper["sections"][1]["questions"][0]["lines"] == 3
    assert ("الزمن", "45 دقيقة") in paper["details"]
    assert ("الدرجة الكلية", "7") in paper["details"]


# --- Clean-up


def test_old_drafts_and_pdf_text_are_cleaned_up(teacher):
    old = timezone.now() - exams.DRAFT_LIFETIME - timedelta(hours=1)
    lost = _ready_draft(teacher, status=ExamDraft.Status.PENDING)
    ExamDraft.objects.filter(pk=lost.pk).update(
        created_at=timezone.now() - exams.PENDING_TIMEOUT - timedelta(minutes=1)
    )
    stale = _ready_draft(teacher)
    ExamDraft.objects.filter(pk=stale.pk).update(created_at=old)
    fresh = _ready_draft(teacher)
    old_source = _source(teacher)
    SourceDocument.objects.filter(pk=old_source.pk).update(updated_at=old)

    clean_up_exam_drafts()

    lost.refresh_from_db()
    assert lost.status == "failed"
    assert lost.error == "timed_out"
    assert not ExamDraft.objects.filter(pk=stale.pk).exists()
    assert ExamDraft.objects.filter(pk=fresh.pk).exists()
    assert not SourceDocument.objects.filter(pk=old_source.pk).exists()


# --- The checks every AI question passes


def test_quotes_match_despite_arabic_marks_and_letter_forms():
    page = exams.normalize("يَصنعُ النباتُ غذاءهُ بنفسهِ في عمليةِ البناءِ الضوئيِّ داخلَ الأوراقِ.")

    assert exams.find_quote("يصنع النبات غذاءه بنفسه في عملية البناء الضوئي", [(4, page)]) == 4
    assert exams.find_quote("الحيوانات تصنع غذاءها بنفسها", [(4, page)]) is None


def test_a_quote_with_a_word_or_two_changed_still_counts():
    page = exams.normalize(QUOTES[1])

    found = exams.find_quote(
        "Plants use sunlight, water and carbon dioxide to make sugar and oxygen.", [(1, page)]
    )

    assert found == 1
    assert exams.find_quote("make glucose", [(1, page)]) is None


@pytest.mark.parametrize(
    ("answer", "saved"), [("True", "true"), ("خطأ", "false"), ("صح", "true"), ("yes", None)]
)
def test_true_or_false_answers_are_read_in_both_languages(answer, saved):
    question = exams.clean_question(_true_false(1, answer=answer), "true_false")

    assert (question and question["answer"]) == saved


def test_marks_are_shown_without_trailing_zeros():
    assert exams.format_marks(Decimal("1.50")) == "1.5"
    assert exams.format_marks(Decimal("100.00")) == "100"
    assert exams.format_marks(Decimal("0.25")) == "0.25"


# --- Paper design (one per workspace, on its own page)


def test_a_new_workspace_starts_with_the_default_paper_design(teacher):
    response = teacher.client.get(f"{BASE}/paper-design/")

    assert response.status_code == 200
    assert response.data == exams.DEFAULT_THEME


def test_the_paper_design_is_saved_and_kept(teacher):
    saved = teacher.client.put(
        f"{BASE}/paper-design/",
        {"color": "green", "font_size": "large", "columns": 2, "name_line": False},
        format="json",
    )

    assert saved.status_code == 200
    assert teacher.client.get(f"{BASE}/paper-design/").data == {
        "color": "green",
        "font_size": "large",
        "columns": 2,
        "name_line": False,
    }
    assert PaperDesign.objects.count() == 1


@pytest.mark.parametrize(
    "body",
    [{"color": "pink"}, {"font_size": "huge"}, {"columns": 3}, {"name_line": "maybe"}],
)
def test_the_paper_design_is_checked(teacher, body):
    response = teacher.client.put(f"{BASE}/paper-design/", body, format="json")

    assert response.status_code == 400
    assert not PaperDesign.objects.exists()


def test_each_workspace_has_its_own_paper_design(trial, other):
    other.client.put(f"{BASE}/paper-design/", {"color": "crimson"}, format="json")

    assert trial.client.get(f"{BASE}/paper-design/").data["color"] == "navy"
    assert other.client.get(f"{BASE}/paper-design/").data["color"] == "crimson"


def test_an_ended_trial_cannot_change_the_paper_design(expired):
    response = expired.client.put(f"{BASE}/paper-design/", {"color": "green"}, format="json")

    assert response.status_code == 403
    assert expired.client.get(f"{BASE}/paper-design/").status_code == 200


def test_signed_out_visitors_cannot_see_the_paper_design(api_client):
    assert api_client.get(f"{BASE}/paper-design/").status_code == 403


@patch("apps.classroom.exam_documents.html_to_pdf", return_value=b"%PDF-1.7")
def test_every_paper_uses_the_workspace_design(to_pdf, teacher):
    exam = _exam(teacher, theme={"color": "navy"})
    teacher.client.put(f"{BASE}/paper-design/", {"color": "crimson"}, format="json")

    teacher.client.get(f"{BASE}/exams/{exam.id}/download/")

    assert exams.THEMES["crimson"]["accent"] in to_pdf.call_args.args[0]


def test_a_test_saved_without_a_design_takes_the_workspace_one(teacher):
    teacher.client.put(f"{BASE}/paper-design/", {"color": "teal"}, format="json")

    response = teacher.client.post(
        f"{BASE}/exams/", {"title": "Quiz", "questions": [_question()]}, format="json"
    )

    assert response.data["theme"]["color"] == "teal"
