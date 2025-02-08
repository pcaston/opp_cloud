from django.urls import re_path
from core import consumers

websocket_urlpatterns = [
    re_path(r'ws/opp_energy/(?P<instance_id>\w+)/$', consumers.OppEnergyConsumer.as_asgi()),
]