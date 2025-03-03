"""URLs for the Home Assistant remote access application."""
from django.urls import path, include
from . import views

# URL patterns for the app
urlpatterns = [
    path('', views.dashboard, name='ha_dashboard'),
    path('site/<int:site_id>/', views.frontend, name='ha_frontend'),
]