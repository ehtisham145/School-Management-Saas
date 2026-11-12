from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Lead(models.Model):
    name = models.CharField(max_length=120)
    school_name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField(max_length=2000)
    is_handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email})"


class DemoRequest(Lead):
    class Plan(models.TextChoices):
        # School plans are yearly; teacher plans are monthly (see the pricing page).
        BASIC = "basic", "Basic"
        PREMIUM = "premium", "Premium"
        CUSTOM = "custom", "Custom"
        TEACHER = "teacher", "Teacher"
        TEACHER_PRO = "teacher_pro", "Teacher Pro"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        DEMO_SCHEDULED = "demo_scheduled", "Demo scheduled"
        CONVERTED = "converted", "Converted"
        REJECTED = "rejected", "Rejected"

    phone = models.CharField(max_length=30, blank=True)
    plan = models.CharField(max_length=20, choices=Plan.choices, blank=True)
    message = models.TextField(max_length=2000, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    admin_notes = models.TextField(max_length=2000, blank=True)
    converted_school = models.ForeignKey(
        "tenancy.School", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    def save(self, *args, **kwargs):
        # Status is the source of truth: a request is handled once someone has picked it up.
        self.is_handled = self.status != self.Status.NEW
        super().save(*args, **kwargs)


class ContactMessage(Lead):
    school_name = models.CharField(max_length=200, blank=True)


# --- Billing. Platform-owned: these rows describe schools, they don't belong to one.

MONEY = {"max_digits": 12, "decimal_places": 2}


class BillingCycle(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"


class Plan(models.Model):
    """A price list entry. A subscription copies the price, so editing a plan never
    changes what a school already pays."""

    code = models.SlugField(max_length=30, unique=True)
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)
    monthly_price = models.DecimalField(**MONEY)
    yearly_price = models.DecimalField(**MONEY)
    # Blank means no limit.
    max_students = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["monthly_price", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(monthly_price__gte=0, yearly_price__gte=0),
                name="plan_prices_not_negative",
            ),
        ]

    def __str__(self):
        return self.name_en

    def price_for(self, billing_cycle):
        return self.yearly_price if billing_cycle == BillingCycle.YEARLY else self.monthly_price


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"

    school = models.ForeignKey(
        "tenancy.School", on_delete=models.PROTECT, related_name="subscriptions"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices)
    price = models.DecimalField(**MONEY)
    starts_on = models.DateField()
    ends_on = models.DateField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    expired_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(max_length=1000, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_on", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["school"],
                condition=Q(status="active"),
                name="one_active_subscription_per_school",
            ),
            models.CheckConstraint(
                condition=Q(ends_on__gt=F("starts_on")), name="subscription_ends_after_start"
            ),
            models.CheckConstraint(
                condition=Q(price__gte=0), name="subscription_price_not_negative"
            ),
        ]

    def __str__(self):
        return f"{self.school} - {self.plan} ({self.billing_cycle})"


class Quotation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    class Language(models.TextChoices):
        EN = "en", "English"
        AR = "ar", "Arabic"

    # Filled in right after the row is created, from its id: Q-2026-00042.
    number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    # Exactly one of these: a school on the platform, or a prospect from a demo request.
    school = models.ForeignKey(
        "tenancy.School", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    demo_request = models.ForeignKey(
        DemoRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="quotations"
    )
    recipient_name = models.CharField(max_length=120)
    recipient_email = models.EmailField()
    recipient_organization = models.CharField(max_length=200)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.EN)
    plan = models.ForeignKey(
        Plan, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    valid_until = models.DateField()
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2)
    subtotal = models.DecimalField(**MONEY, default=0)
    vat_amount = models.DecimalField(**MONEY, default=0)
    total = models.DecimalField(**MONEY, default=0)
    notes = models.TextField(max_length=2000, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(school__isnull=False, demo_request__isnull=True)
                    | Q(school__isnull=True, demo_request__isnull=False)
                ),
                name="quotation_has_one_recipient",
            ),
            models.CheckConstraint(
                condition=Q(vat_rate__gte=0, vat_rate__lte=100), name="quotation_vat_rate_range"
            ),
        ]

    def __str__(self):
        return self.number or f"Quotation {self.pk}"

    @property
    def is_expired(self):
        """A sent quotation nobody answered before its last valid day."""
        return self.status == self.Status.SENT and self.valid_until < timezone.localdate()


class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="items")
    position = models.PositiveSmallIntegerField()
    description = models.CharField(max_length=300)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(**MONEY)
    amount = models.DecimalField(**MONEY)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "position"], name="unique_item_position_per_quotation"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1, unit_price__gte=0), name="quotation_item_valid"
            ),
        ]

    def __str__(self):
        return self.description
