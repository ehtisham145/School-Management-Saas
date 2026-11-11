import email
import logging
from pathlib import Path

import pytest
from django.core import mail
from django.core.management import CommandError, call_command

from apps.accounts.tasks import send_otp_email_task
from apps.integrations.email.adapter import (
    lead_notification_content,
    otp_email_content,
    preview_messages,
    quotation_email_content,
    school_admin_welcome_content,
    send_lead_notification_email,
    send_school_admin_welcome_email,
)
from apps.integrations.email.branded import (
    CTA,
    NAVY,
    ORANGE,
    build_branded_email,
    buttons,
    checklist,
    code_box,
    detail_table,
    html_for_preview,
    notice,
    paragraph,
    render_branded_email,
    send_branded_email,
    user_text,
)

ATTACK = '<script>alert("x")</script>'
ESCAPED = "&lt;script&gt;"
LEAD = {
    "subject": "Demo request: Al Noor",
    "heading": "New demo request",
    "intro": "Someone filled in the form.",
    "rows": [["Name", "Sara"], ["Phone", "+966501234567"]],
    "message": "Hello",
    "reply_to": "sara@example.com",
}


def _html(message):
    return message.alternatives[0][0]


# --- Blocks


def test_user_text_escapes_html_and_keeps_line_breaks():
    assert user_text("<b>Sara</b>\nAhmed") == "&lt;b&gt;Sara&lt;/b&gt;<br>Ahmed"
    assert user_text("") == ""
    assert user_text(None) == ""


def test_paragraph_has_a_muted_style():
    assert "font-size:15px" in paragraph("Hello")
    assert "font-size:13px" in paragraph("Hello", muted=True)
    assert "margin:0 0 4px" in paragraph("Hello", spacing=4)


def test_code_box_shows_the_label_and_escapes_the_code():
    box = code_box("<1>", label="Your code")

    assert "Your code" in box
    assert "&lt;1&gt;" in box
    assert "<1>" not in box


def test_buttons_show_each_link_as_a_fallback_and_escape_urls():
    row = buttons(
        [("Open", "https://a.example/?x=1&y=2", "primary"), ("Back", "https://b", "neutral")]
    )

    assert "https://a.example/?x=1&amp;y=2" in row
    assert "x=1&y=2" not in row
    assert CTA in row
    assert NAVY in row
    assert "copy these links" in row


def test_detail_table_escapes_labels_and_values():
    table = detail_table([("Name", ATTACK), (ATTACK, "value")], mono=("Name",))

    assert "<script>" not in table
    assert ESCAPED in table
    assert "monospace" in table


def test_notice_uses_the_tone_and_title():
    assert "#fef0e5" in notice("Soon", tone="warning", title="Expiry")
    assert "Expiry" in notice("Soon", title="Expiry")
    assert notice("x", tone="unknown") == notice("x", tone="neutral")


def test_checklist_lists_every_item():
    items = checklist(["One", "Two"], title="Steps")

    assert "One" in items
    assert "Two" in items
    assert "Steps" in items


# --- The shell


def test_shell_has_the_brand_and_is_safe_for_email_clients():
    html = render_branded_email(
        heading="Hello",
        body_html="<p>Body</p>",
        cta_label="Go",
        cta_url="https://x.example/?a=1&b=2",
    )

    assert NAVY in html
    assert f"border-bottom:3px solid {ORANGE}" in html
    assert "https://x.example/?a=1&amp;b=2" in html
    assert 'width="600"' in html
    for banned in ("<script", "<link", "<style", "@import", "gradient"):
        assert banned not in html


def test_shell_logo_uses_the_settings_and_is_absolute(settings):
    settings.BRAND_LOGO_URL = "https://cdn.example/logo.png"
    settings.BRAND_LOGO_WIDTH = 155
    settings.BRAND_LOGO_HEIGHT = 36

    html = render_branded_email(heading="Hello", body_html="")

    assert 'src="https://cdn.example/logo.png"' in html
    assert 'width="155" height="36"' in html


