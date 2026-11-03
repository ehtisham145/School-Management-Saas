from rest_framework import mixins, viewsets
from rest_framework.permissions import BasePermission

from apps.platform.api.serializers import SchoolSerializer
from apps.platform.selectors import list_schools
from apps.platform.services import create_school_with_admin


class IsVerifiedPlatformAdmin(BasePermission):
    """A password-only session, such as a Django admin login, is not enough here."""

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.is_platform_admin and user.is_verified()


class SchoolViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsVerifiedPlatformAdmin]
    serializer_class = SchoolSerializer

    def get_queryset(self):
        return list_schools()

    def perform_create(self, serializer):
        school = create_school_with_admin(actor=self.request.user, **serializer.validated_data)
        serializer.instance = self.get_queryset().get(pk=school.pk)
