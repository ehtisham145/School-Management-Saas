from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.platform.documents import hijri_date, render_quotation_html, render_quotation_pdf
from apps.platform.models import DemoRequest, Quotation
from apps.platform.services import quotation_totals
from apps.platform.tasks import send_quotation_email_task
from apps.tenancy.models import School

QUOTATIONS_URL = "/api/platform/quotations/"
ITEMS = [
    {"description": "Premium plan, 12 months", "quantity": 1, "unit_price": "30000.00"},
    {"description": "Onboarding and training", "quantity": 2, "unit_price": "1250.50"},
]


def _url(quotation_id, suffix=""):
    return f"{QUOTATIONS_URL}{quotation_id}/{suffix}"


def _create(client, **payload):
    return client.post(QUOTATIONS_URL, {"items": ITEMS, **payload}, format="json")


@pytest.fixture
def school(two_schools):
    School.objects.filter(pk=two_schools[0].pk).update(
        email="office@school-a.example", admin_name="Huda Saleh"
    )
    two_schools[0].refresh_from_db()
    return two_schools[0]


@pytest.fixture
def draft(platform_client, school):
    return _create(platform_client, school=school.pk).data


# --- Totals


def test_totals_round_each_line_and_the_vat_to_the_halala():
    items = [
        {"quantity": 3, "unit_price": Decimal("33.33")},
        {"quantity": 1, "unit_price": Decimal("0.05")},
    ]

    assert quotation_totals(items, Decimal("15")) == (
        Decimal("100.04"),
        Decimal("15.01"),
        Decimal("115.05"),
    )


def test_zero_vat_is_allowed():
    items = [{"quantity": 2, "unit_price": Decimal("10.00")}]

    assert quotation_totals(items, Decimal("0")) == (
        Decimal("20.00"),
        Decimal("0.00"),
        Decimal("20.00"),
    )


# --- Creating


def test_create_for_a_school_fills_the_recipient_and_totals(platform_client, school):
    response = _create(platform_client, school=school.pk)

    assert response.status_code == 201
    data = response.data
    year = timezone.localdate().year
    assert data["number"] == f"Q-{year}-{data['id']:05d}"
    assert data["status"] == "draft"
    assert data["recipient_email"] == "office@school-a.example"
    assert data["recipient_name"] == "Huda Saleh"
    assert data["recipient_organization"] == "School A"
    assert data["vat_rate"] == "15.00"
    assert data["subtotal"] == "32501.00"
    assert data["vat_amount"] == "4875.15"
    assert data["total"] == "37376.15"
    assert [item["amount"] for item in data["items"]] == ["30000.00", "2501.00"]
    assert data["valid_until"] == (timezone.localdate() + timedelta(days=30)).isoformat()
    event = AuditEvent.objects.get(action=AuditEvent.Action.QUOTATION_CREATED)
    assert event.school == school
    assert event.details == {"total": "37376.15"}


def test_arabic_quotation_uses_the_arabic_school_name(platform_client, school):
    response = _create(platform_client, school=school.pk, language="ar")

    assert response.data["recipient_organization"] == "مدرسة أ"


def test_create_for_a_demo_request_uses_the_prospect(platform_client, demo_request):
    response = _create(platform_client, demo_request=demo_request.pk)

    assert response.status_code == 201
    assert response.data["school"] is None
    assert response.data["demo_request"] == demo_request.pk
    assert response.data["recipient_email"] == "sara@alnoor.example"
    assert response.data["recipient_organization"] == "Al Noor School"


def test_given_recipient_details_win(platform_client, demo_request):
    response = _create(
        platform_client,
        demo_request=demo_request.pk,
        recipient_email="finance@alnoor.example",
        recipient_name="Finance office",
    )

    assert response.data["recipient_email"] == "finance@alnoor.example"
    assert response.data["recipient_name"] == "Finance office"


def test_a_school_without_email_needs_one(platform_client, two_schools):
    response = _create(platform_client, school=two_schools[1].pk)

    assert response.status_code == 400
    assert "recipient_email" in response.data["error"]["fields"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"school": "SCHOOL", "demo_request": "DEMO"},
        {"school": "SCHOOL", "items": []},
        {"school": "SCHOOL", "items": [{"description": "x", "quantity": 0, "unit_price": "1"}]},
        {"school": "SCHOOL", "items": [{"description": "x", "quantity": 1, "unit_price": "-1"}]},
        {"school": "SCHOOL", "items": [{"description": "", "quantity": 1, "unit_price": "1"}]},
        {"school": "SCHOOL", "vat_rate": "101"},
        {"school": "SCHOOL", "valid_until": "2020-01-01"},
        {"school": "SCHOOL", "language": "fr"},
        {"school": "SCHOOL", "billing_cycle": "weekly"},
        {"school": 999999},
    ],
)
def test_create_rejects_invalid_input(platform_client, school, demo_request, payload):
    swap = {"SCHOOL": school.pk, "DEMO": demo_request.pk}
    body = {
        key: swap.get(value, value) if isinstance(value, str) else value
        for key, value in payload.items()
    }
    if "items" not in body:
        body["items"] = ITEMS

    response = platform_client.post(QUOTATIONS_URL, body, format="json")

    assert response.status_code == 400
    assert not Quotation.objects.exists()


