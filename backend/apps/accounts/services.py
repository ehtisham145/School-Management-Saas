import math
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from apps.accounts.models import EmailOTP
from apps.accounts.tasks import send_otp_email_task


def totp_wait_seconds(device):
    """How long until django-otp will check a code again, after wrong ones. 0 means now.

    While this is above 0 it refuses every code, including the correct one.
    """
    allowed, details = device.verify_is_allowed()
    if allowed:
        return 0
    locked_until = details.get("locked_until")
    if locked_until is None:
        return 1
    return max(1, math.ceil((locked_until - timezone.now()).total_seconds()))


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
