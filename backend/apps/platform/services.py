import logging

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.platform.models import ContactMessage, DemoRequest
from apps.platform.tasks import (
    send_lead_notification_email_task,
    send_school_admin_welcome_email_task,
)
from apps.tenancy.models import Membership, School

logger = logging.getLogger(__name__)


def _create_admin_user(code, email, name):
    username = f"{code}.admin"
    if User.objects.filter(username=username).exists():
        raise ValidationError({"code": "This code is not available."})

    first_name, _, last_name = name.partition(" ")
    # No password: the new admin signs in with an email code, then sets up 2FA.
    return User.objects.create_user(
        username=username, email=email, password=None, first_name=first_name, last_name=last_name
    )


def _lock_convertible_demo_request(demo_request_id):
    demo = DemoRequest.objects.select_for_update().filter(pk=demo_request_id).first()
    if demo is None:
        raise ValidationError({"demo_request": "This demo request doesn't exist."})
    if demo.status == DemoRequest.Status.CONVERTED:
        raise ValidationError({"demo_request": "This demo request already has a school."})
    return demo


# Two requests can pass validation at the same moment, and then the database refuses
# the second one. Each entry maps part of a constraint's name to the form field it is about.
UNIQUE_FIELD_BY_CONSTRAINT = {
    "unique_school_email": ("email", "This email is already in use."),
    "accounts_user_email": ("admin_email", "This email is already in use."),
    "tenancy_school_code": ("code", "This code is not available."),
    "accounts_user_username": ("code", "This code is not available."),
}


def create_school_with_admin(*, actor, admin_email, code, **details):
    try:
        return _create_school_with_admin(actor=actor, admin_email=admin_email, code=code, **details)
    except IntegrityError as error:
        for constraint, (field, message) in UNIQUE_FIELD_BY_CONSTRAINT.items():
            if constraint in str(error):
                raise ValidationError({field: message}) from error
        raise


@transaction.atomic
def _create_school_with_admin(
    *, actor, name_en, name_ar, code, admin_email, admin_name, demo_request=None, **details
):
    demo = _lock_convertible_demo_request(demo_request) if demo_request else None

    school = School.objects.create(
        name_en=name_en, name_ar=name_ar, code=code, admin_name=admin_name, **details
    )
    admin = _create_admin_user(code, admin_email, admin_name)
    Membership.objects.create(school=school, user=admin, role=Membership.Role.SCHOOL_ADMIN)

    if demo is not None:
        demo.status = DemoRequest.Status.CONVERTED
        demo.converted_school = school
        demo.save()

    logger.info("school_created school_id=%s actor_id=%s", school.id, actor.id)
    transaction.on_commit(
        lambda: send_school_admin_welcome_email_task.delay(admin.email, name_en),
        robust=True,
    )
    return school


def set_school_active(*, actor, school, is_active):
    """Tenant access stops on the user's next request; memberships stay as they are."""
    if school.is_active != is_active:
        school.is_active = is_active
        school.save(update_fields=["is_active", "updated_at"])
        logger.info(
            "school_%s school_id=%s actor_id=%s",
            "activated" if is_active else "deactivated",
            school.id,
            actor.id,
        )
    return school


@transaction.atomic
def update_demo_request(*, actor, demo_request_id, **changes):
    demo = DemoRequest.objects.select_for_update().get(pk=demo_request_id)
    status = changes.get("status", demo.status)
    converted = DemoRequest.Status.CONVERTED

    # Conversion always comes with a school, so it happens only by creating one.
    if status != demo.status and converted in (status, demo.status):
        raise ValidationError({"status": "Converted can only be set by creating a school."})

    for field, value in changes.items():
        setattr(demo, field, value)
    demo.save()

    logger.info("demo_request_updated id=%s status=%s actor_id=%s", demo.id, demo.status, actor.id)
    return demo


def _notify_team(*, subject, heading, intro, rows, message, reply_to):
    transaction.on_commit(
        lambda: send_lead_notification_email_task.delay(
            subject=subject,
            heading=heading,
            intro=intro,
            rows=rows,
            message=message,
            reply_to=reply_to,
        ),
        robust=True,
    )


@transaction.atomic
def create_demo_request(*, name, school_name, email, phone="", plan="", message=""):
    demo = DemoRequest.objects.create(
        name=name, school_name=school_name, email=email, phone=phone, plan=plan, message=message
    )
    logger.info("demo_request_created id=%s", demo.id)
    _notify_team(
        subject=f"Demo request: {school_name}",
        heading="New demo request",
        intro="Someone filled in the Book a demo form on the website.",
        rows=[
            ("Name", name),
            ("School", school_name),
            ("Email", email),
            ("Phone", phone or "-"),
            ("Plan", plan or "-"),
        ],
        message=message,
        reply_to=email,
    )
    return demo


@transaction.atomic
def create_contact_message(*, name, email, message, school_name=""):
    contact = ContactMessage.objects.create(
        name=name, school_name=school_name, email=email, message=message
    )
    logger.info("contact_message_created id=%s", contact.id)
    _notify_team(
        subject=f"Contact message: {name}",
        heading="New contact message",
        intro="Someone sent a message through the Contact form on the website.",
        rows=[("Name", name), ("School", school_name or "-"), ("Email", email)],
        message=message,
        reply_to=email,
    )
    return contact
