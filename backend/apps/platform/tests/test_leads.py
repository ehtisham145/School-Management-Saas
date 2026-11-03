import pytest
from django.contrib.admin.sites import site
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import User
from apps.platform.models import ContactMessage, DemoRequest

DEMO_URL = "/api/platform/demo-requests/"
CONTACT_URL = "/api/platform/contact-messages/"
VALID_DEMO = {
    "name": "Sara Ahmed",
    "school_name": "Al Noor School",
    "email": "sara@alnoor.example",
    "phone": "+966 50 123 4567",
    "plan": "premium",
    "message": "We have 400 students.",
}
VALID_CONTACT = {
    "name": "Omar",
    "school_name": "",
    "email": "omar@example.com",
    "message": "How do I get started?",
}

pytestmark = pytest.mark.django_db


def test_demo_request_is_saved(api_client):
    response = api_client.post(DEMO_URL, VALID_DEMO)

    assert response.status_code == 201
    demo = DemoRequest.objects.get()
    assert demo.school_name == "Al Noor School"
    assert demo.plan == "premium"
    assert demo.is_handled is False


def test_demo_request_needs_only_name_school_and_email(api_client):
    response = api_client.post(
        DEMO_URL, {"name": "A", "school_name": "B", "email": "a@example.com"}
    )

    assert response.status_code == 201
    assert DemoRequest.objects.count() == 1


def test_demo_request_emails_the_team(api_client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        api_client.post(DEMO_URL, VALID_DEMO)

    message = mail.outbox[0]
    assert message.to == ["info@lessonlab.me"]
    assert message.reply_to == [VALID_DEMO["email"]]
    assert "Al Noor School" in message.subject
    assert "+966 50 123 4567" in message.body


@override_settings(LEADS_EMAIL="sales@example.com")
def test_team_address_comes_from_settings(api_client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        api_client.post(DEMO_URL, VALID_DEMO)

    assert mail.outbox[0].to == ["sales@example.com"]


def test_line_breaks_cannot_inject_email_headers(api_client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            DEMO_URL, {**VALID_DEMO, "school_name": "School\nBcc: victim@example.com"}
        )

    assert response.status_code == 201
    assert "\n" not in mail.outbox[0].subject
    assert mail.outbox[0].bcc == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", "x" * 121),
        ("school_name", ""),
        ("email", "not-an-email"),
        ("phone", "abc"),
        ("plan", "free"),
    ],
)
def test_demo_request_rejects_invalid_fields(api_client, field, value):
    response = api_client.post(DEMO_URL, {**VALID_DEMO, field: value})

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert field in response.data["error"]["fields"]
    assert not DemoRequest.objects.exists()


def test_contact_message_is_saved_and_emailed(api_client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(CONTACT_URL, VALID_CONTACT)

    assert response.status_code == 201
    assert ContactMessage.objects.get().message == VALID_CONTACT["message"]
    assert mail.outbox[0].reply_to == [VALID_CONTACT["email"]]


@pytest.mark.parametrize(
    ("field", "value"), [("name", ""), ("email", "bad"), ("message", ""), ("message", "x" * 2001)]
)
def test_contact_message_rejects_invalid_fields(api_client, field, value):
    response = api_client.post(CONTACT_URL, {**VALID_CONTACT, field: value})

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]
    assert not ContactMessage.objects.exists()


@pytest.mark.parametrize(
    ("url", "body", "model"),
    [(DEMO_URL, VALID_DEMO, DemoRequest), (CONTACT_URL, VALID_CONTACT, ContactMessage)],
)
def test_filled_honeypot_looks_successful_but_saves_nothing(
    api_client, django_capture_on_commit_callbacks, url, body, model
):
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(url, {**body, "website": "http://spam.example"})

    assert response.status_code == 201
    assert not model.objects.exists()
    assert mail.outbox == []


@pytest.mark.parametrize(("url", "body"), [(DEMO_URL, VALID_DEMO), (CONTACT_URL, VALID_CONTACT)])
def test_public_forms_are_throttled(api_client, monkeypatch, url, body):
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "leads", "2/hour")

    assert api_client.post(url, body).status_code == 201
    assert api_client.post(url, body).status_code == 201
    response = api_client.post(url, body)

    assert response.status_code == 429
    assert response.data["error"]["code"] == "throttled"


@pytest.mark.parametrize(("url", "body"), [(DEMO_URL, VALID_DEMO), (CONTACT_URL, VALID_CONTACT)])
def test_a_logged_in_visitor_can_submit_without_a_csrf_token(url, body):
    user = User.objects.create_user("visitor", password="correct-pass123")
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    assert client.post(url, body, format="json").status_code == 201


@pytest.mark.parametrize("url", [DEMO_URL, CONTACT_URL])
def test_leads_cannot_be_read_through_the_api(api_client, url):
    DemoRequest.objects.create(name="A", school_name="B", email="a@example.com")

    assert api_client.get(url).status_code == 405


def test_submissions_are_listed_in_django_admin_without_add_permission(rf):
    for model in (DemoRequest, ContactMessage):
        assert model in site._registry
        assert site._registry[model].has_add_permission(rf.get("/")) is False