def test_logo_is_attached_to_the_email_by_default(settings):
    settings.BRAND_LOGO_URL = ""

    message = build_branded_email(subject="Hi", to="a@example.com", heading="H", body_html="x")

    assert 'src="cid:lessonlab-logo"' in _html(message)
    parsed = email.message_from_bytes(message.message().as_bytes())
    assert parsed.get_content_type() == "multipart/related"
    image = next(part for part in parsed.walk() if part.get_content_type() == "image/png")
    assert image["Content-ID"] == "<lessonlab-logo>"
    assert image.get_content_disposition() == "inline"
    assert image.get_payload(decode=True).startswith(b"\x89PNG")
    types = [part.get_content_type() for part in parsed.walk()]
    assert "text/plain" in types
    assert "text/html" in types


def test_a_logo_url_replaces_the_attachment(settings):
    settings.BRAND_LOGO_URL = "https://cdn.example/logo.png"

    message = build_branded_email(subject="Hi", to="a@example.com", heading="H", body_html="x")

    assert message.attachments == []
    assert "cid:" not in _html(message)


def test_preview_builds_the_logo_into_the_html(settings):
    settings.BRAND_LOGO_URL = ""

    message = build_branded_email(subject="Hi", to="a@example.com", heading="H", body_html="x")

    assert "cid:" not in html_for_preview(message)
    assert 'src="data:image/png;base64,' in html_for_preview(message)


def test_shell_hides_footer_parts_with_no_value(settings):
    settings.SUPPORT_EMAIL = ""
    settings.COMPANY_ADDRESS = ""
    settings.COMPANY_WEBSITE = ""

    html = render_branded_email(heading="Hello", body_html="")

    assert "Need help?" not in html
    assert "mailto:" not in html
    assert "&nbsp;·&nbsp;" not in html


def test_shell_shows_footer_parts_with_a_value(settings):
    settings.SUPPORT_EMAIL = "help@example.com"
    settings.COMPANY_ADDRESS = "1 King Road"
    settings.COMPANY_WEBSITE = "https://app.example"

    html = render_branded_email(heading="Hello", body_html="")

    assert "mailto:help@example.com" in html
    assert "1 King Road" in html
    assert ">app.example</a>" in html


def test_preheader_and_call_to_action_are_optional():
    html = render_branded_email(heading="Hello", body_html="")

    assert "display:none" not in html
    assert "copy this link" not in html
    assert "display:none" in render_branded_email(heading="Hello", body_html="", preheader="Soon")


def test_footer_says_do_not_reply_only_when_replies_go_nowhere():
    assert "do not reply" in render_branded_email(heading="Hello", body_html="")
    assert "do not reply" not in render_branded_email(heading="Hello", body_html="", can_reply=True)


# --- Building and sending


def test_plain_text_is_generated_and_shows_user_text_as_typed():
    message = build_branded_email(
        subject="Hi",
        to="a@example.com",
        heading="Hello",
        intro="Dear " + user_text("O'Brien <b>"),
        body_html=checklist(["One"]) + paragraph("Two"),
        cta_label="Go",
        cta_url="https://x.example",
    )

    assert "Hello" in message.body
    assert "Dear O'Brien <b>" in message.body
    assert "- " in message.body
    assert "Two" in message.body
    assert "Go: https://x.example" in message.body
    assert "<p" not in message.body


def test_subject_line_breaks_are_removed():
    message = build_branded_email(
        subject="Hi\r\nBcc: x@example.com", to=["a@example.com"], heading="H", body_html=""
    )

    assert message.subject == "Hi Bcc: x@example.com"
    assert message.bcc == []


def test_send_returns_true_and_adds_an_html_version():
    assert send_branded_email(subject="Hi", to="a@example.com", heading="H", body_html="x") is True

    assert mail.outbox[0].to == ["a@example.com"]
    assert mail.outbox[0].alternatives[0][1] == "text/html"


def _failing_send(self, fail_silently=False):
    raise OSError("SMTP refused code 123456")


def test_failed_send_raises_by_default_and_logs_no_content(monkeypatch, caplog):
    monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", _failing_send)

    with caplog.at_level(logging.ERROR), pytest.raises(OSError):
        send_branded_email(
            subject="Hi", to="a@example.com", heading="H", body_html=code_box("123456")
        )

    assert "branded_email_send_failed" in caplog.text
    assert "123456" not in caplog.text


