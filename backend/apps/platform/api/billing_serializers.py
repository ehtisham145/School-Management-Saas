"""Serializers for plans, subscriptions, quotations, usage and the audit log."""

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.audit.models import AuditEvent
from apps.platform.api.serializers import (
    ARABIC_LETTER,
    LATIN_LETTER,
    MAX_STUDENTS,
    SEARCH_MAX_LENGTH,
    SchoolFilterSerializer,
)
from apps.platform.models import BillingCycle, DemoRequest, Plan, Quotation, Subscription
from apps.tenancy.models import School

MAX_PRICE = Decimal("999999999.99")
MAX_START_OFFSET_DAYS = 366
MAX_QUOTATION_ITEMS = 50
MAX_ITEM_QUANTITY = 10_000


def money_field(**kwargs):
    return serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal(0), max_value=MAX_PRICE, **kwargs
    )


class SchoolRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "code", "name_en", "name_ar"]
        read_only_fields = fields


class PlanRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "code", "name_en", "name_ar"]
        read_only_fields = fields


class ListFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=SEARCH_MAX_LENGTH)


# --- Plans


class PlanSerializer(serializers.ModelSerializer):
    code = serializers.SlugField(max_length=30)
    monthly_price = money_field()
    yearly_price = money_field()
    max_students = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=MAX_STUDENTS
    )
    active_subscriptions = serializers.IntegerField(read_only=True)

    class Meta:
        model = Plan
        fields = [
            "id",
            "code",
            "name_en",
            "name_ar",
            "monthly_price",
            "yearly_price",
            "max_students",
            "is_active",
            "active_subscriptions",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate_code(self, value):
        code = value.lower()
        if self.instance is not None:
            if code != self.instance.code:
                raise serializers.ValidationError("The code can't be changed.")
        elif Plan.objects.filter(code=code).exists():
            raise serializers.ValidationError("This code is already in use.")
        return code

    def validate_name_en(self, value):
        if not LATIN_LETTER.search(value) or ARABIC_LETTER.search(value):
            raise serializers.ValidationError("Enter the name in English letters.")
        return value

    def validate_name_ar(self, value):
        if not ARABIC_LETTER.search(value):
            raise serializers.ValidationError("Enter the name in Arabic letters.")
        return value


class PlanFilterSerializer(serializers.Serializer):
    active = serializers.BooleanField(required=False, allow_null=True, default=None)


# --- Subscriptions


class SubscriptionSerializer(serializers.ModelSerializer):
    school = SchoolRefSerializer(read_only=True)
    plan = PlanRefSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "school",
            "plan",
            "billing_cycle",
            "price",
            "starts_on",
            "ends_on",
            "status",
            "expired_at",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class SubscriptionCreateSerializer(serializers.Serializer):
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all())
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    billing_cycle = serializers.ChoiceField(choices=BillingCycle.choices)
    starts_on = serializers.DateField(required=False)
    # Left out, the plan's price for the cycle is used. A value records an agreed discount.
    price = money_field(required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000, default="")

    def validate_starts_on(self, value):
        if abs((value - timezone.localdate()).days) > MAX_START_OFFSET_DAYS:
            raise serializers.ValidationError("Choose a start date within a year of today.")
        return value

    def validate(self, attrs):
        attrs.setdefault("starts_on", timezone.localdate())
        return attrs


class SubscriptionFilterSerializer(ListFilterSerializer):
    status = serializers.ChoiceField(choices=Subscription.Status.choices, required=False)
    school = serializers.IntegerField(required=False, min_value=1)


# --- Quotations


class QuotationItemSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=300)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_ITEM_QUANTITY)
    unit_price = money_field()


