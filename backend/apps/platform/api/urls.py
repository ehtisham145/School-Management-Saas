from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.platform.api.views import ContactMessageView, DemoRequestView, SchoolViewSet

router = SimpleRouter()
router.register("schools", SchoolViewSet, basename="platform-school")

urlpatterns = [
    path("demo-requests/", DemoRequestView.as_view(), name="demo-request"),
    path("contact-messages/", ContactMessageView.as_view(), name="contact-message"),
    *router.urls,
]
