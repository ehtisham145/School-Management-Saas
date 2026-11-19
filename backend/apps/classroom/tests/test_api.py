from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.classroom.models import (
    AIGeneration,
    Assessment,
    AttendanceRecord,
    Classroom,
    LessonPlan,
    Mark,
    ParentMessage,
    PresentationExport,
    Student,
    TeacherProfile,
    UpgradeRequest,
)
from apps.integrations.ai.lesson_provider import LessonAiUnavailable
from apps.integrations.pdf.renderer import PdfUnavailable
from apps.tenancy.models import Membership, School

pytestmark = pytest.mark.django_db

BASE = "/api/classroom"
LESSON = {"title": "Water cycle", "objectives": "Explain evaporation\nExplain rain"}
AI_LESSON = {
    "title": "Fractions",
    "objectives": "Add fractions",
    "materials": "Cards",
    "activities": "Group work",
    "assessment": "Quiz",
    "homework": "Page 12",
}
GENERATE = {"topic": "Fractions", "subject": "Math", "grade": "5", "language": "en"}


def _class(workspace, name="Grade 5A"):
    return Classroom.objects.create(school=workspace.school, name=name)


def _student(workspace, classroom, name="Ali", email=""):
    first, _, last = name.partition(" ")
    return Student.objects.create(
        school=workspace.school,
        classroom=classroom,
        first_name=first,
        last_name=last,
        parent_email=email,
    )


def _assessment(workspace, classroom, max_marks=20):
    return Assessment.objects.create(
        school=workspace.school,
        classroom=classroom,
        title="Quiz 1",
        max_marks=max_marks,
        date=timezone.localdate(),
    )


def _plan(workspace, **fields):
    return LessonPlan.objects.create(school=workspace.school, title="Lesson", **fields)


# --- Who can use the workspace


@pytest.mark.parametrize(
    "path",
    [
        "workspace/",
        "classes/",
        "lesson-plans/",
        "assessments/",
        "messages/",
    ],
)
def test_signed_out_visitors_are_denied(db, path):
    assert APIClient().get(f"{BASE}/{path}").status_code == 403


@pytest.mark.parametrize("role", [Membership.Role.SCHOOL_ADMIN, Membership.Role.TEACHER])
def test_people_in_a_real_school_are_denied(db, role):
    school = School.objects.create(name_en="Al Noor", code="alnoor")
    user = User.objects.create_user("staff", password="x" * 12)
    membership = Membership.objects.create(school=school, user=user, role=role)
    client = APIClient()
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    session = client.session
    session["active_membership_id"] = membership.id
    session.save()

    assert client.get(f"{BASE}/classes/").status_code == 403


def test_a_student_role_in_a_workspace_is_denied(trial):
    Membership.objects.filter(pk=trial.membership.pk).update(role=Membership.Role.STUDENT)

    assert trial.client.get(f"{BASE}/classes/").status_code == 403


# --- Another teacher's data is never reachable


def test_other_teachers_records_are_not_found(trial, other):
    classroom = _class(other)
    student = _student(other, classroom)
    plan = _plan(other)
    assessment = _assessment(other, classroom)
    client = trial.client

    assert client.get(f"{BASE}/classes/{classroom.id}/").status_code == 404
    assert client.patch(f"{BASE}/classes/{classroom.id}/", {"name": "X"}).status_code == 404
    assert client.delete(f"{BASE}/classes/{classroom.id}/").status_code == 404
    assert client.get(f"{BASE}/classes/{classroom.id}/students/").status_code == 404
    assert (
        client.post(
            f"{BASE}/classes/{classroom.id}/students/",
            {"students": [{"first_name": "X"}]},
            format="json",
        ).status_code
        == 404
    )
    assert client.get(f"{BASE}/classes/{classroom.id}/attendance/").status_code == 404
    assert client.get(f"{BASE}/classes/{classroom.id}/gradebook/").status_code == 404
    assert client.patch(f"{BASE}/students/{student.id}/", {"first_name": "X"}).status_code == 404
    assert client.delete(f"{BASE}/students/{student.id}/").status_code == 404
    assert client.get(f"{BASE}/students/{student.id}/profile/").status_code == 404
    assert client.get(f"{BASE}/lesson-plans/{plan.id}/").status_code == 404
    assert client.patch(f"{BASE}/lesson-plans/{plan.id}/", {"title": "X"}).status_code == 404
    assert client.delete(f"{BASE}/lesson-plans/{plan.id}/").status_code == 404
    assert client.get(f"{BASE}/lesson-plans/{plan.id}/presentation/").status_code == 404
    assert client.patch(f"{BASE}/assessments/{assessment.id}/", {"title": "X"}).status_code == 404
    assert client.delete(f"{BASE}/assessments/{assessment.id}/").status_code == 404
    assert client.get(f"{BASE}/assessments/{assessment.id}/marks/").status_code == 404
    assert Classroom.objects.filter(pk=classroom.pk, name="Grade 5A").exists()


def test_a_pro_teacher_cannot_open_another_teachers_report_card(pro, other):
    student = _student(other, _class(other))

    assert pro.client.get(f"{BASE}/students/{student.id}/report-card/").status_code == 404


def test_lists_show_only_your_own_records(trial, other):
    _class(trial, "Mine")
    theirs = _class(other, "Theirs")
    _plan(other)
    _assessment(other, theirs)

    classes = trial.client.get(f"{BASE}/classes/").data
    assert [row["name"] for row in classes] == ["Mine"]
    assert trial.client.get(f"{BASE}/lesson-plans/").data["count"] == 0
    assert trial.client.get(f"{BASE}/assessments/").data == []


def test_another_teachers_class_cannot_be_linked(trial, other):
    theirs = _class(other)

    lesson = trial.client.post(
        f"{BASE}/lesson-plans/", {**LESSON, "classroom": theirs.id}, format="json"
    )
    assessment = trial.client.post(
        f"{BASE}/assessments/",
        {
            "classroom": theirs.id,
            "title": "Quiz",
            "max_marks": 10,
            "date": timezone.localdate().isoformat(),
        },
        format="json",
    )

    assert lesson.status_code == 400
    assert assessment.status_code == 400


