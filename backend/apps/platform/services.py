import logging

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.platform.tasks import send_school_admin_welcome_email_task
from apps.tenancy.models import Membership, School

logger = logging.getLogger(__name__)


def _get_or_create_admin_user(code, email):
    user = User.objects.filter(email__iexact=email).first()
    if user is not None:
        return user

    username = f"{code}.admin"
    if User.objects.filter(username=username).exists():
        raise ValidationError({"code": "This code is not available."})

    # No password: the new admin signs in with an email code, then sets up 2FA.
    return User.objects.create_user(username=username, email=email, password=None)


@transaction.atomic
def create_school_with_admin(*, actor, name_en, name_ar, code, admin_email):
    school = School.objects.create(name_en=name_en, name_ar=name_ar, code=code)
    admin = _get_or_create_admin_user(code, admin_email)
    Membership.objects.create(school=school, user=admin, role=Membership.Role.SCHOOL_ADMIN)

    logger.info("school_created school_id=%s actor_id=%s", school.id, actor.id)
    transaction.on_commit(
        lambda: send_school_admin_welcome_email_task.delay(admin.email, name_en),
        robust=True,
    )
    return school
