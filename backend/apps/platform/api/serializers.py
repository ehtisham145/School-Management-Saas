import re

from rest_framework import serializers

from apps.platform.models import ContactMessage, DemoRequest
from apps.platform.selectors import is_email_registered
from apps.tenancy.models import School

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
SAUDI_MOBILE = re.compile(r"(?:\+?966|0)?(5[0-9]{8})")
SAUDI_PHONE = re.compile(r"(?:\+?966|0)?((?:5|1)[0-9]{8})")
ARABIC_LETTER = re.compile(r"[؀-ۿ]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
REGISTRATION_CHARACTERS = re.compile(r"(?:[^\W_]|[ /-])+")
LETTER_OR_DIGIT = re.compile(r"[^\W_]")
MAX_STUDENTS = 100_000
SEARCH_MAX_LENGTH = 100
EMAIL_IN_USE = "This email is already in use."
REQUIRED_TEXT = {"required": True, "allow_blank": False}


def _normalize_phone(value, pattern, message):
    digits = re.sub(r"[\s-]", "", value.translate(ARABIC_DIGITS))
    match = pattern.fullmatch(digits)
    if not match:
        raise serializers.ValidationError(message)
    return f"+966{match.group(1)}"


def normalize_saudi_mobile(value):
    """Returns the number as +9665XXXXXXXX, or raises if it isn't a Saudi mobile."""
    return _normalize_phone(value, SAUDI_MOBILE, "Enter a valid Saudi mobile number.")


def normalize_saudi_phone(value):
    """Accepts a Saudi mobile or landline, and returns it with the +966 prefix."""
    return _normalize_phone(value, SAUDI_PHONE, "Enter a valid Saudi phone number.")


def _registration_number(value):
    """Letters, numbers, spaces, - and /. Blank is fine, because these are optional."""
    number = value.translate(ARABIC_DIGITS)
    if number and not (
        REGISTRATION_CHARACTERS.fullmatch(number) and LETTER_OR_DIGIT.search(number)
    ):
        raise serializers.ValidationError("Use only letters, numbers, spaces, - and /.")
    return number


class SchoolSerializer(serializers.ModelSerializer):
    code = serializers.SlugField(max_length=30)
    education_stages = serializers.ListField(
        child=serializers.ChoiceField(choices=School.Stage.choices), allow_empty=False
    )
    admin_email = serializers.EmailField(write_only=True)
    demo_request = serializers.IntegerField(write_only=True, required=False, min_value=1)
    member_count = serializers.IntegerField(read_only=True)
    school_admin_email = serializers.EmailField(read_only=True, allow_null=True)

    class Meta:
        model = School
        fields = [
            "id",
            "name_en",
            "name_ar",
            "code",
            "is_active",
            "created_at",
            "member_count",
            "school_admin_email",
            "school_type",
            "education_stages",
            "email",
            "phone",
            "region",
            "city",
            "address",
            "cr_number",
            "moe_license_number",
            "estimated_students",
            "admin_name",
            "admin_phone",
            "admin_email",
            "demo_request",
        ]
        read_only_fields = ["is_active", "created_at"]
        extra_kwargs = {
            "school_type": REQUIRED_TEXT,
            "email": REQUIRED_TEXT,
            "region": REQUIRED_TEXT,
            "city": REQUIRED_TEXT,
            "address": REQUIRED_TEXT,
            "admin_name": REQUIRED_TEXT,
            "admin_phone": REQUIRED_TEXT,
            "estimated_students": {
                "required": True,
                "allow_null": False,
                "min_value": 1,
                "max_value": MAX_STUDENTS,
            },
        }

    def validate_name_en(self, value):
        if not LATIN_LETTER.search(value) or ARABIC_LETTER.search(value):
            raise serializers.ValidationError("Enter the name in English letters.")
        return value

    def validate_name_ar(self, value):
        if not ARABIC_LETTER.search(value):
            raise serializers.ValidationError("Enter the name in Arabic letters.")
        return value

    def validate_code(self, value):
        code = value.lower()
        if School.objects.filter(code=code).exists():
            raise serializers.ValidationError("This code is already in use.")
        return code

    def _validate_unused_email(self, value):
        if is_email_registered(value):
            raise serializers.ValidationError(EMAIL_IN_USE)
        return value

    def validate_email(self, value):
        return self._validate_unused_email(value)

    def validate_admin_email(self, value):
        return self._validate_unused_email(value)

    def validate(self, attrs):
        if attrs["email"].lower() == attrs["admin_email"].lower():
            raise serializers.ValidationError({"admin_email": EMAIL_IN_USE})
        return attrs

    def validate_education_stages(self, value):
        # Removes repeats and stores the stages in school order.
        return [stage for stage in School.Stage.values if stage in value]

    def validate_phone(self, value):
        return normalize_saudi_phone(value) if value else value

    def validate_admin_phone(self, value):
        return normalize_saudi_mobile(value)

    def validate_cr_number(self, value):
        return _registration_number(value)

    def validate_moe_license_number(self, value):
        return _registration_number(value)


class SchoolFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["active", "inactive"], required=False)
    search = serializers.CharField(required=False, max_length=SEARCH_MAX_LENGTH)


class LeadSerializer(serializers.ModelSerializer):
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)


class DemoRequestSerializer(LeadSerializer):
    phone = serializers.CharField(required=False, allow_blank=True, max_length=30)

    class Meta:
        model = DemoRequest
        fields = ["name", "school_name", "email", "phone", "plan", "message", "website"]

    def validate_phone(self, value):
        return normalize_saudi_mobile(value) if value else value


class ContactMessageSerializer(LeadSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "school_name", "email", "message", "website"]


class DemoRequestAdminSerializer(serializers.ModelSerializer):
    """What the platform panel reads. Only the status and notes can be changed."""

    admin_notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    converted_school_code = serializers.CharField(
        source="converted_school.code", read_only=True, default=None
    )

    class Meta:
        model = DemoRequest
        fields = [
            "id",
            "name",
            "school_name",
            "email",
            "phone",
            "plan",
            "message",
            "status",
            "admin_notes",
            "converted_school_code",
            "created_at",
        ]
        read_only_fields = [
            "name",
            "school_name",
            "email",
            "phone",
            "plan",
            "message",
            "created_at",
        ]


class DemoRequestFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=DemoRequest.Status.choices, required=False)
    search = serializers.CharField(required=False, max_length=SEARCH_MAX_LENGTH)