def test_failed_send_can_be_silent(monkeypatch):
    monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", _failing_send)

    assert (
        send_branded_email(
            subject="Hi", to="a@example.com", heading="H", body_html="", fail_silently=True
        )
        is False
    )


# --- The real emails


def test_otp_email_shows_the_code_but_not_in_the_subject_or_preheader():
    send_otp_email_task.delay("parent@example.com", "123456")

    message = mail.outbox[0]
    assert "123456" in _html(message)
    assert message.body.startswith("Your verification code is: 123456")
    assert "123456" not in message.subject
    assert "123456" not in otp_email_content("a@example.com", "123456")["preheader"]
    assert "10 minutes" in _html(message)


def test_welcome_email_escapes_the_school_name_and_keeps_the_login_link(settings):
    settings.FRONTEND_URL = "https://app.example"

    send_school_admin_welcome_email("admin@example.com", ATTACK)

    html = _html(mail.outbox[0])
    assert "<script>" not in html
    assert ESCAPED in html
    assert 'href="https://app.example/login"' in html
    assert "https://app.example/login" in mail.outbox[0].body
    assert "Sign in with an email code" in html
    assert "<script>" not in school_admin_welcome_content("a@b.co", ATTACK)["preheader"]


def test_lead_email_escapes_everything_a_visitor_typed(settings):
    settings.LEADS_EMAIL = "team@example.com"

    send_lead_notification_email(
        **{**LEAD, "subject": f"Demo: {ATTACK}", "rows": [["Name", ATTACK]], "message": ATTACK}
    )

    message = mail.outbox[0]
    assert message.to == ["team@example.com"]
    assert message.reply_to == ["sara@example.com"]
    assert "<script>" not in _html(message)
    assert ESCAPED in _html(message)
    assert "do not reply" not in _html(message)


def test_lead_email_leaves_out_an_empty_message():
    assert "Message" not in lead_notification_content(**{**LEAD, "message": ""})["body_html"]


# --- Previews


def test_every_email_can_be_previewed():
    assert set(preview_messages()) == {
        "otp",
        "school-admin-welcome",
        "demo-request",
        "quotation",
        "contact-message",
    }


def test_preview_command_writes_html_and_text_files(settings, tmp_path):
    settings.DEBUG = True

    call_command("preview_emails", out=str(tmp_path))

    assert Path(tmp_path, "otp.html").read_text(encoding="utf8").startswith("<!DOCTYPE html>")
    assert "Subject:" in Path(tmp_path, "otp.txt").read_text(encoding="utf8")
    assert len(list(tmp_path.iterdir())) == 10


# --- Attachments


def test_a_file_attachment_keeps_the_message_mixed_so_clients_show_it(settings):
    settings.BRAND_LOGO_URL = ""

    message = build_branded_email(
        subject="Quote",
        to="a@example.com",
        heading="Quote",
        body_html="<p>x</p>",
        attachments=[("Q-2026-00001.pdf", b"%PDF-1.7", "application/pdf")],
    )

    assert message.mixed_subtype == "mixed"
    assert ("Q-2026-00001.pdf", b"%PDF-1.7", "application/pdf") in [
        tuple(item) for item in message.attachments if isinstance(item, tuple)
    ]


def test_without_files_the_logo_stays_related(settings):
    settings.BRAND_LOGO_URL = ""

    message = build_branded_email(subject="x", to="a@example.com", heading="x", body_html="")

    assert message.mixed_subtype == "related"


def test_quotation_email_escapes_names_and_keeps_the_number():
    content = quotation_email_content(
        to_email="a@example.com",
        recipient_name="<b>Sara</b>",
        organization="Al Noor",
        number="Q-2026-00042",
        total="3,450.00",
        valid_until="11/12/2026",
    )

    assert "&lt;b&gt;Sara&lt;/b&gt;" in content["intro"]
    assert "Q-2026-00042" in content["subject"]
    assert content["attachments"] is None


def test_preview_command_refuses_to_run_outside_debug(settings, tmp_path):
    settings.DEBUG = False

    with pytest.raises(CommandError):
        call_command("preview_emails", out=str(tmp_path))

    assert list(tmp_path.iterdir()) == []
