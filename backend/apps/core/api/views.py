from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.selectors import is_database_reachable


class HealthView(APIView):
    """For Docker and the Deploy Script"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if is_database_reachable():
            return Response({"status": "oK"})
        return Response({"status": "unavailable"}, status=503)
