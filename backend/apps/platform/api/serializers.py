from django.core.validators import RegexValidator
from rest_framework import serializers

from apps.platform.models import ContactMessage, DemoRequest
from apps.tenancy.models import School


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
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=30,
        validators=[RegexValidator(r"^\+?[0-9][0-9\s-]{5,28}$")],
    )

    class Meta:
        model = DemoRequest
        fields = ["name", "school_name", "email", "phone", "plan", "message", "website"]


class ContactMessageSerializer(LeadSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "school_name", "email", "message", "website"]
