"""Every app's WebSocket routes, collected for config/asgi.py."""

from apps.browser_agent.routing import websocket_urlpatterns as browser_agent_routes

websocket_urlpatterns = [
    *browser_agent_routes,
]
