import os
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.integrations.pdf.renderer import PdfUnavailable, html_to_pdf
from apps.platform.models import DemoRequest, Plan
from apps.tenancy.models import Membership

PASSWORD = "correct-pass123"  # noqa: S105


def signed_in(user):
    client = APIClient()
    response = client.post("/api/auth/login/", {"username": user.username, "password": PASSWORD})
    assert response.status_code == 200
    return client


@pytest.fixture
def platform_admin(db):
    return User.objects.create_user(
        "platform", password=PASSWORD, email="owner@lessonlab.example", is_platform_admin=True
    )


@pytest.fixture
def platform_client(platform_admin):
    return signed_in(platform_admin)


@pytest.fixture
def school_admin_client(two_schools):
    user = User.objects.create_user("head", password=PASSWORD)
    Membership.objects.create(school=two_schools[0], user=user, role=Membership.Role.SCHOOL_ADMIN)
    return signed_in(user)


@pytest.fixture
def basic_plan(db):
    return Plan.objects.create(
        code="basic",
        name_en="Basic",
        name_ar="الأساسية",
        monthly_price=Decimal("1500.00"),
        yearly_price=Decimal("15000.00"),
        max_students=300,
    )


@pytest.fixture
def demo_request(db):
    return DemoRequest.objects.create(
        name="Sara Ahmed", school_name="Al Noor School", email="sara@alnoor.example"
    )


def _pdf_available():
    try:
        html_to_pdf("<p>check</p>")
    except PdfUnavailable:
        return False
    return True


@pytest.fixture
def requires_pdf():
    """Skips a test on a machine without Pango. CI sets REQUIRE_PDF, so there it fails."""
    if not _pdf_available():
        if os.environ.get("REQUIRE_PDF"):
            pytest.fail("WeasyPrint can't load, and REQUIRE_PDF is set")
        pytest.skip("WeasyPrint can't load on this machine (Pango missing)")


@pytest.fixture
def fake_pdf(monkeypatch):
    """Replaces the PDF renderer, for tests about everything around the PDF."""
    monkeypatch.setattr(
        "apps.platform.documents.html_to_pdf", lambda html: b"%PDF-1.7 fake " + html[:20].encode()
    )
