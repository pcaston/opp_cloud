# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Your existing URLs
    path('', views.dashboard, name='dashboard'),
    path('site/<str:site_id>/', views.site_interface, name='site_interface'),
    path('site/<str:site_id>/delete/', views.delete_site, name='delete_site'),
]