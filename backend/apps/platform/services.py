import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.audit.services import SYSTEM, Action, record_event
from apps.platform.models import (
    BillingCycle,
    ContactMessage,
    DemoRequest,
    Plan,
    Quotation,
    QuotationItem,
    Subscription,
)
from apps.platform.tasks import (
    send_lead_notification_email_task,
    send_quotation_email_task,
    send_school_admin_welcome_email_task,
)
from apps.tenancy.models import Membership, School

CENT = Decimal("0.01")

# --- Schools


def _create_admin_user(code, email, name):
    username = f"{code}.admin"
    if User.objects.filter(username=username).exists():
        raise ValidationError({"code": "This code is not available."})

    first_name, _, last_name = name.partition(" ")
    # No password: the new admin signs in with an email code.
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
    *, actor, name_en, name_ar="", code, admin_email, admin_name, demo_request=None, **details
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

    record_event(
        actor,
        Action.SCHOOL_CREATED,
        school,
        school=school,
        details={"code": code, "demo_request": demo.pk if demo else None},
    )
    transaction.on_commit(
        lambda: send_school_admin_welcome_email_task.delay(admin.email, name_en),
        robust=True,
    )
    return school


@transaction.atomic
def set_school_active(*, actor, school, is_active):
    """Tenant access stops on the user's next request; memberships stay as they are."""
    if school.is_active != is_active:
        school.is_active = is_active
        school.save(update_fields=["is_active", "updated_at"])
        record_event(
            actor,
            Action.SCHOOL_ACTIVATED if is_active else Action.SCHOOL_DEACTIVATED,
            school,
            school=school,
        )
    return school


# --- Demo requests and contact messages


@transaction.atomic
def update_demo_request(*, actor, demo_request_id, **changes):
    demo = DemoRequest.objects.select_for_update().get(pk=demo_request_id)
    status = changes.get("status", demo.status)
    converted = DemoRequest.Status.CONVERTED

    # Conversion always comes with a school, so it happens only by creating one.
    if status != demo.status and converted in (status, demo.status):
        raise ValidationError({"status": "Converted can only be set by creating a school."})

    previous_status = demo.status
    for field, value in changes.items():
        setattr(demo, field, value)
    demo.save()

    record_event(
        actor,
        Action.DEMO_REQUEST_UPDATED,
        demo,
        label=demo.school_name,
        details={
            "status": [previous_status, demo.status],
            "notes_changed": "admin_notes" in changes,
        },
    )
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
    _notify_team(
        subject=f"Contact message: {name}",
        heading="New contact message",
        intro="Someone sent a message through the Contact form on the website.",
        rows=[("Name", name), ("School", school_name or "-"), ("Email", email)],
        message=message,
        reply_to=email,
    )
    return contact


# --- Plans


def _changes(before, after):
    """Field -> [old, new] for the audit log, with Decimals as text."""
    return {
        field: [str(old), str(after[field])]
        for field, old in before.items()
        if field in after and old != after[field]
    }


@transaction.atomic
def create_plan(*, actor, **fields):
    try:
        with transaction.atomic():
            plan = Plan.objects.create(**fields)
    except IntegrityError as error:
        raise ValidationError({"code": "This code is already in use."}) from error
    record_event(actor, Action.PLAN_CREATED, plan, details={"code": plan.code})
    return plan


@transaction.atomic
def update_plan(*, actor, plan_id, **changes):
    plan = Plan.objects.select_for_update().get(pk=plan_id)
    before = {field: getattr(plan, field) for field in changes}
    for field, value in changes.items():
        setattr(plan, field, value)
    plan.save()

    changed = _changes(before, changes)
    if changed:
        record_event(actor, Action.PLAN_UPDATED, plan, details={"changes": changed})
    return plan


# --- Subscriptions


def add_months(day: date, months: int) -> date:
    """Same day of the month, moved back to the month's last day when it has fewer days."""
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def subscription_end(starts_on: date, billing_cycle: str) -> date:
    """The first day the subscription no longer covers."""
    return add_months(starts_on, 12 if billing_cycle == BillingCycle.YEARLY else 1)


