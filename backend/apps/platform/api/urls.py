from rest_framework.routers import SimpleRouter

from apps.platform.api.views import SchoolViewSet

router = SimpleRouter()
router.register("schools", SchoolViewSet, basename="platform-school")

urlpatterns = router.urls