def test_another_teachers_student_cannot_get_attendance_or_marks(trial, other):
    classroom = _class(trial)
    assessment = _assessment(trial, classroom)
    stranger = _student(other, _class(other))
    today = timezone.localdate().isoformat()

    attendance = trial.client.put(
        f"{BASE}/classes/{classroom.id}/attendance/",
        {"date": today, "records": [{"student": stranger.id, "status": "present"}]},
        format="json",
    )
    marks = trial.client.put(
        f"{BASE}/assessments/{assessment.id}/marks/",
        {"marks": [{"student": stranger.id, "value": "5"}]},
        format="json",
    )

    assert attendance.status_code == 400
    assert marks.status_code == 400
    assert not AttendanceRecord.objects.exists()
    assert not Mark.objects.exists()


# --- Workspace and setup


def test_workspace_reports_access_limits_and_usage(trial):
    classroom = _class(trial)
    _student(trial, classroom)

    response = trial.client.get(f"{BASE}/workspace/")

    assert response.status_code == 200
    assert response.data["access"]["tier"] == "trial"
    assert response.data["access"]["read_only"] is False
    assert response.data["access"]["days_left"] == 7
    assert response.data["limits"]["classes"] == 2
    assert response.data["usage"]["classes"] == 1
    assert response.data["usage"]["students"] == 1
    assert response.data["profile"] is None


def test_workspace_uses_a_small_fixed_number_of_queries(trial, django_assert_max_num_queries):
    for index in range(3):
        _student(trial, _class(trial, f"Class {index}"))

    with django_assert_max_num_queries(9):
        assert trial.client.get(f"{BASE}/workspace/").status_code == 200


def test_setup_saves_the_profile_and_can_be_changed(trial):
    details = {"subject": "Science", "grade_levels": "Grades 4-6"}

    assert trial.client.post(f"{BASE}/setup/", details).status_code == 201
    assert trial.client.post(f"{BASE}/setup/", {**details, "subject": "Math"}).status_code == 201

    assert TeacherProfile.objects.get(user=trial.user).subject == "Math"
    assert trial.client.get(f"{BASE}/workspace/").data["profile"]["subject"] == "Math"


@pytest.mark.parametrize("field", ["subject", "grade_levels"])
def test_setup_needs_every_field(trial, field):
    details = {"subject": "Science", "grade_levels": "Grades 4-6", field: ""}

    response = trial.client.post(f"{BASE}/setup/", details)

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]


# --- Classes


def test_class_can_be_created_read_updated_and_deleted(teacher):
    created = teacher.client.post(
        f"{BASE}/classes/", {"name": "Grade 6", "subject": "Math", "grade": "6"}
    )
    assert created.status_code == 201
    assert created.data["student_count"] == 0
    url = f"{BASE}/classes/{created.data['id']}/"

    assert teacher.client.get(url).data["name"] == "Grade 6"
    assert teacher.client.patch(url, {"name": "Grade 6B"}).data["name"] == "Grade 6B"
    assert teacher.client.delete(url).status_code == 204
    assert not Classroom.objects.exists()


def test_a_class_name_can_be_used_once_in_any_letter_case(teacher):
    _class(teacher, "Grade 6")
    second = _class(teacher, "Grade 7")

    created = teacher.client.post(f"{BASE}/classes/", {"name": "GRADE 6"})
    renamed = teacher.client.patch(f"{BASE}/classes/{second.id}/", {"name": "grade 6"})

    assert created.status_code == 400
    assert "name" in created.data["error"]["fields"]
    assert renamed.status_code == 400


def test_the_same_class_name_can_be_used_for_another_subject(teacher):
    teacher.client.post(f"{BASE}/classes/", {"name": "Grade 6", "subject": "Math"})

    science = teacher.client.post(f"{BASE}/classes/", {"name": "Grade 6", "subject": "Science"})
    repeated = teacher.client.post(
        f"{BASE}/classes/", {"name": "  grade   6 ", "subject": " MATH "}
    )

    assert science.status_code == 201
    assert repeated.status_code == 400
    assert str(repeated.data["error"]["fields"]["name"]) == (
        "You already have this class for this subject."
    )


def test_changing_only_the_subject_checks_for_a_repeat(teacher):
    teacher.client.post(f"{BASE}/classes/", {"name": "Grade 6", "subject": "Math"})
    science = teacher.client.post(f"{BASE}/classes/", {"name": "Grade 6", "subject": "Science"})

    response = teacher.client.patch(f"{BASE}/classes/{science.data['id']}/", {"subject": "math"})

    assert response.status_code == 400


def test_extra_spaces_are_removed_from_a_class(teacher):
    created = teacher.client.post(
        f"{BASE}/classes/", {"name": "  Grade   6 ", "subject": " Math ", "grade": " 6 "}
    )

    assert created.data["name"] == "Grade 6"
    assert created.data["subject"] == "Math"
    assert created.data["grade"] == "6"


def test_a_blank_class_name_is_rejected(teacher):
    assert teacher.client.post(f"{BASE}/classes/", {"name": "   "}).status_code == 400


def test_class_list_shows_tests_and_todays_attendance(teacher):
    taken = _class(teacher, "Taken")
    waiting = _class(teacher, "Waiting")
    ali, huda = _student(teacher, taken), _student(teacher, waiting, "Huda")
    _student(teacher, taken, "Omar")
    _assessment(teacher, taken)
    _assessment(teacher, taken)
    today = timezone.localdate()
    AttendanceRecord.objects.create(
        school=teacher.school, classroom=taken, student=ali, date=today, status="present"
    )
    AttendanceRecord.objects.create(
        school=teacher.school,
        classroom=waiting,
        student=huda,
        date=today - timedelta(days=1),
        status="present",
    )

    rows = {row["name"]: row for row in teacher.client.get(f"{BASE}/classes/").data}

    assert rows["Taken"]["student_count"] == 2
    assert rows["Taken"]["assessment_count"] == 2
    assert rows["Taken"]["attendance_taken_today"] is True
    assert rows["Waiting"]["student_count"] == 1
    assert rows["Waiting"]["assessment_count"] == 0
    assert rows["Waiting"]["attendance_taken_today"] is False