@transaction.atomic
def activate_subscription(*, actor, school, plan, billing_cycle, starts_on, price=None, notes=""):
    # Locks the school, so two activations for one school run one after the other.
    school = School.objects.select_for_update().get(pk=school.pk)
    if not school.is_active:
        raise ValidationError({"school": "Activate the school before giving it a subscription."})
    if not plan.is_active:
        raise ValidationError({"plan": "This plan is no longer offered."})
    if school.subscriptions.filter(status=Subscription.Status.ACTIVE).exists():
        raise ValidationError(
            {"school": "This school already has an active subscription. Expire it first."}
        )

    subscription = Subscription.objects.create(
        school=school,
        plan=plan,
        billing_cycle=billing_cycle,
        price=plan.price_for(billing_cycle) if price is None else price,
        starts_on=starts_on,
        ends_on=subscription_end(starts_on, billing_cycle),
        notes=notes,
        created_by=actor.user,
    )
    record_event(
        actor,
        Action.SUBSCRIPTION_ACTIVATED,
        subscription,
        label=f"{school.name_en} - {plan.name_en}",
        school=school,
        details={
            "plan": plan.code,
            "billing_cycle": billing_cycle,
            "price": str(subscription.price),
            "starts_on": subscription.starts_on.isoformat(),
            "ends_on": subscription.ends_on.isoformat(),
        },
    )
    return subscription


def _expire(subscription, actor, reason):
    subscription.status = Subscription.Status.EXPIRED
    subscription.expired_at = timezone.now()
    subscription.save(update_fields=["status", "expired_at", "updated_at"])
    record_event(
        actor,
        Action.SUBSCRIPTION_EXPIRED,
        subscription,
        label=f"{subscription.school.name_en} - {subscription.plan.name_en}",
        school=subscription.school,
        details={"reason": reason},
    )


@transaction.atomic
def expire_subscription(*, actor, subscription_id):
    subscription = (
        Subscription.objects.select_for_update()
        .select_related("school", "plan")
        .get(pk=subscription_id)
    )
    if subscription.status != Subscription.Status.ACTIVE:
        raise ValidationError({"status": "This subscription has already expired."})
    _expire(subscription, actor, "manual")
    return subscription


@transaction.atomic
def expire_overdue_subscriptions(today=None):
    """Expires every active subscription whose last covered day has passed."""
    today = today or timezone.localdate()
    overdue = (
        Subscription.objects.select_for_update(skip_locked=True, of=("self",))
        .select_related("school", "plan")
        .filter(status=Subscription.Status.ACTIVE, ends_on__lte=today)
    )
    count = 0
    for subscription in overdue:
        _expire(subscription, SYSTEM, "ended")
        count += 1
    return count


# --- Quotations


def _money(value) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def quotation_totals(items, vat_rate):
    """(subtotal, vat_amount, total). Each line and the VAT are rounded to the halala."""
    subtotal = sum((_money(item["quantity"] * item["unit_price"]) for item in items), Decimal(0))
    vat_amount = _money(subtotal * Decimal(vat_rate) / 100)
    return subtotal, vat_amount, subtotal + vat_amount


def _recipient_defaults(*, school, demo_request, language):
    if school is not None:
        return {
            "recipient_name": school.admin_name or school.name_en,
            "recipient_email": school.email,
            "recipient_organization": (
                (school.name_ar or school.name_en) if language == "ar" else school.name_en
            ),
        }
    return {
        "recipient_name": demo_request.name,
        "recipient_email": demo_request.email,
        "recipient_organization": demo_request.school_name,
    }


def _replace_items(quotation, items):
    quotation.items.all().delete()
    QuotationItem.objects.bulk_create(
        QuotationItem(
            quotation=quotation,
            position=position,
            description=item["description"],
            quantity=item["quantity"],
            unit_price=_money(item["unit_price"]),
            amount=_money(item["quantity"] * item["unit_price"]),
        )
        for position, item in enumerate(items, start=1)
    )
    quotation.subtotal, quotation.vat_amount, quotation.total = quotation_totals(
        items, quotation.vat_rate
    )


def _lock_quotation(quotation_id):
    return Quotation.objects.select_for_update().get(pk=quotation_id)


