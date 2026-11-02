from rest_framework import serializers

from apps.academics.models import AcademicYear


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ["id", "name", "start_date", "end_date", "is_current"]
        read_only_fields = ["is_current"]

    def validate(self, attrs):
        instance = self.instance
        start_date = attrs.get("start_date", getattr(instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(instance, "end_date", None))
        if end_date <= start_date:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})

        name = attrs.get("name", getattr(instance, "name", None))
        same_name = AcademicYear.objects.filter(school=self.context["request"].school, name=name)
        if instance:
            same_name = same_name.exclude(pk=instance.pk)
        if same_name.exists():
            raise serializers.ValidationError({"name": "This academic year already exists."})

        return attrs