def test_two_teachers_can_use_the_same_class_name(trial, other):
    _class(other, "Grade 6")

    assert trial.client.post(f"{BASE}/classes/", {"name": "Grade 6"}).status_code == 201


def test_class_list_query_count_does_not_grow(trial, django_assert_max_num_queries):
    for index in range(12):
        _student(trial, _class(trial, f"Class {index}"))

    with django_assert_max_num_queries(6):
        response = trial.client.get(f"{BASE}/classes/")

    assert len(response.data) == 12
    assert response.data[0]["student_count"] == 1


# --- Students


def test_students_can_be_added_listed_updated_and_deleted(teacher):
    classroom = _class(teacher)
    url = f"{BASE}/classes/{classroom.id}/students/"

    added = teacher.client.post(
        url,
        {"students": [{"first_name": "Ali"}, {"first_name": "Huda", "parent_email": "p@x.com"}]},
        format="json",
    )
    assert added.status_code == 201
    assert [row["full_name"] for row in teacher.client.get(url).data] == ["Ali", "Huda"]

    student_id = added.data[0]["id"]
    updated = teacher.client.patch(f"{BASE}/students/{student_id}/", {"first_name": "Aly"})
    assert updated.data["full_name"] == "Aly"
    assert teacher.client.delete(f"{BASE}/students/{student_id}/").status_code == 204
    assert Student.objects.count() == 1


def test_students_keep_every_detail(teacher):
    classroom = _class(teacher)
    row = {
        "first_name": "  Ali ",
        "last_name": "Hassan  Khan",
        "father_name": "Hassan",
        "student_number": " S-01 ",
    }

    added = teacher.client.post(
        f"{BASE}/classes/{classroom.id}/students/", {"students": [row]}, format="json"
    )

    assert added.status_code == 201
    saved = added.data[0]
    assert saved["first_name"] == "Ali"
    assert saved["last_name"] == "Hassan Khan"
    assert saved["full_name"] == "Ali Hassan Khan"
    assert saved["father_name"] == "Hassan"
    assert saved["student_number"] == "S-01"


def _add(workspace, classroom, *rows):
    return workspace.client.post(
        f"{BASE}/classes/{classroom.id}/students/", {"students": list(rows)}, format="json"
    )


def test_a_student_id_can_be_used_once_in_a_class(teacher):
    classroom = _class(teacher)
    _add(teacher, classroom, {"first_name": "Ali", "student_number": "7"})

    response = _add(
        teacher,
        classroom,
        {"first_name": "Huda", "student_number": "8"},
        {"first_name": "Omar", "student_number": "7"},
    )

    assert response.status_code == 400
    rows = response.data["error"]["fields"]["students"]
    assert rows[0] == {}
    assert "student_number" in rows[1]
    assert Student.objects.count() == 1


def test_the_same_student_id_twice_in_one_list_is_rejected(teacher):
    classroom = _class(teacher)

    response = _add(
        teacher,
        classroom,
        {"first_name": "Ali", "student_number": "7"},
        {"first_name": "Huda", "student_number": "7"},
        {"first_name": "Omar"},
    )

    assert response.status_code == 400
    assert not Student.objects.exists()


def test_students_with_no_id_and_ids_in_other_classes_are_fine(teacher):
    first, second = _class(teacher, "A"), _class(teacher, "B")
    _add(teacher, first, {"first_name": "Ali", "student_number": "7"})

    response = _add(
        teacher,
        second,
        {"first_name": "Ali", "student_number": "7"},
        {"first_name": "Huda"},
        {"first_name": "Omar"},
    )

    assert response.status_code == 201


def test_editing_a_student_cannot_take_another_students_id(teacher):
    classroom = _class(teacher)
    Student.objects.create(
        school=teacher.school, classroom=classroom, first_name="Ali", student_number="7"
    )
    huda = _student(teacher, classroom, "Huda")

    response = teacher.client.patch(f"{BASE}/students/{huda.id}/", {"student_number": "7"})

    assert response.status_code == 400
    assert "student_number" in response.data["error"]["fields"]


@pytest.mark.parametrize(
    "students",
    [
        [],
        [{"first_name": ""}],
        [{"first_name": "Ali", "parent_email": "not-an-email"}],
        [{"first_name": "x" * 101}],
        [{"first_name": "Ali", "student_number": "x" * 31}],
    ],
)
def test_invalid_students_are_rejected(teacher, students):
    classroom = _class(teacher)

    response = teacher.client.post(
        f"{BASE}/classes/{classroom.id}/students/", {"students": students}, format="json"
    )

    assert response.status_code == 400
    assert not Student.objects.exists()


# --- Plan limits


def test_trial_class_limit(trial):
    _class(trial, "One")
    _class(trial, "Two")

    response = trial.client.post(f"{BASE}/classes/", {"name": "Three"})

    assert response.status_code == 403
    assert response.data["error"]["code"] == "plan_limit_reached"


