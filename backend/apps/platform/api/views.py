from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.platform.api.serializers import (
    ContactMessageSerializer,
    DemoRequestSerializer,
    SchoolSerializer,
)
from apps.platform.selectors import list_schools
from apps.platform.services import (
    create_contact_message,
    create_demo_request,
    create_school_with_admin,
)


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


class PublicLeadView(APIView):
    """A public form. It needs no session, so a stale login can't block it."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "leads"
    serializer_class = None
    create_lead = None

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = dict(serializer.validated_data)
        # Bots fill this hidden field. They get a normal reply and nothing is saved.
        if not data.pop("website", ""):
            self.create_lead(**data)
        return Response(status=201)


class DemoRequestView(PublicLeadView):
    serializer_class = DemoRequestSerializer
    create_lead = staticmethod(create_demo_request)


class ContactMessageView(PublicLeadView):
    serializer_class = ContactMessageSerializer
    create_lead = staticmethod(create_contact_message)
