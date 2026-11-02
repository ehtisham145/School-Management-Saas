from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import HasPolicy


class TenantScopedViewSet(viewsets.ModelViewSet):
    """Limits every request to the logged-in school and checks role policies."""

    permission_classes = [IsAuthenticated, HasPolicy]
    policies = {}

    def get_queryset(self):
        queryset = super().get_queryset().filter(school=self.request.school)
        return queryset if queryset.ordered else queryset.order_by("pk")

    def perform_create(self, serializer):
        serializer.save(school=self.request.school)

    def perform_update(self, serializer):
        serializer.save(school=self.request.school)