def test_too_many_lines_are_refused(platform_client, school):
    items = [{"description": f"Line {i}", "quantity": 1, "unit_price": "1"} for i in range(51)]

    response = platform_client.post(
        QUOTATIONS_URL, {"school": school.pk, "items": items}, format="json"
    )

    assert response.status_code == 400


# --- Editing


def test_a_draft_can_be_edited_and_totals_follow(platform_client, draft):
    response = platform_client.patch(
        _url(draft["id"]),
        {"vat_rate": "0", "items": [{"description": "Basic", "quantity": 1, "unit_price": "100"}]},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["total"] == "100.00"
    assert len(response.data["items"]) == 1
    assert AuditEvent.objects.filter(
        action=AuditEvent.Action.QUOTATION_UPDATED, details={"fields": ["items", "vat_rate"]}
    ).exists()


def test_changing_only_the_vat_rate_recomputes_totals(platform_client, draft):
    response = platform_client.patch(_url(draft["id"]), {"vat_rate": "5"}, format="json")

    assert response.data["vat_amount"] == "1625.05"
    assert response.data["total"] == "34126.05"


def test_the_recipient_choice_cannot_change(platform_client, draft, demo_request):
    platform_client.patch(_url(draft["id"]), {"demo_request": demo_request.pk}, format="json")

    quotation = Quotation.objects.get(pk=draft["id"])
    assert quotation.demo_request is None
    assert quotation.school is not None


# --- Sending


def test_send_emails_the_pdf_once_the_change_is_saved(
    platform_client, draft, fake_pdf, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        response = platform_client.post(_url(draft["id"], "send/"))

    assert response.status_code == 200
    assert response.data["status"] == "sent"
    assert response.data["sent_at"] is not None
    message = mail.outbox[0]
    assert message.to == ["office@school-a.example"]
    assert draft["number"] in message.subject
    filename, content, mimetype = message.attachments[-1]
    assert filename == f"{draft['number']}.pdf"
    assert content.startswith(b"%PDF")
    assert mimetype == "application/pdf"
    assert AuditEvent.objects.filter(
        action=AuditEvent.Action.QUOTATION_SENT, details__resend=False
    ).exists()


def test_a_sent_quotation_can_be_sent_again_but_not_edited(
    platform_client, draft, fake_pdf, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        platform_client.post(_url(draft["id"], "send/"))
        again = platform_client.post(_url(draft["id"], "send/"))

    edit = platform_client.patch(_url(draft["id"]), {"notes": "late change"}, format="json")

    assert again.status_code == 200
    assert len(mail.outbox) == 2
    assert AuditEvent.objects.filter(
        action=AuditEvent.Action.QUOTATION_SENT, details__resend=True
    ).exists()
    assert edit.status_code == 400


def test_an_expired_draft_cannot_be_sent(platform_client, draft):
    Quotation.objects.filter(pk=draft["id"]).update(
        valid_until=timezone.localdate() - timedelta(days=1)
    )

    response = platform_client.post(_url(draft["id"], "send/"))

    assert response.status_code == 400
    assert "valid_until" in response.data["error"]["fields"]


def test_the_email_task_skips_a_quotation_that_is_not_sent(draft, fake_pdf):
    send_quotation_email_task(draft["id"])
    send_quotation_email_task(999999)

    assert mail.outbox == []


# --- Answers


def test_accept_and_reject_only_after_sending(platform_client, draft, fake_pdf):
    assert platform_client.post(_url(draft["id"], "accept/")).status_code == 400

    platform_client.post(_url(draft["id"], "send/"))
    accepted = platform_client.post(_url(draft["id"], "accept/"))
    reject_after = platform_client.post(_url(draft["id"], "reject/"))
    resend_after = platform_client.post(_url(draft["id"], "send/"))

    assert accepted.status_code == 200
    assert accepted.data["status"] == "accepted"
    assert accepted.data["responded_at"] is not None
    assert reject_after.status_code == 400
    assert resend_after.status_code == 400


def test_reject_is_recorded(platform_client, draft, fake_pdf):
    platform_client.post(_url(draft["id"], "send/"))

    response = platform_client.post(_url(draft["id"], "reject/"))

    assert response.data["status"] == "rejected"
    assert AuditEvent.objects.filter(action=AuditEvent.Action.QUOTATION_REJECTED).exists()


def test_a_sent_quotation_past_its_date_shows_as_expired(platform_client, draft, fake_pdf):
    platform_client.post(_url(draft["id"], "send/"))
    Quotation.objects.filter(pk=draft["id"]).update(
        valid_until=timezone.localdate() - timedelta(days=1)
    )

    assert platform_client.get(_url(draft["id"])).data["is_expired"] is True


# --- Listing


def test_list_filters_and_counts(platform_client, school, demo_request, fake_pdf):
    first = _create(platform_client, school=school.pk).data
    _create(platform_client, demo_request=demo_request.pk)
    platform_client.post(_url(first["id"], "send/"))

    sent = platform_client.get(f"{QUOTATIONS_URL}?status=sent")
    searched = platform_client.get(QUOTATIONS_URL, {"search": "Al Noor"})
    summary = platform_client.get(f"{QUOTATIONS_URL}summary/")

    assert [row["id"] for row in sent.data["results"]] == [first["id"]]
    assert searched.data["count"] == 1
    assert summary.data["total"] == 2
    assert summary.data["by_status"] == {"draft": 1, "sent": 1, "accepted": 0, "rejected": 0}


# --- PDF


def test_pdf_html_is_in_the_quotation_language(platform_client, school):
    english = Quotation.objects.get(pk=_create(platform_client, school=school.pk).data["id"])
    arabic = Quotation.objects.get(
        pk=_create(platform_client, school=school.pk, language="ar").data["id"]
    )

    english_html = render_quotation_html(english)
    arabic_html = render_quotation_html(arabic)

    assert 'dir="ltr"' in english_html
    assert "Quotation" in english_html
    assert "37,376.15" in english_html
    assert 'dir="rtl"' in arabic_html
    assert "عرض سعر" in arabic_html
    assert "مدرسة أ" in arabic_html


def test_pdf_escapes_what_people_typed(platform_client, demo_request):
    DemoRequest.objects.filter(pk=demo_request.pk).update(school_name="<script>x</script>")
    data = _create(platform_client, demo_request=demo_request.pk).data

    html = render_quotation_html(Quotation.objects.get(pk=data["id"]))

    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_hijri_date_uses_umm_al_qura():
    from datetime import date

    assert hijri_date(date(2026, 11, 11)) == "01/06/1448"


def test_real_pdf_is_made(platform_client, school, requires_pdf):
    data = _create(platform_client, school=school.pk, language="ar").data

    content = render_quotation_pdf(Quotation.objects.get(pk=data["id"]))

    assert content.startswith(b"%PDF")


def test_pdf_download(platform_client, draft, fake_pdf):
    response = platform_client.get(_url(draft["id"], "pdf/"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert f'filename="{draft["number"]}.pdf"' in response["Content-Disposition"]
    assert response.content.startswith(b"%PDF")


def test_pdf_download_says_when_pdfs_cannot_be_made(platform_client, draft, monkeypatch):
    from apps.integrations.pdf.renderer import PdfUnavailable

    def unavailable(html):
        raise PdfUnavailable("no pango")

    monkeypatch.setattr("apps.platform.documents.html_to_pdf", unavailable)

    response = platform_client.get(_url(draft["id"], "pdf/"))

    assert response.status_code == 503
    assert response.data["error"]["code"] == "pdf_unavailable"


# --- Access


def test_quotations_are_denied_to_everyone_else(school_admin_client, school, draft):
    for client in (APIClient(), school_admin_client):
        assert client.get(QUOTATIONS_URL).status_code == 403
        assert client.get(_url(draft["id"])).status_code == 403
        assert client.get(_url(draft["id"], "pdf/")).status_code == 403
        assert _create(client, school=school.pk).status_code == 403
        assert client.post(_url(draft["id"], "send/")).status_code == 403
        assert client.patch(_url(draft["id"]), {"notes": "x"}, format="json").status_code == 403

    quotation = Quotation.objects.get()
    assert quotation.status == Quotation.Status.DRAFT
    assert quotation.notes == ""


def test_quotations_cannot_be_deleted(platform_client, draft):
    assert platform_client.delete(_url(draft["id"])).status_code == 405
