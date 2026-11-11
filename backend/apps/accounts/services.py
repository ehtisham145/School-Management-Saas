import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from apps.accounts.models import EmailOTP
from apps.accounts.tasks import send_otp_email_task


def request_email_otp(user, purpose):
    code = f"{secrets.randbelow(1_000_000):06d}"
    EmailOTP.objects.create(
        user=user,
        code_hash=make_password(code),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    send_otp_email_task.delay(user.email, code)


def verify_email_otp(user, purpose, code):
    otp = (
        EmailOTP.objects.filter(user=user, purpose=purpose, used_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if otp is None or otp.expires_at < timezone.now() or otp.attempts >= 5:
        return False

    otp.attempts += 1
    otp.save(update_fields=["attempts"])

    if not check_password(code, otp.code_hash):
        return False

    otp.used_at = timezone.now()
    otp.save(update_fields=["used_at"])
    return True
