from django.conf import settings
from django.core.mail import EmailMessage, send_mail


def send_otp_email(to_email, code):
    send_mail(
        subject="Your verification code",
        message=f"Your verification code is: {code}\n\nThis code expires in 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
    )


def send_school_admin_welcome_email(to_email, school_name):
    login_url = f"{settings.FRONTEND_URL}/login"
    send_mail(
        subject=f"Your {school_name} account is ready",
        message=(
            f"You are now the administrator of {school_name}.\n\n"
            f'To sign in, open {login_url}, choose "Sign in with an email code" '
            f"and enter this email address. You will then set up two-factor authentication."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
    )


def send_lead_notification_email(*, subject, body, reply_to):
    # Subjects come from a public form, so line breaks are removed.
    EmailMessage(
        subject=" ".join(subject.split()),
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.LEADS_EMAIL],
        reply_to=[reply_to],
    ).send()
