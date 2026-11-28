"""The individual teacher's app shows only the AI tools. Classes and everything built on
them belong to the school plan (ADR-0027). Their data is kept, not deleted."""

from io import BytesIO

import pytest
from django.utils import timezone

from apps.classroom.models import Assessment, Classroom, LessonPlan, Student

pytestmark = pytest.mark.django_db

BASE = "/api/classroom"


@pytest.fixture(autouse=True)
def classes_off(settings, classes_on):
    # Runs after conftest's classes_on, so the real setting is the one tested here.
    settings.TEACHER_CLASSES_ENABLED = False


def _class(workspace):
    return Classroom.objects.create(school=workspace.school, name="Grade 5A")


@pytest.mark.parametrize("workspace", ["trial", "teacher", "pro"])
def test_class_features_say_they_belong_to_the_school_plan(workspace, request):
    chosen = request.getfixturevalue(workspace)
    classroom = _class(chosen)
    student = Student.objects.create(school=chosen.school, classroom=classroom, first_name="Ali")
    assessment = Assessment.objects.create(
        school=chosen.school,
        classroom=classroom,
        title="Quiz",
        max_marks=10,
        date=timezone.localdate(),
    )
    client = chosen.client

    responses = [
        client.get(f"{BASE}/classes/"),
        client.post(f"{BASE}/classes/", {"name": "Grade 6"}, format="json"),
        client.get(f"{BASE}/classes/{classroom.id}/students/"),
        client.get(f"{BASE}/classes/{classroom.id}/attendance/"),
        client.get(f"{BASE}/students/{student.id}/profile/"),
        client.get(f"{BASE}/students/{student.id}/report-card/"),
        client.get(f"{BASE}/assessments/"),
        client.get(f"{BASE}/assessments/{assessment.id}/marks/"),
        client.get(f"{BASE}/messages/"),
        client.post(
            f"{BASE}/messages/",
            {"classroom": classroom.id, "subject": "Hi", "body": "Hello"},
            format="json",
        ),
    ]

    assert [response.status_code for response in responses] == [403] * len(responses)
    assert {response.data["error"]["code"] for response in responses} == {"school_plan_only"}
    assert Classroom.objects.count() == 1


def test_existing_class_data_is_kept(teacher):
    classroom = _class(teacher)
    Student.objects.create(school=teacher.school, classroom=classroom, first_name="Ali")

    teacher.client.get(f"{BASE}/classes/")

    assert Classroom.objects.filter(pk=classroom.pk).exists()
    assert Student.objects.count() == 1


def test_signed_out_visitors_still_get_the_usual_answer(api_client):
    assert api_client.get(f"{BASE}/classes/").status_code == 403


def test_the_workspace_tells_the_app_that_classes_are_off(teacher):
    response = teacher.client.get(f"{BASE}/workspace/")

    assert response.status_code == 200
    assert response.data["features"]["classes"] is False


def test_the_workspace_says_when_classes_are_on(teacher, settings):
    settings.TEACHER_CLASSES_ENABLED = True

    assert teacher.client.get(f"{BASE}/workspace/").data["features"]["classes"] is True


def test_the_workspace_says_whether_the_agent_is_on_and_its_allowance(teacher, settings):
    settings.BROWSER_AGENT_ENABLED = False
    data = teacher.client.get(f"{BASE}/workspace/").data
    assert data["features"]["agent"] is False
    assert data["limits"]["agent_tasks"] == 20

    settings.BROWSER_AGENT_ENABLED = True
    assert teacher.client.get(f"{BASE}/workspace/").data["features"]["agent"] is True


@pytest.mark.parametrize("workspace", ["trial", "teacher", "pro"])
def test_the_ai_tools_still_work(workspace, request):
    chosen = request.getfixturevalue(workspace)
    client = chosen.client

    lesson = client.post(f"{BASE}/lesson-plans/", {"title": "Water cycle"}, format="json")

    assert lesson.status_code == 201
    assert client.get(f"{BASE}/lesson-plans/").status_code == 200
    assert client.get(f"{BASE}/exams/").status_code == 200
    assert client.get(f"{BASE}/exam-options/").status_code == 200
    assert client.get(f"{BASE}/workspace/").status_code == 200


# --- Branding on the files


def _deck_text(content):
    from pptx import Presentation

    deck = Presentation(BytesIO(content))
    return " ".join(
        shape.text_frame.text
        for slide in deck.slides
        for shape in slide.shapes
        if shape.has_text_frame
    )


def test_a_paid_presentation_carries_the_brand_and_the_teacher(teacher):
    pytest.importorskip("pptx")
    plan = LessonPlan.objects.create(
        school=teacher.school, title="Water cycle", objectives="Explain rain"
    )

    response = teacher.client.get(f"{BASE}/lesson-plans/{plan.id}/presentation/")

    text = _deck_text(response.content)
    assert "Lesson Lab" in text
    assert "Prepared by Tariq" in text
    assert "Made with Lesson Lab" not in text


def test_a_trial_presentation_carries_the_trial_mark(trial):
    pytest.importorskip("pptx")
    plan = LessonPlan.objects.create(
        school=trial.school, title="Water cycle", objectives="Explain rain"
    )

    response = trial.client.get(f"{BASE}/lesson-plans/{plan.id}/presentation/")

    assert "Made with Lesson Lab · Sara" in _deck_text(response.content)


def test_an_arabic_presentation_names_the_teacher_in_arabic(teacher):
    pytest.importorskip("pptx")
    plan = LessonPlan.objects.create(
        school=teacher.school, title="دورة الماء", objectives="شرح التبخر"
    )

    response = teacher.client.get(f"{BASE}/lesson-plans/{plan.id}/presentation/")

    assert "إعداد: Tariq" in _deck_text(response.content)


def test_the_word_lesson_plan_names_the_teacher_and_the_brand(teacher):
    docx = pytest.importorskip("docx")
    plan = LessonPlan.objects.create(
        school=teacher.school, title="Water cycle", objectives="Explain rain"
    )

    response = teacher.client.get(f"{BASE}/lesson-plans/{plan.id}/document/")

    document = docx.Document(BytesIO(response.content))
    body = "\n".join(paragraph.text for paragraph in document.paragraphs)
    footer = document.sections[0].footer.paragraphs[0].text
    assert "Teacher: Tariq" in body
    assert footer == "Lesson Lab"


def test_an_arabic_teacher_name_does_not_turn_an_english_lesson_right_to_left(teacher):
    docx = pytest.importorskip("docx")
    teacher.user.first_name = "طارق"
    teacher.user.save(update_fields=["first_name"])
    plan = LessonPlan.objects.create(
        school=teacher.school, title="Water cycle", objectives="Explain rain"
    )

    response = teacher.client.get(f"{BASE}/lesson-plans/{plan.id}/document/")

    document = docx.Document(BytesIO(response.content))
    assert "Objectives" in "\n".join(paragraph.text for paragraph in document.paragraphs)
