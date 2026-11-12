from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class SwitchSchoolSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False, max_length=128)

    def validate_password(self, value):
        # Django's validators: length, common passwords, all digits, too close to the username.
        try:
            validate_password(value, self.context["user"])
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value


class EmailOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailOTPLoginVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
