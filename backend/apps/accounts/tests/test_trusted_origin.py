import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "Blue-river-2026!"  # noqa: S105
LOGIN = {"username": "sara@example.com", "password": PASSWORD}
SIGNUP = {
    "full_name": "Sara Ahmed",
    "email": "new@example.com",
    "password": PASSWORD,
    "accept_privacy": True,
}
PUBLIC_ENDPOINTS = [
    ("/api/auth/login/", LOGIN),
    ("/api/auth/teacher-signup/request/", SIGNUP),
    ("/api/auth/teacher-signup/verify/", {**SIGNUP, "code": "123456"}),
    ("/api/auth/password/reset/request/", {"email": "sara@example.com"}),
    (
        "/api/auth/password/reset/confirm/",
        {"email": "sara@example.com", "code": "123456", "password": PASSWORD},
    ),
]


@pytest.fixture(autouse=True)
def account():
    return User.objects.create_user("sara@example.com", email="sara@example.com", password=PASSWORD)


@pytest.mark.parametrize(("path", "body"), PUBLIC_ENDPOINTS)
@pytest.mark.parametrize("origin", ["https://evil.example", "null"])
def test_another_website_is_refused(path, body, origin):
    response = APIClient().post(path, body, format="json", HTTP_ORIGIN=origin)

    assert response.status_code == 403
    assert response.data["error"]["code"] == "permission_denied"


def test_a_form_on_another_website_cannot_sign_a_visitor_in():
    client = APIClient()

    response = client.post(
        "/api/auth/login/", LOGIN, format="multipart", HTTP_ORIGIN="https://evil.example"
    )

    assert response.status_code == 403
    assert "sessionid" not in client.cookies


def test_the_websites_own_origin_can_sign_in():
    origin = settings.CSRF_TRUSTED_ORIGINS[0]

    response = APIClient().post("/api/auth/login/", LOGIN, format="json", HTTP_ORIGIN=origin)

    assert response.status_code == 200


def test_the_origin_is_compared_in_any_letter_case():
    origin = settings.CSRF_TRUSTED_ORIGINS[0].upper()

    response = APIClient().post("/api/auth/login/", LOGIN, format="json", HTTP_ORIGIN=origin)

    assert response.status_code == 200


def test_the_host_serving_the_request_is_trusted():
    response = APIClient().post(
        "/api/auth/login/", LOGIN, format="json", HTTP_ORIGIN="http://testserver"
    )

    assert response.status_code == 200


def test_a_lookalike_of_a_trusted_origin_is_refused():
    origin = f"{settings.CSRF_TRUSTED_ORIGINS[0]}.evil.example"

    response = APIClient().post("/api/auth/login/", LOGIN, format="json", HTTP_ORIGIN=origin)

    assert response.status_code == 403


def test_a_client_that_is_not_a_browser_can_sign_in():
    assert APIClient().post("/api/auth/login/", LOGIN, format="json").status_code == 200


def test_a_session_lasts_twelve_hours():
    client = APIClient()

    client.post("/api/auth/login/", LOGIN, format="json")

    assert client.cookies["sessionid"]["max-age"] == 12 * 60 * 60
