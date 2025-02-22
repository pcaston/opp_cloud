from django.urls import re_path
from core import consumers

websocket_urlpatterns = [
    re_path(r'ws/opp_energy/?$', consumers.OppEnergyConsumer.as_asgi()),
]