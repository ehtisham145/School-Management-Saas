from rest_framework import serializers


class SwitchSchoolSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)
