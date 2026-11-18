from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class SwitchSchoolSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)

    def validate_username(self, value):
        # Individual teachers sign in with their email, which is stored in lowercase.
        return value.lower() if "@" in value else value


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False, max_length=128)

    def validate_password(self, value):
        # Django's validators: length, common passwords, all digits, too close to the username.
        try:
            validate_password(value, self.context["user"])
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value


class TeacherSignupSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, max_length=128)
    accept_privacy = serializers.BooleanField()

    def validate_full_name(self, value):
        if not any(character.isalpha() for character in value):
            raise serializers.ValidationError("Enter your name.")
        return value

    def validate_email(self, value):
        return value.lower()

    def validate_accept_privacy(self, value):
        if not value:
            raise serializers.ValidationError("Please accept the privacy policy.")
        return value

    def validate(self, attrs):
        # An unsaved user, so the password can be compared with the name and email.
        candidate = get_user_model()(
            username=attrs["email"], email=attrs["email"], first_name=attrs["full_name"]
        )
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return attrs


class TeacherSignupRequestSerializer(TeacherSignupSerializer):
    # Hidden on the form. Only bots fill it in.
    website = serializers.CharField(required=False, allow_blank=True)


class TeacherSignupVerifySerializer(TeacherSignupSerializer):
    code = serializers.RegexField(r"^[0-9]{6}$")


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    password = serializers.CharField(trim_whitespace=False, max_length=128)