def test_trial_student_limit_counts_the_whole_batch(trial):
    classroom = _class(trial)
    Student.objects.bulk_create(
        Student(school=trial.school, classroom=classroom, first_name=f"S{index}")
        for index in range(29)
    )

    response = trial.client.post(
        f"{BASE}/classes/{classroom.id}/students/",
        {"students": [{"first_name": "A"}, {"first_name": "B"}]},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "plan_limit_reached"
    assert Student.objects.count() == 29


def test_trial_lesson_plan_limit(trial):
    LessonPlan.objects.bulk_create(
        LessonPlan(school=trial.school, title=f"L{index}") for index in range(20)
    )

    response = trial.client.post(f"{BASE}/lesson-plans/", LESSON, format="json")

    assert response.status_code == 403
    assert response.data["error"]["code"] == "plan_limit_reached"


def test_teacher_plan_class_limit_is_higher_and_pro_has_none(teacher, pro):
    for index in range(5):
        _class(teacher, f"T{index}")
        _class(pro, f"P{index}")

    assert teacher.client.post(f"{BASE}/classes/", {"name": "Six"}).status_code == 403
    assert pro.client.post(f"{BASE}/classes/", {"name": "Six"}).status_code == 201


# --- Read-only after the trial


def test_an_ended_trial_can_read_but_not_change(expired):
    classroom = _class(expired)
    student = _student(expired, classroom)
    client = expired.client

    assert client.get(f"{BASE}/workspace/").data["access"]["read_only"] is True
    assert client.get(f"{BASE}/classes/").status_code == 200
    assert client.get(f"{BASE}/classes/{classroom.id}/students/").status_code == 200

    blocked = [
        client.post(f"{BASE}/classes/", {"name": "New"}),
        client.patch(f"{BASE}/classes/{classroom.id}/", {"name": "New"}),
        client.delete(f"{BASE}/classes/{classroom.id}/"),
        client.delete(f"{BASE}/students/{student.id}/"),
        client.post(f"{BASE}/lesson-plans/", LESSON, format="json"),
        client.post(f"{BASE}/setup/", {"subject": "A", "grade_levels": "B"}),
    ]
    assert {response.status_code for response in blocked} == {403}
    assert blocked[0].data["error"]["code"] == "workspace_read_only"
    assert Classroom.objects.filter(pk=classroom.pk, name="Grade 5A").exists()


def test_a_workspace_with_no_subscription_is_read_only(trial):
    trial.school.subscriptions.all().delete()

    assert trial.client.post(f"{BASE}/classes/", {"name": "New"}).status_code == 403


def test_an_ended_trial_can_still_ask_for_a_plan(expired):
    response = expired.client.post(f"{BASE}/upgrade-request/", {"plan": "teacher"})

    assert response.status_code == 201
    assert UpgradeRequest.objects.get().status == UpgradeRequest.Status.PENDING


# --- Attendance


def test_attendance_is_saved_and_can_be_corrected(teacher):
    classroom = _class(teacher)
    ali = _student(teacher, classroom, "Ali")
    huda = _student(teacher, classroom, "Huda")
    url = f"{BASE}/classes/{classroom.id}/attendance/"
    today = timezone.localdate().isoformat()

    first = teacher.client.put(
        url,
        {
            "date": today,
            "records": [
                {"student": ali.id, "status": "present"},
                {"student": huda.id, "status": "absent"},
            ],
        },
        format="json",
    )
    assert first.status_code == 204

    teacher.client.put(
        url,
        {"date": today, "records": [{"student": huda.id, "status": "late"}]},
        format="json",
    )

    roster = teacher.client.get(url, {"date": today}).data["students"]
    assert {row["full_name"]: row["status"] for row in roster} == {"Ali": "present", "Huda": "late"}
    assert AttendanceRecord.objects.count() == 2


def test_attendance_roster_shows_students_with_no_status_yet(teacher):
    classroom = _class(teacher)
    _student(teacher, classroom)

    response = teacher.client.get(f"{BASE}/classes/{classroom.id}/attendance/")

    assert response.data["date"] == timezone.localdate()
    assert response.data["students"][0]["status"] is None


def test_attendance_roster_query_count_does_not_grow(teacher, django_assert_max_num_queries):
    classroom = _class(teacher)
    Student.objects.bulk_create(
        Student(school=teacher.school, classroom=classroom, first_name=f"S{index}")
        for index in range(40)
    )

    with django_assert_max_num_queries(6):
        response = teacher.client.get(f"{BASE}/classes/{classroom.id}/attendance/")

    assert len(response.data["students"]) == 40


def test_attendance_cannot_be_saved_for_a_future_date(teacher):
    classroom = _class(teacher)
    student = _student(teacher, classroom)
    tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()

    response = teacher.client.put(
        f"{BASE}/classes/{classroom.id}/attendance/",
        {"date": tomorrow, "records": [{"student": student.id, "status": "present"}]},
        format="json",
    )

    assert response.status_code == 400
    assert "date" in response.data["error"]["fields"]


@pytest.mark.parametrize("status", ["unknown", ""])
def test_attendance_rejects_an_unknown_status(teacher, status):
    classroom = _class(teacher)
    student = _student(teacher, classroom)

    response = teacher.client.put(
        f"{BASE}/classes/{classroom.id}/attendance/",
        {
            "date": timezone.localdate().isoformat(),
            "records": [{"student": student.id, "status": status}],
        },
        format="json",
    )

    assert response.status_code == 400


def test_attendance_rejects_the_same_student_twice(teacher):
    classroom = _class(teacher)
    student = _student(teacher, classroom)

    response = teacher.client.put(
        f"{BASE}/classes/{classroom.id}/attendance/",
        {
            "date": timezone.localdate().isoformat(),
            "records": [
                {"student": student.id, "status": "present"},
                {"student": student.id, "status": "absent"},
            ],
        },
        format="json",
    )

    assert response.status_code == 400


def test_a_student_from_another_of_your_classes_is_rejected(teacher):
    classroom = _class(teacher, "A")
    elsewhere = _student(teacher, _class(teacher, "B"))

    response = teacher.client.put(
        f"{BASE}/classes/{classroom.id}/attendance/",
        {
            "date": timezone.localdate().isoformat(),
            "records": [{"student": elsewhere.id, "status": "present"}],
        },
        format="json",
    )

    assert response.status_code == 400


# --- Lesson plans


def test_lesson_plan_can_be_created_read_updated_and_deleted(teacher):
    classroom = _class(teacher)
    created = teacher.client.post(
        f"{BASE}/lesson-plans/", {**LESSON, "classroom": classroom.id}, format="json"
    )
    assert created.status_code == 201
    assert created.data["classroom_name"] == classroom.name
    assert created.data["source"] == "manual"
    url = f"{BASE}/lesson-plans/{created.data['id']}/"

    assert teacher.client.get(url).data["title"] == "Water cycle"
    assert teacher.client.patch(url, {"title": "Rain"}, format="json").data["title"] == "Rain"
    assert teacher.client.delete(url).status_code == 204
    assert not LessonPlan.objects.exists()


def test_lesson_plans_can_be_searched_and_filtered_by_class(teacher):
    classroom = _class(teacher)
    _plan(teacher, classroom=classroom)
    LessonPlan.objects.create(school=teacher.school, title="Fractions")

    found = teacher.client.get(f"{BASE}/lesson-plans/", {"search": "fract"}).data
    in_class = teacher.client.get(f"{BASE}/lesson-plans/", {"classroom": classroom.id}).data

    assert [row["title"] for row in found["results"]] == ["Fractions"]
    assert [row["title"] for row in in_class["results"]] == ["Lesson"]


def test_lesson_plan_list_query_count_does_not_grow(teacher, django_assert_max_num_queries):
    classroom = _class(teacher)
    LessonPlan.objects.bulk_create(
        LessonPlan(school=teacher.school, classroom=classroom, title=f"L{index}")
        for index in range(15)
    )

    with django_assert_max_num_queries(7):
        response = teacher.client.get(f"{BASE}/lesson-plans/")

    assert response.data["count"] == 15


@pytest.mark.parametrize(
    ("field", "value"),
    [("title", ""), ("title", "x" * 201), ("objectives", "x" * 5001), ("lesson_date", "soon")],
)
def test_invalid_lesson_plans_are_rejected(teacher, field, value):
    response = teacher.client.post(f"{BASE}/lesson-plans/", {**LESSON, field: value}, format="json")

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]


