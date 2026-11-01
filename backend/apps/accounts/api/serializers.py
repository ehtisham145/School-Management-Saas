from rest_framework import serializers


class SwitchSchoolSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class TOTPConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=6, min_length=6)


class EmailOTPConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)


class EmailOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailOTPLoginVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
