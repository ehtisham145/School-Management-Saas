import re

from rest_framework import serializers

from apps.platform.models import ContactMessage, DemoRequest
from apps.tenancy.models import School

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
SAUDI_MOBILE = re.compile(r"(?:\+?966|0)?(5[0-9]{8})")


def normalize_saudi_mobile(value):
    """Returns the number as +9665XXXXXXXX, or raises if it isn't a Saudi mobile."""
    digits = re.sub(r"[\s-]", "", value.translate(ARABIC_DIGITS))
    match = SAUDI_MOBILE.fullmatch(digits)
    if not match:
        raise serializers.ValidationError("Enter a valid Saudi mobile number.")
    return f"+966{match.group(1)}"


class SchoolSerializer(serializers.ModelSerializer):
    code = serializers.SlugField(max_length=30)
    admin_email = serializers.EmailField(write_only=True)
    member_count = serializers.IntegerField(read_only=True)

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
            "admin_email",
        ]
        read_only_fields = ["is_active", "created_at"]

    def validate_code(self, value):
        code = value.lower()
        if School.objects.filter(code=code).exists():
            raise serializers.ValidationError("This code is already in use.")
        return code


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