# --- PowerPoint


def _deck_text(content):
    from pptx import Presentation

    deck = Presentation(BytesIO(content))
    return [
        shape.text_frame.text
        for slide in deck.slides
        for shape in slide.shapes
        if shape.has_text_frame
    ]


def test_presentation_downloads_as_powerpoint(teacher):
    pytest.importorskip("pptx")
    plan = _plan(teacher, objectives="Explain rain", subject="Science")

    response = teacher.client.get(f"{BASE}/lesson-plans/{plan.id}/presentation/")

    assert response.status_code == 200
    assert "presentationml" in response["Content-Type"]
    assert 'filename="lesson.pptx"' in response["Content-Disposition"]
    text = " ".join(_deck_text(response.content))
    assert "Objectives" in text
    assert "Explain rain" in text
    assert "Made with Lesson Lab" not in text


def test_trial_presentation_has_the_mark_and_a_limit(trial):
    pytest.importorskip("pptx")
    plan = _plan(trial, objectives="Explain rain")
    url = f"{BASE}/lesson-plans/{plan.id}/presentation/"

    first = trial.client.get(url)
    assert "Made with Lesson Lab" in " ".join(_deck_text(first.content))

    PresentationExport.objects.bulk_create(
        PresentationExport(school=trial.school, lesson_plan=plan) for _ in range(9)
    )
    eleventh = trial.client.get(url)

    assert eleventh.status_code == 403
    assert eleventh.data["error"]["code"] == "plan_limit_reached"
    assert PresentationExport.objects.count() == 10


def _document(content):
    from docx import Document

    return Document(BytesIO(content))


def _document_text(document):
    footer = [p.text for p in document.sections[0].footer.paragraphs]
    return " ".join([p.text for p in document.paragraphs] + footer)


def test_lesson_plan_downloads_as_word(teacher):
    pytest.importorskip("docx")
    classroom = _class(teacher)
    plan = _plan(
        teacher,
        classroom=classroom,
        subject="Science",
        lesson_date=timezone.localdate().replace(day=5),
        objectives="Explain evaporation\nExplain rain",
        homework="Page 12",
    )

    response = teacher.client.get(f"{BASE}/lesson-plans/{plan.id}/document/")

    assert response.status_code == 200
    assert "wordprocessingml" in response["Content-Type"]
    assert response["Content-Disposition"].endswith('lesson.docx"')
    text = _document_text(_document(response.content))
    assert "Lesson" in text
    assert "Science" in text
    assert "Grade 5A" in text
    assert f"05/{timezone.localdate():%m/%Y}" in text
    assert "Objectives" in text and "Explain rain" in text
    # A section with nothing in it is left out.
    assert "Materials" not in text
    assert "Made with Lesson Lab" not in text
    # A Word download is not counted against the PowerPoint limit.
    assert not PresentationExport.objects.exists()


def test_trial_word_file_has_the_mark_and_no_limit(trial):
    pytest.importorskip("docx")
    plan = _plan(trial, objectives="Explain rain")
    PresentationExport.objects.bulk_create(
        PresentationExport(school=trial.school, lesson_plan=plan) for _ in range(10)
    )

    response = trial.client.get(f"{BASE}/lesson-plans/{plan.id}/document/")

    assert response.status_code == 200
    assert "Made with Lesson Lab" in _document_text(_document(response.content))


def test_an_ended_trial_can_still_download_word(expired):
    pytest.importorskip("docx")
    plan = _plan(expired, objectives="Explain rain")

    assert expired.client.get(f"{BASE}/lesson-plans/{plan.id}/document/").status_code == 200


def test_another_teachers_lesson_cannot_be_downloaded_as_word(trial, other):
    plan = _plan(other)

    assert trial.client.get(f"{BASE}/lesson-plans/{plan.id}/document/").status_code == 404


def test_arabic_word_file_is_right_to_left(teacher):
    pytest.importorskip("docx")
    plan = LessonPlan.objects.create(
        school=teacher.school, title="دورة الماء", objectives="شرح التبخر"
    )

    response = teacher.client.get(f"{BASE}/lesson-plans/{plan.id}/document/")

    document = _document(response.content)
    assert "الأهداف" in _document_text(document)
    body = document.element.body.xml
    assert "<w:bidi/>" in body
    assert "<w:rtl/>" in body


