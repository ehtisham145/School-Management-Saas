from django.conf import settings
from django.core.mail import send_mail


def send_otp_email(to_email, code):
    send_mail(
        subject="Your verification code",
        message=f"Your verification code is: {code}\n\nThis code expires in 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
    )
