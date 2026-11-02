from rest_framework.routers import SimpleRouter

from apps.academics.api.views import AcademicYearViewSet

router = SimpleRouter()
router.register("years", AcademicYearViewSet, basename="academic-year")

urlpatterns = router.urls
