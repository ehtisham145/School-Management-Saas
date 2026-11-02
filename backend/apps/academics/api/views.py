from rest_framework.decorators import action
from rest_framework.response import Response

from apps.academics.api.serializers import AcademicYearSerializer
from apps.academics.models import AcademicYear
from apps.academics.services import set_current_year
from apps.core.views import TenantScopedViewSet


class AcademicYearViewSet(TenantScopedViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    policies = {
        "list": "academics.view",
        "retrieve": "academics.view",
        "create": "academics.manage",
        "partial_update": "academics.manage",
        "set_current": "academics.manage",
    }

    @action(detail=True, methods=["post"], url_path="set-current")
    def set_current(self, request, pk=None):
        year = set_current_year(request.school, pk)
        return Response(self.get_serializer(year).data)
