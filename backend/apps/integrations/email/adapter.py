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
        "intro": "Use this code to reset your password.",
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


def teacher_signup_code_content(to_email, code):
    expiry = f"This code expires in {OTP_EXPIRY_MINUTES} minutes."
    return {
        "subject": "Confirm your email for Lesson Lab",
        "to": to_email,
        "heading": "Confirm your email",
        "intro": "Enter this code to start your 7-day free trial.",
        "body_html": (
            code_box(code)
            + notice(f"{expiry} It can only be used once.", tone="warning")
            + paragraph(
                "If you didn't try to sign up, you can ignore this email.", muted=True, spacing=0
            )
        ),
        "preheader": expiry,
        "text_body": (
            f"Your verification code is: {code}\n\n"
            f"{expiry} It can only be used once.\n\n"
            "If you didn't try to sign up, you can ignore this email."
        ),
    }


def teacher_account_exists_content(to_email):
    return {
        "subject": "You already have a Lesson Lab account",
        "to": to_email,
        "heading": "You already have an account",
        "intro": "Someone tried to start a free trial with this email address.",
        "body_html": paragraph(
            "If it was you, sign in instead. If you forgot your password, you can reset it on "
            "the sign-in page. If it wasn't you, you can ignore this email.",
            spacing=0,
        ),
        "cta_label": "Sign in to Lesson Lab",
        "cta_url": f"{settings.FRONTEND_URL}/login",
        "preheader": "Sign in with your existing account.",
    }


def trial_reminder_content(to_email, name, days_left):
    when = "tomorrow" if days_left <= 1 else f"in {days_left} days"
    return {
        "subject": f"Your Lesson Lab free trial ends {when}",
        "to": to_email,
        "heading": f"Your free trial ends {when}",
        "intro": f"Hello {user_text(name)}, we hope your classes are going well.",
        "body_html": paragraph(
            "Choose a plan to keep adding classes, lessons and results. "
            "Everything you have created stays safe in your account.",
            spacing=0,
        ),
        "cta_label": "Choose a plan",
        "cta_url": f"{settings.FRONTEND_URL}/teacher/plan",
        "preheader": "Choose a plan to keep working without a break.",
    }


def trial_ended_content(to_email, name):
    return {
        "subject": "Your Lesson Lab free trial has ended",
        "to": to_email,
        "heading": "Your free trial has ended",
        "intro": f"Hello {user_text(name)}, thank you for trying Lesson Lab.",
        "body_html": paragraph(
            "You can still sign in and see your work. Choose a plan to make changes again.",
            spacing=0,
        ),
        "cta_label": "Choose a plan",
        "cta_url": f"{settings.FRONTEND_URL}/teacher/plan",
        "preheader": "Your work is safe. Choose a plan to continue.",
    }


def parent_message_content(*, to_email, teacher_name, class_name, subject, body):
    return {
        "subject": subject,
        "to": to_email,
        "heading": user_text(subject),
        "intro": f"A message from {user_text(teacher_name)} about {user_text(class_name)}.",
        "body_html": paragraph(user_text(body), spacing=0),
        "preheader": f"A message from {user_text(teacher_name)}.",
    }


def school_admin_welcome_content(to_email, school_name, username=None):
    school = user_text(school_name)
    steps = [
        "Open the sign-in page using the button below.",
        "Choose <strong>Forgot password?</strong>",
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


def send_teacher_signup_code_email(to_email, code):
    send_branded_email(**teacher_signup_code_content(to_email, code))


def send_trial_reminder_email(to_email, name, days_left):
    send_branded_email(**trial_reminder_content(to_email, name, days_left))


def send_trial_ended_email(to_email, name):
    send_branded_email(**trial_ended_content(to_email, name))


def send_parent_message_email(**content):
    send_branded_email(**parent_message_content(**content))


def send_teacher_account_exists_email(to_email):
    send_branded_email(**teacher_account_exists_content(to_email))


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
        "teacher-signup-code": teacher_signup_code_content("teacher@example.com", "123456"),
        "teacher-account-exists": teacher_account_exists_content("teacher@example.com"),
        "trial-reminder": trial_reminder_content("teacher@example.com", "Sara Ahmed", 2),
        "trial-ended": trial_ended_content("teacher@example.com", "Sara Ahmed"),
        "parent-message": parent_message_content(
            to_email="parent@example.com",
            teacher_name="Sara Ahmed",
            class_name="Grade 5 Science",
            subject="Science test next week",
            body="Please help your child revise chapter three.",
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
