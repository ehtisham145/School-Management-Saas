from rest_framework import serializers


class SwitchSchoolSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField()
