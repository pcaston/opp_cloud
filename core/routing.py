# core/routing.py
from django.urls import path
from . import consumers

# These patterns should match your existing functionality
websocket_urlpatterns = [
    # Route for OppEnergyConsumer - main connection from HA client
    path('ws/opp_energy/', consumers.OppEnergyConsumer.as_asgi()),
    
    # Route for SiteFrontendConsumer - connections from web users
    path('ws/frontend/<str:site_id>/', consumers.SiteFrontendConsumer.as_asgi()),
    
    # Add any other existing routes...
]