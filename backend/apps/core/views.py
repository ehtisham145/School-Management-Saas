from rest_framework import viewsets

# give the data of only that school by which user is logged in


class TenantScopedViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return super().get_queryset().filter(school=self.request.school)
