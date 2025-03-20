"""
ha_remote/urls.py
URLs for the Home Assistant remote access application.
"""
from django.urls import path, include
from . import views

# URL patterns for the app
urlpatterns = [
    path('', views.dashboard, name='ha_dashboard'),
    path('site/<int:site_id>/', views.frontend, name='ha_frontend'),
    path('api/site/<int:site_id>/status/', views.site_status, name='site_status'),
    path('site/<int:site_id>/delete/', views.delete_site, name='delete_site'),
]