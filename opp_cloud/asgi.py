"""
ASGI config for opp_cloud project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'opp_cloud.settings')
django.setup()

# Import WebSocket URL patterns from core - these should take priority
from core.routing import websocket_urlpatterns as core_websocket_urlpatterns

# Import the ha_remote patterns separately for clarity
from ha_remote.routing import websocket_urlpatterns as ha_remote_websocket_urlpatterns

# IMPORTANT: Put core patterns BEFORE ha_remote patterns to ensure
# they get priority in routing decisions
all_websocket_urlpatterns = core_websocket_urlpatterns + ha_remote_websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(URLRouter(all_websocket_urlpatterns)),
})