@transaction.atomic
def create_quotation(
    *,
    actor,
    items,
    school=None,
    demo_request=None,
    language=Quotation.Language.EN,
    plan=None,
    billing_cycle="",
    valid_until=None,
    vat_rate=None,
    notes="",
    recipient_name="",
    recipient_email="",
    recipient_organization="",
):
    if (school is None) == (demo_request is None):
        raise ValidationError({"school": "Choose either a school or a demo request."})

    recipient = _recipient_defaults(school=school, demo_request=demo_request, language=language)
    given = {
        "recipient_name": recipient_name,
        "recipient_email": recipient_email,
        "recipient_organization": recipient_organization,
    }
    recipient.update({field: value for field, value in given.items() if value})
    if not recipient["recipient_email"]:
        raise ValidationError({"recipient_email": "This school has no email. Enter one."})

    quotation = Quotation.objects.create(
        school=school,
        demo_request=demo_request,
        language=language,
        plan=plan,
        billing_cycle=billing_cycle,
        valid_until=valid_until
        or timezone.localdate() + timedelta(days=settings.QUOTATION_VALID_DAYS),
        vat_rate=Decimal(settings.QUOTATION_VAT_RATE) if vat_rate is None else vat_rate,
        notes=notes,
        created_by=actor.user,
        **recipient,
    )
    quotation.number = f"Q-{timezone.localtime(quotation.created_at).year}-{quotation.pk:05d}"
    _replace_items(quotation, items)
    quotation.save()

    record_event(
        actor,
        Action.QUOTATION_CREATED,
        quotation,
        label=f"{quotation.number} - {quotation.recipient_organization}",
        school=school,
        details={"total": str(quotation.total)},
    )
    return quotation


EDITABLE_QUOTATION_FIELDS = {
    "language",
    "plan",
    "billing_cycle",
    "valid_until",
    "vat_rate",
    "notes",
    "recipient_name",
    "recipient_email",
    "recipient_organization",
}


@transaction.atomic
def update_quotation(*, actor, quotation_id, items=None, **changes):
    quotation = _lock_quotation(quotation_id)
    if quotation.status != Quotation.Status.DRAFT:
        raise ValidationError({"status": "Only a draft quotation can be changed."})
    unknown = set(changes) - EDITABLE_QUOTATION_FIELDS
    if unknown:
        raise ValidationError({field: "This field can't be changed." for field in unknown})

    for field, value in changes.items():
        setattr(quotation, field, value)
    if items is not None:
        _replace_items(quotation, items)
    else:
        # A new VAT rate changes the totals even when the lines stay the same.
        lines = [
            {"quantity": i.quantity, "unit_price": i.unit_price} for i in quotation.items.all()
        ]
        quotation.subtotal, quotation.vat_amount, quotation.total = quotation_totals(
            lines, quotation.vat_rate
        )
    quotation.save()

    record_event(
        actor,
        Action.QUOTATION_UPDATED,
        quotation,
        label=f"{quotation.number} - {quotation.recipient_organization}",
        school=quotation.school,
        details={"fields": sorted([*changes, *(["items"] if items is not None else [])])},
    )
    return quotation


@transaction.atomic
def send_quotation(*, actor, quotation_id):
    """Emails the PDF. A sent quotation can be sent again, such as after a bounce."""
    quotation = _lock_quotation(quotation_id)
    if quotation.status not in (Quotation.Status.DRAFT, Quotation.Status.SENT):
        raise ValidationError({"status": "An answered quotation can't be sent again."})
    if quotation.valid_until < timezone.localdate():
        raise ValidationError({"valid_until": "This quotation has expired. Change its date first."})
    if not quotation.items.exists():
        raise ValidationError({"items": "Add at least one line before sending."})

    resend = quotation.status == Quotation.Status.SENT
    quotation.status = Quotation.Status.SENT
    quotation.sent_at = timezone.now()
    quotation.save(update_fields=["status", "sent_at", "updated_at"])

    record_event(
        actor,
        Action.QUOTATION_SENT,
        quotation,
        label=f"{quotation.number} - {quotation.recipient_organization}",
        school=quotation.school,
        details={"to": quotation.recipient_email, "resend": resend},
    )
    transaction.on_commit(lambda: send_quotation_email_task.delay(quotation.pk), robust=True)
    return quotation


@transaction.atomic
def respond_to_quotation(*, actor, quotation_id, accepted):
    quotation = _lock_quotation(quotation_id)
    if quotation.status != Quotation.Status.SENT:
        raise ValidationError({"status": "Only a sent quotation can be accepted or rejected."})

    quotation.status = Quotation.Status.ACCEPTED if accepted else Quotation.Status.REJECTED
    quotation.responded_at = timezone.now()
    quotation.save(update_fields=["status", "responded_at", "updated_at"])

    record_event(
        actor,
        Action.QUOTATION_ACCEPTED if accepted else Action.QUOTATION_REJECTED,
        quotation,
        label=f"{quotation.number} - {quotation.recipient_organization}",
        school=quotation.school,
    )
    return quotation
