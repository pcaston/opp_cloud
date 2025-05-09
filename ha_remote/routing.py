# ha_remote/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/ha/remote/<str:site_id>/', consumers.HomeAssistantRelayConsumer.as_asgi()),
]