def test_arabic_presentation_is_right_to_left(teacher):
    pytest.importorskip("pptx")
    plan = LessonPlan.objects.create(
        school=teacher.school, title="دورة الماء", objectives="شرح التبخر"
    )

    response = teacher.client.get(f"{BASE}/lesson-plans/{plan.id}/presentation/")

    from pptx import Presentation

    deck = Presentation(BytesIO(response.content))
    paragraphs = [
        paragraph
        for slide in deck.slides
        for shape in slide.shapes
        if shape.has_text_frame
        for paragraph in shape.text_frame.paragraphs
        if paragraph.text
    ]
    assert all(paragraph._p.pPr.get("rtl") == "1" for paragraph in paragraphs)
    assert "الأهداف" in " ".join(_deck_text(response.content))


# --- Assessments and marks


def test_assessment_can_be_created_updated_and_deleted(teacher):
    classroom = _class(teacher)
    created = teacher.client.post(
        f"{BASE}/assessments/",
        {
            "classroom": classroom.id,
            "title": "Quiz",
            "max_marks": "20",
            "date": timezone.localdate().isoformat(),
        },
        format="json",
    )
    assert created.status_code == 201
    url = f"{BASE}/assessments/{created.data['id']}/"

    assert teacher.client.patch(url, {"title": "Test"}, format="json").data["title"] == "Test"
    assert (
        teacher.client.get(f"{BASE}/assessments/", {"classroom": classroom.id}).data[0]["title"]
        == "Test"
    )
    assert teacher.client.delete(url).status_code == 204


@pytest.mark.parametrize("max_marks", ["0", "-1", "abc"])
def test_assessment_needs_a_positive_maximum(teacher, max_marks):
    response = teacher.client.post(
        f"{BASE}/assessments/",
        {
            "classroom": _class(teacher).id,
            "title": "Quiz",
            "max_marks": max_marks,
            "date": timezone.localdate().isoformat(),
        },
        format="json",
    )

    assert response.status_code == 400
    assert "max_marks" in response.data["error"]["fields"]


def test_marks_are_saved_corrected_and_cleared(teacher):
    classroom = _class(teacher)
    ali = _student(teacher, classroom, "Ali")
    huda = _student(teacher, classroom, "Huda")
    assessment = _assessment(teacher, classroom)
    url = f"{BASE}/assessments/{assessment.id}/marks/"

    saved = teacher.client.put(
        url,
        {"marks": [{"student": ali.id, "value": "15.50"}, {"student": huda.id, "value": "18"}]},
        format="json",
    )
    assert saved.status_code == 204

    teacher.client.put(
        url,
        {"marks": [{"student": ali.id, "value": "16"}, {"student": huda.id, "value": None}]},
        format="json",
    )

    sheet = teacher.client.get(url).data["students"]
    assert {row["full_name"]: row["value"] for row in sheet} == {"Ali": "16.00", "Huda": None}
    assert Mark.objects.get().value == Decimal("16.00")


@pytest.mark.parametrize("value", ["21", "-1", "abc"])
def test_a_mark_outside_the_range_is_rejected(teacher, value):
    classroom = _class(teacher)
    student = _student(teacher, classroom)
    assessment = _assessment(teacher, classroom)

    response = teacher.client.put(
        f"{BASE}/assessments/{assessment.id}/marks/",
        {"marks": [{"student": student.id, "value": value}]},
        format="json",
    )

    assert response.status_code == 400
    assert not Mark.objects.exists()


def test_the_maximum_cannot_drop_below_a_saved_mark(teacher):
    classroom = _class(teacher)
    student = _student(teacher, classroom)
    assessment = _assessment(teacher, classroom)
    Mark.objects.create(school=teacher.school, assessment=assessment, student=student, value=18)

    response = teacher.client.patch(
        f"{BASE}/assessments/{assessment.id}/", {"max_marks": "10"}, format="json"
    )

    assert response.status_code == 400
    assert "max_marks" in response.data["error"]["fields"]


def test_gradebook_lists_every_student_and_assessment(teacher):
    classroom = _class(teacher)
    ali = _student(teacher, classroom, "Ali")
    _student(teacher, classroom, "Huda")
    assessment = _assessment(teacher, classroom)
    Mark.objects.create(school=teacher.school, assessment=assessment, student=ali, value=15)

    response = teacher.client.get(f"{BASE}/classes/{classroom.id}/gradebook/")

    assert response.data["assessments"][0]["title"] == "Quiz 1"
    assert response.data["students"][0]["marks"] == {str(assessment.id): "15.00"}
    assert response.data["students"][1]["marks"] == {}


def test_gradebook_query_count_does_not_grow(teacher, django_assert_max_num_queries):
    classroom = _class(teacher)
    students = Student.objects.bulk_create(
        Student(school=teacher.school, classroom=classroom, first_name=f"S{index}")
        for index in range(25)
    )
    assessment = _assessment(teacher, classroom)
    Mark.objects.bulk_create(
        Mark(school=teacher.school, assessment=assessment, student=student, value=10)
        for student in students
    )

    with django_assert_max_num_queries(8):
        response = teacher.client.get(f"{BASE}/classes/{classroom.id}/gradebook/")

    assert len(response.data["students"]) == 25


# --- AI lesson plans


@patch("apps.classroom.services.generate_lesson_content", return_value=AI_LESSON)
@pytest.mark.parametrize("workspace", ["trial", "teacher", "pro"])
def test_every_plan_can_make_an_ai_draft(generate, workspace, request):
    client = request.getfixturevalue(workspace).client

    response = client.post(f"{BASE}/lesson-plans/generate/", GENERATE, format="json")

    assert response.status_code == 200
    assert response.data["title"] == "Fractions"
    assert response.data["subject"] == "Math"
    assert AIGeneration.objects.count() == 1
    # A draft only: nothing is saved until the teacher saves it.
    assert not LessonPlan.objects.exists()
    generate.assert_called_once_with(topic="Fractions", subject="Math", grade="5", language="en")