class QuotationItemReadSerializer(serializers.Serializer):
    description = serializers.CharField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class QuotationSerializer(serializers.ModelSerializer):
    school = SchoolRefSerializer(read_only=True)
    plan = PlanRefSerializer(read_only=True)
    items = QuotationItemReadSerializer(many=True, read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Quotation
        fields = [
            "id",
            "number",
            "status",
            "is_expired",
            "school",
            "demo_request",
            "recipient_name",
            "recipient_email",
            "recipient_organization",
            "language",
            "plan",
            "billing_cycle",
            "valid_until",
            "vat_rate",
            "subtotal",
            "vat_amount",
            "total",
            "notes",
            "items",
            "sent_at",
            "responded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class QuotationUpdateSerializer(serializers.Serializer):
    """Changing a draft. The recipient (school or demo request) is fixed once created."""

    language = serializers.ChoiceField(choices=Quotation.Language.choices, required=False)
    plan = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(), required=False, allow_null=True
    )
    billing_cycle = serializers.ChoiceField(
        choices=BillingCycle.choices, required=False, allow_blank=True
    )
    valid_until = serializers.DateField(required=False)
    vat_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal(0),
        max_value=Decimal(100),
        required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    recipient_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    recipient_email = serializers.EmailField(required=False, allow_blank=True)
    recipient_organization = serializers.CharField(required=False, allow_blank=True, max_length=200)
    items = QuotationItemSerializer(many=True, required=False)

    def validate_valid_until(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Choose today or a later date.")
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Add at least one line.")
        if len(value) > MAX_QUOTATION_ITEMS:
            raise serializers.ValidationError(f"Use at most {MAX_QUOTATION_ITEMS} lines.")
        return value


class QuotationCreateSerializer(QuotationUpdateSerializer):
    school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(), required=False, allow_null=True, default=None
    )
    demo_request = serializers.PrimaryKeyRelatedField(
        queryset=DemoRequest.objects.all(), required=False, allow_null=True, default=None
    )
    items = QuotationItemSerializer(many=True)

    def validate(self, attrs):
        if (attrs.get("school") is None) == (attrs.get("demo_request") is None):
            raise serializers.ValidationError(
                {"school": "Choose either a school or a demo request."}
            )
        return attrs


class QuotationFilterSerializer(ListFilterSerializer):
    status = serializers.ChoiceField(choices=Quotation.Status.choices, required=False)


# --- Usage


class SchoolUsageSerializer(serializers.ModelSerializer):
    students = serializers.IntegerField(read_only=True)
    teachers = serializers.IntegerField(read_only=True)
    parents = serializers.IntegerField(read_only=True)
    staff = serializers.IntegerField(read_only=True)
    active_users = serializers.IntegerField(read_only=True)
    plan = serializers.SerializerMethodField()
    subscription_ends_on = serializers.DateField(read_only=True, allow_null=True)
    over_student_limit = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            "id",
            "code",
            "name_en",
            "name_ar",
            "is_active",
            "estimated_students",
            "students",
            "teachers",
            "parents",
            "staff",
            "active_users",
            "plan",
            "subscription_ends_on",
            "over_student_limit",
        ]
        read_only_fields = fields

    def get_plan(self, school):
        if school.plan_code is None:
            return None
        return {
            "code": school.plan_code,
            "name_en": school.plan_name_en,
            "name_ar": school.plan_name_ar,
            "max_students": school.plan_max_students,
        }

    def get_over_student_limit(self, school):
        limit = school.plan_max_students
        return limit is not None and school.students > limit


UsageFilterSerializer = SchoolFilterSerializer


# --- Audit log

AUDIT_TARGET_TYPES = ["school", "demorequest", "plan", "subscription", "quotation"]


class AuditEventSerializer(serializers.ModelSerializer):
    school = SchoolRefSerializer(read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "action",
            "actor_label",
            "target_type",
            "target_id",
            "target_label",
            "school",
            "ip_address",
            "details",
            "created_at",
        ]
        read_only_fields = fields


class AuditEventFilterSerializer(ListFilterSerializer):
    action = serializers.ChoiceField(choices=AuditEvent.Action.choices, required=False)
    target_type = serializers.ChoiceField(choices=AUDIT_TARGET_TYPES, required=False)
    school = serializers.IntegerField(required=False, min_value=1)
