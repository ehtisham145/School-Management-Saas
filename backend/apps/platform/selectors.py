from django.db.models import Count

from apps.tenancy.models import School


def list_schools():
    return School.objects.annotate(member_count=Count("membership")).order_by("-created_at", "-id")