@patch("apps.classroom.services.generate_lesson_content", return_value=AI_LESSON)
def test_a_saved_ai_draft_is_marked_as_ai(_generate, teacher):
    draft = teacher.client.post(f"{BASE}/lesson-plans/generate/", GENERATE, format="json").data

    saved = teacher.client.post(
        f"{BASE}/lesson-plans/",
        {**draft, "title": "Fractions, edited", "source": "ai"},
        format="json",
    )

    assert saved.status_code == 201
    assert saved.data["source"] == "ai"
    assert LessonPlan.objects.get().title == "Fractions, edited"


@patch("apps.classroom.services.generate_lesson_content", return_value=AI_LESSON)
def test_the_trial_has_ten_ai_drafts_in_all(generate, trial):
    old = timezone.now() - timedelta(days=40)
    AIGeneration.objects.bulk_create(AIGeneration(school=trial.school) for _ in range(10))
    # Counted over the whole trial, not only this month.
    AIGeneration.objects.update(created_at=old)

    response = trial.client.post(f"{BASE}/lesson-plans/generate/", GENERATE, format="json")

    assert response.status_code == 403
    assert response.data["error"]["code"] == "ai_quota_reached"
    assert trial.client.get(f"{BASE}/workspace/").data["usage"]["ai_used"] == 10
    generate.assert_not_called()


@patch("apps.classroom.services.generate_lesson_content", return_value=AI_LESSON)
@pytest.mark.parametrize(("workspace", "allowance"), [("teacher", 30), ("pro", 100)])
def test_paid_plans_have_a_monthly_ai_allowance(generate, workspace, allowance, request):
    client = request.getfixturevalue(workspace)
    AIGeneration.objects.bulk_create(AIGeneration(school=client.school) for _ in range(allowance))

    response = client.client.post(f"{BASE}/lesson-plans/generate/", GENERATE, format="json")

    assert response.status_code == 403
    assert response.data["error"]["code"] == "ai_quota_reached"
    generate.assert_not_called()


@patch("apps.classroom.services.generate_lesson_content", return_value=AI_LESSON)
def test_last_months_ai_drafts_do_not_count_on_a_paid_plan(_generate, teacher):
    AIGeneration.objects.bulk_create(AIGeneration(school=teacher.school) for _ in range(30))
    AIGeneration.objects.update(created_at=timezone.now() - timedelta(days=40))

    response = teacher.client.post(f"{BASE}/lesson-plans/generate/", GENERATE, format="json")

    assert response.status_code == 200
    assert teacher.client.get(f"{BASE}/workspace/").data["usage"]["ai_used"] == 1


@patch("apps.classroom.services.generate_lesson_content", return_value=AI_LESSON)
def test_no_ai_draft_when_no_lesson_plan_can_be_saved(generate, trial):
    LessonPlan.objects.bulk_create(
        LessonPlan(school=trial.school, title=f"L{index}") for index in range(20)
    )

    response = trial.client.post(f"{BASE}/lesson-plans/generate/", GENERATE, format="json")

    assert response.status_code == 403
    assert response.data["error"]["code"] == "plan_limit_reached"
    generate.assert_not_called()


@patch("apps.classroom.services.generate_lesson_content", return_value=AI_LESSON)
def test_an_ended_trial_cannot_make_ai_drafts(generate, expired):
    response = expired.client.post(f"{BASE}/lesson-plans/generate/", GENERATE, format="json")

    assert response.status_code == 403
    assert response.data["error"]["code"] == "workspace_read_only"
    generate.assert_not_called()


@patch(
    "apps.classroom.services.generate_lesson_content",
    side_effect=LessonAiUnavailable("down"),
)
def test_an_ai_failure_uses_no_allowance(_generate, pro):
    response = pro.client.post(f"{BASE}/lesson-plans/generate/", GENERATE, format="json")

    assert response.status_code == 503
    assert not AIGeneration.objects.exists()
    assert not LessonPlan.objects.exists()


@pytest.mark.parametrize("field", ["topic", "subject", "grade", "language"])
def test_ai_needs_every_field(pro, field):
    response = pro.client.post(
        f"{BASE}/lesson-plans/generate/", {**GENERATE, field: ""}, format="json"
    )

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]


# --- Teacher Pro: report cards


@pytest.mark.parametrize("workspace", ["trial", "teacher"])
def test_report_cards_need_teacher_pro(workspace, request):
    chosen = request.getfixturevalue(workspace)
    student = _student(chosen, _class(chosen))

    response = chosen.client.get(f"{BASE}/students/{student.id}/report-card/")

    assert response.status_code == 403
    assert response.data["error"]["code"] == "pro_required"


@patch("apps.classroom.documents.html_to_pdf", return_value=b"%PDF-1.7")
def test_report_card_contains_the_students_results(to_pdf, pro):
    classroom = _class(pro)
    student = _student(pro, classroom, "Ali <b>")
    assessment = _assessment(pro, classroom)
    Mark.objects.create(school=pro.school, assessment=assessment, student=student, value=15)
    AttendanceRecord.objects.create(
        school=pro.school,
        classroom=classroom,
        student=student,
        date=timezone.localdate(),
        status="present",
    )

    response = pro.client.get(f"{BASE}/students/{student.id}/report-card/", {"language": "ar"})

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    html = to_pdf.call_args.args[0]
    assert 'dir="rtl"' in html
    assert "Quiz 1" in html
    assert "75%" in html
    assert "Ali &lt;b&gt;" in html


@patch("apps.classroom.documents.html_to_pdf", side_effect=PdfUnavailable("no pango"))
def test_report_card_says_when_pdf_is_unavailable(_to_pdf, pro):
    student = _student(pro, _class(pro))

    response = pro.client.get(f"{BASE}/students/{student.id}/report-card/")

    assert response.status_code == 503


# --- Teacher Pro: messages to parents


