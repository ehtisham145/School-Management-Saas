"""Plans, subscriptions, quotations, usage and the audit log. Platform admins only."""

from django.http import HttpResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.selectors import list_audit_events
from apps.audit.services import actor_from_request
from apps.integrations.pdf.renderer import PdfUnavailable
from apps.platform.api.billing_serializers import (
    AuditEventFilterSerializer,
    AuditEventSerializer,
    PlanFilterSerializer,
    PlanSerializer,
    QuotationCreateSerializer,
    QuotationFilterSerializer,
    QuotationSerializer,
    QuotationUpdateSerializer,
    SchoolUsageSerializer,
    SubscriptionCreateSerializer,
    SubscriptionFilterSerializer,
    SubscriptionSerializer,
    UsageFilterSerializer,
)
from apps.platform.api.views import IsPlatformAdmin
from apps.platform.documents import quotation_filename, render_quotation_pdf
from apps.platform.selectors import (
    get_form_choices,
    get_quotation_counts,
    get_subscription_counts,
    get_usage_totals,
    list_plans,
    list_quotations,
    list_school_usage,
    list_subscriptions,
)
from apps.platform.services import (
    activate_subscription,
    create_plan,
    create_quotation,
    expire_subscription,
    respond_to_quotation,
    send_quotation,
    update_plan,
    update_quotation,
)


def _filters(serializer_class, request):
    filters = serializer_class(data=request.query_params)
    filters.is_valid(raise_exception=True)
    return {key: value for key, value in filters.validated_data.items() if value is not None}


class PlanViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """No delete: a plan that is no longer sold is switched off with is_active."""

    permission_classes = [IsPlatformAdmin]
    serializer_class = PlanSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None

    def get_queryset(self):
        if self.action != "list":
            return list_plans()
        return list_plans(**_filters(PlanFilterSerializer, self.request))

    def perform_create(self, serializer):
        plan = create_plan(actor=actor_from_request(self.request), **serializer.validated_data)
        serializer.instance = list_plans().get(pk=plan.pk)

    def perform_update(self, serializer):
        plan = update_plan(
            actor=actor_from_request(self.request),
            plan_id=serializer.instance.pk,
            **serializer.validated_data,
        )
        serializer.instance = list_plans().get(pk=plan.pk)


class SubscriptionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsPlatformAdmin]
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        if self.action != "list":
            return list_subscriptions()
        return list_subscriptions(**_filters(SubscriptionFilterSerializer, self.request))

    def get_serializer_class(self):
        return SubscriptionCreateSerializer if self.action == "create" else SubscriptionSerializer

    def create(self, request):
        serializer = SubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = activate_subscription(
            actor=actor_from_request(request), **serializer.validated_data
        )
        return Response(SubscriptionSerializer(subscription).data, status=201)

    @action(detail=True, methods=["post"])
    def expire(self, request, pk=None):
        subscription = expire_subscription(
            actor=actor_from_request(request), subscription_id=self.get_object().pk
        )
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(get_subscription_counts())


class QuotationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsPlatformAdmin]
    serializer_class = QuotationSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        if self.action != "list":
            return list_quotations()
        return list_quotations(**_filters(QuotationFilterSerializer, self.request))

    def get_serializer_class(self):
        return {
            "create": QuotationCreateSerializer,
            "partial_update": QuotationUpdateSerializer,
        }.get(self.action, QuotationSerializer)

    def _respond(self, quotation, status=200):
        return Response(QuotationSerializer(list_quotations().get(pk=quotation.pk)).data, status)

    def create(self, request):
        serializer = QuotationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quotation = create_quotation(actor=actor_from_request(request), **serializer.validated_data)
        return self._respond(quotation, status=201)

    def partial_update(self, request, pk=None):
        quotation = self.get_object()
        serializer = QuotationUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        quotation = update_quotation(
            actor=actor_from_request(request),
            quotation_id=quotation.pk,
            **serializer.validated_data,
        )
        return self._respond(quotation)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        quotation = send_quotation(
            actor=actor_from_request(request), quotation_id=self.get_object().pk
        )
        return self._respond(quotation)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        quotation = respond_to_quotation(
            actor=actor_from_request(request), quotation_id=self.get_object().pk, accepted=True
        )
        return self._respond(quotation)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        quotation = respond_to_quotation(
            actor=actor_from_request(request), quotation_id=self.get_object().pk, accepted=False
        )
        return self._respond(quotation)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        quotation = self.get_object()
        try:
            content = render_quotation_pdf(quotation)
        except PdfUnavailable:
            return Response(
                {
                    "error": {
                        "code": "pdf_unavailable",
                        "message": "PDFs can't be made on this server right now.",
                    }
                },
                status=503,
            )
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{quotation_filename(quotation)}"'
        response["Cache-Control"] = "no-store"
        return response

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(get_quotation_counts())


class UsageViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsPlatformAdmin]
    serializer_class = SchoolUsageSerializer

    def get_queryset(self):
        return list_school_usage(**_filters(UsageFilterSerializer, self.request))

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(get_usage_totals())


class FormChoicesView(APIView):
    """Active schools, open demo requests and active plans, for the billing forms."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        choices = get_form_choices()
        for plan in choices["plans"]:
            for field in ("monthly_price", "yearly_price"):
                plan[field] = f"{plan[field]:.2f}"
        return Response(choices)


class AuditEventViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Read-only: nobody can change or remove an entry through the API."""

    permission_classes = [IsPlatformAdmin]
    serializer_class = AuditEventSerializer

    def get_queryset(self):
        return list_audit_events(**_filters(AuditEventFilterSerializer, self.request))
