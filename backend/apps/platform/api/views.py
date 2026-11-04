from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.platform.api.serializers import (
    ContactMessageSerializer,
    DemoRequestAdminSerializer,
    DemoRequestFilterSerializer,
    DemoRequestSerializer,
    SchoolFilterSerializer,
    SchoolSerializer,
)
from apps.platform.selectors import (
    get_dashboard_overview,
    get_demo_request_counts,
    get_school_counts,
    list_demo_requests,
    list_schools,
)
from apps.platform.services import (
    create_contact_message,
    create_demo_request,
    create_school_with_admin,
    set_school_active,
    update_demo_request,
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
        if self.action != "list":
            return list_schools()
        filters = SchoolFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        return list_schools(**filters.validated_data)

    def perform_create(self, serializer):
        school = create_school_with_admin(actor=self.request.user, **serializer.validated_data)
        serializer.instance = self.get_queryset().get(pk=school.pk)

    def _set_active(self, is_active):
        school = set_school_active(
            actor=self.request.user, school=self.get_object(), is_active=is_active
        )
        return Response(self.get_serializer(school).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._set_active(True)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        return self._set_active(False)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(get_school_counts())


class DemoRequestAdminViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """The panel's inbox. It is separate from the public form, which stays write-only."""

    permission_classes = [IsVerifiedPlatformAdmin]
    serializer_class = DemoRequestAdminSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        if self.action != "list":
            return list_demo_requests()
        filters = DemoRequestFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        return list_demo_requests(**filters.validated_data)

    def perform_update(self, serializer):
        demo = update_demo_request(
            actor=self.request.user,
            demo_request_id=serializer.instance.pk,
            **serializer.validated_data,
        )
        serializer.instance = self.get_queryset().get(pk=demo.pk)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(get_demo_request_counts())


class DashboardView(APIView):
    permission_classes = [IsVerifiedPlatformAdmin]

    def get(self, request):
        overview = get_dashboard_overview()
        return Response(
            {
                "schools": overview["schools"],
                "demo_requests": overview["demo_requests"],
                "recent_schools": SchoolSerializer(overview["recent_schools"], many=True).data,
                "recent_demo_requests": DemoRequestAdminSerializer(
                    overview["recent_demo_requests"], many=True
                ).data,
            }
        )


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
