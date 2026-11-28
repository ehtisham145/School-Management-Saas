from django.urls import path

from apps.browser_agent.consumers import BrowserTaskConsumer

websocket_urlpatterns = [
    path("ws/browser-agent/<int:task_id>/", BrowserTaskConsumer.as_asgi()),
]
