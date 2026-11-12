from django.conf import settings

from .branded import (
    build_branded_email,
    checklist,
    code_box,
    detail_table,
    notice,
    paragraph,
    send_branded_email,
    user_text,
)

# Matches the expiry set in accounts.services.request_email_otp.
OTP_EXPIRY_MINUTES = 10


def otp_email_content(to_email, code):
    expiry = f"This code expires in {OTP_EXPIRY_MINUTES} minutes."
    return {
        "subject": "Your Lesson Lab verification code",
        "to": to_email,
        "heading": "Your verification code",
        "intro": "Use this code to sign in to Lesson Lab.",
        "body_html": (
            code_box(code)
            + notice(f"{expiry} It can only be used once.", tone="warning")
            + paragraph(
                "If you didn't ask for this code, you can ignore this email. "
                "Please don't share this code with anyone.",
                muted=True,
                spacing=0,
            )
        ),
        "preheader": expiry,
        # Written by hand, so the code is on the very first line of the plain version.
        "text_body": (
            f"Your verification code is: {code}\n\n"
            f"{expiry} It can only be used once.\n\n"
            "If you didn't ask for this code, you can ignore this email. "
            "Please don't share this code with anyone."
        ),
    }


def school_admin_welcome_content(to_email, school_name, username=None):
    school = user_text(school_name)
    steps = [
        "Open the sign-in page using the button below.",
        "Choose <strong>Sign in with an email code</strong>.",
        "Enter this email address, then the code we send you.",
        "Choose your password. After that, sign in with your username and password.",
    ]
    body = checklist(steps, title="How to sign in the first time")
    if username:
        body = detail_table([("Your username", username)]) + body
    return {
        "subject": f"Your {school_name} account is ready",
        "to": to_email,
        "heading": "Welcome to Lesson Lab",
        "intro": f"You are now the administrator of <strong>{school}</strong>.",
        "body_html": body,
        "cta_label": "Sign in to Lesson Lab",
        "cta_url": f"{settings.FRONTEND_URL}/login",
        "preheader": f"Your {school} account is ready. Here is how to sign in.",
    }


def lead_notification_content(*, subject, heading, intro, rows, message, reply_to):
    body = detail_table([(label, value) for label, value in rows])
    if message:
        body += notice(user_text(message), title="Message")
    body += paragraph("Reply to this email to answer them directly.", muted=True, spacing=0)
    return {
        "subject": subject,
        "to": settings.LEADS_EMAIL,
        "heading": heading,
        "intro": intro,
        "body_html": body,
        "preheader": user_text(" ".join(subject.split())),
        "reply_to": reply_to,
    }


def quotation_email_content(
    *, to_email, recipient_name, organization, number, total, valid_until, attachment=None
):
    """valid_until is already formatted. attachment = (filename, pdf_bytes, mimetype)."""
    return {
        "subject": f"Your Lesson Lab quotation {number}",
        "to": to_email,
        "heading": "Your quotation",
        "intro": f"Hello {user_text(recipient_name)}, here is the quotation we prepared for "
        f"<strong>{user_text(organization)}</strong>.",
        "body_html": (
            detail_table(
                [
                    ("Quotation no.", number),
                    ("Total (incl. VAT)", f"SAR {total}"),
                    ("Valid until", valid_until),
                ],
                mono=("Quotation no.",),
            )
            + paragraph("The full quotation is attached as a PDF.")
            + paragraph(
                "Reply to this email if you have any questions, or to accept the quotation.",
                muted=True,
                spacing=0,
            )
        ),
        "preheader": f"Quotation {number} for {user_text(organization)}",
        "reply_to": settings.LEADS_EMAIL,
        "attachments": [attachment] if attachment else None,
    }


def send_otp_email(to_email, code):
    send_branded_email(**otp_email_content(to_email, code))


def send_school_admin_welcome_email(to_email, school_name, username=None):
    send_branded_email(**school_admin_welcome_content(to_email, school_name, username))


def send_quotation_email(**content):
    send_branded_email(**quotation_email_content(**content))


def send_lead_notification_email(*, subject, heading, intro, rows, message, reply_to):
    send_branded_email(
        **lead_notification_content(
            subject=subject,
            heading=heading,
            intro=intro,
            rows=rows,
            message=message,
            reply_to=reply_to,
        )
    )


def preview_messages():
    """Every email, with sample data, for the preview_emails command."""
    demo_rows = [
        ("Name", "Sara Ahmed"),
        ("School", "Al Noor School"),
        ("Email", "sara@example.com"),
        ("Phone", "+966501234567"),
        ("Plan", "growth"),
    ]
    contact_rows = [
        ("Name", "Omar Saleh"),
        ("School", "-"),
        ("Email", "omar@example.com"),
    ]
    contents = {
        "otp": otp_email_content("admin@example.com", "123456"),
        "school-admin-welcome": school_admin_welcome_content(
            "admin@example.com", "Al Noor School", "alnoor.admin"
        ),
        "demo-request": lead_notification_content(
            subject="Demo request: Al Noor School",
            heading="New demo request",
            intro="Someone filled in the Book a demo form on the website.",
            rows=demo_rows,
            message="We have 400 students.\nCan we see the attendance screens?",
            reply_to="sara@example.com",
        ),
        "quotation": quotation_email_content(
            to_email="admin@example.com",
            recipient_name="Sara Ahmed",
            organization="Al Noor School",
            number="Q-2026-00042",
            total="3,450.00",
            valid_until="11/12/2026",
        ),
        "contact-message": lead_notification_content(
            subject="Contact message: Omar Saleh",
            heading="New contact message",
            intro="Someone sent a message through the Contact form on the website.",
            rows=contact_rows,
            message="Do you support Arabic and English?",
            reply_to="omar@example.com",
        ),
    }
    return {name: build_branded_email(**content) for name, content in contents.items()}