def test_messages_need_teacher_pro(teacher):
    classroom = _class(teacher)

    response = teacher.client.post(
        f"{BASE}/messages/",
        {"classroom": classroom.id, "subject": "Test", "body": "Hello"},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "pro_required"


def test_a_message_reaches_each_parent_once(pro, django_capture_on_commit_callbacks):
    classroom = _class(pro)
    _student(pro, classroom, "Ali", "parent@example.com")
    _student(pro, classroom, "Huda", "parent@example.com")
    _student(pro, classroom, "Sami", "other@example.com")
    _student(pro, classroom, "Noura")

    with django_capture_on_commit_callbacks(execute=True):
        response = pro.client.post(
            f"{BASE}/messages/",
            {"classroom": classroom.id, "subject": "Test next week", "body": "Please revise."},
            format="json",
        )

    assert response.status_code == 201
    assert response.data["recipient_count"] == 2
    assert sorted(message.to[0] for message in mail.outbox) == [
        "other@example.com",
        "parent@example.com",
    ]
    assert pro.client.get(f"{BASE}/messages/").data["count"] == 1


def test_a_message_needs_a_parent_email(pro):
    classroom = _class(pro)
    _student(pro, classroom)

    response = pro.client.post(
        f"{BASE}/messages/",
        {"classroom": classroom.id, "subject": "Test", "body": "Hello"},
        format="json",
    )

    assert response.status_code == 400
    assert not ParentMessage.objects.exists()


@pytest.mark.parametrize(("field", "value"), [("subject", ""), ("body", ""), ("body", "x" * 3001)])
def test_invalid_messages_are_rejected(pro, field, value):
    classroom = _class(pro)
    _student(pro, classroom, "Ali", "parent@example.com")
    details = {"classroom": classroom.id, "subject": "Test", "body": "Hello", field: value}

    response = pro.client.post(f"{BASE}/messages/", details, format="json")

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]


# --- Upgrade requests


def test_asking_again_updates_the_same_request(trial):
    trial.client.post(f"{BASE}/upgrade-request/", {"plan": "teacher"})
    trial.client.post(f"{BASE}/upgrade-request/", {"plan": "teacher_pro", "note": "Please call"})

    upgrade = UpgradeRequest.objects.get()
    assert upgrade.plan == "teacher_pro"
    assert trial.client.get(f"{BASE}/workspace/").data["pending_upgrade"] == {"plan": "teacher_pro"}


@pytest.mark.parametrize("plan", ["", "school", "basic"])
def test_upgrade_needs_a_teacher_plan(trial, plan):
    response = trial.client.post(f"{BASE}/upgrade-request/", {"plan": plan})

    assert response.status_code == 400
    assert not UpgradeRequest.objects.exists()


# --- Student profile


def _profile(workspace, student, period=""):
    query = f"?period={period}" if period else ""
    return workspace.client.get(f"{BASE}/students/{student.id}/profile/{query}")


def _attendance(workspace, student, days_ago, status):
    AttendanceRecord.objects.create(
        school=workspace.school,
        classroom=student.classroom,
        student=student,
        date=timezone.localdate() - timedelta(days=days_ago),
        status=status,
    )


def test_student_profile_shows_attendance_and_marks(teacher):
    classroom = _class(teacher)
    ali, huda = _student(teacher, classroom, "Ali Khan"), _student(teacher, classroom, "Huda")
    for days_ago, status in [(0, "present"), (1, "absent"), (2, "late"), (3, "excused")]:
        _attendance(teacher, ali, days_ago, status)
    quiz = _assessment(teacher, classroom, max_marks=20)
    unmarked = _assessment(teacher, classroom, max_marks=10)
    Mark.objects.create(school=teacher.school, assessment=quiz, student=ali, value=15)
    Mark.objects.create(school=teacher.school, assessment=quiz, student=huda, value=5)

    response = _profile(teacher, ali)

    assert response.status_code == 200
    data = response.data
    assert data["student"]["full_name"] == "Ali Khan"
    assert data["student"]["classroom_name"] == "Grade 5A"
    assert data["period"] == "month"
    attendance = data["attendance"]
    assert (attendance["present"], attendance["absent"], attendance["late"]) == (1, 1, 1)
    assert attendance["excused"] == 1
    assert attendance["total"] == 4
    # Late and excused days count as attended; only the absent day counts against.
    assert attendance["rate"] == "75.0"
    assert attendance["days"][0] == {
        "date": timezone.localdate().isoformat(),
        "status": "present",
    }
    marks = {row["id"]: row for row in data["marks"]}
    assert marks[quiz.id]["value"] == "15.00"
    assert marks[quiz.id]["percent"] == "75.0"
    assert marks[quiz.id]["class_average_percent"] == "50.0"
    assert marks[unmarked.id]["value"] is None
    assert marks[unmarked.id]["percent"] is None
    assert data["average_percent"] == "75.0"


def test_student_profile_period_limits_what_is_shown(teacher):
    ali = _student(teacher, _class(teacher))
    _attendance(teacher, ali, 60, "absent")

    assert _profile(teacher, ali).data["attendance"]["total"] == 0
    assert _profile(teacher, ali, "90days").data["attendance"]["total"] == 1
    assert _profile(teacher, ali, "all").data["attendance"]["total"] == 1
    assert _profile(teacher, ali, "all").data["start"] is None


def test_an_empty_student_profile_has_no_rates(teacher):
    data = _profile(teacher, _student(teacher, _class(teacher))).data

    assert data["attendance"]["rate"] is None
    assert data["average_percent"] is None
    assert data["marks"] == []


def test_student_profile_rejects_an_unknown_period(teacher):
    response = _profile(teacher, _student(teacher, _class(teacher)), "year")

    assert response.status_code == 400


def test_student_profile_is_open_on_every_plan(trial, expired):
    assert _profile(trial, _student(trial, _class(trial))).status_code == 200
    assert _profile(expired, _student(expired, _class(expired))).status_code == 200


def test_student_profile_query_count_does_not_grow(teacher, django_assert_max_num_queries):
    classroom = _class(teacher)
    ali = _student(teacher, classroom)
    for index in range(10):
        assessment = _assessment(teacher, classroom)
        Mark.objects.create(school=teacher.school, assessment=assessment, student=ali, value=index)
        _attendance(teacher, ali, index, "present")

    with django_assert_max_num_queries(9):
        response = _profile(teacher, ali)

    assert len(response.data["marks"]) == 10
