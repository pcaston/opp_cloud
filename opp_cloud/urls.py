
"""
URL configuration for opp_cloud project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# Handle the root URL - redirect to admin or remote access dashboard
def home_redirect(request):
    if request.user.is_authenticated:
        # If user is authenticated, redirect to remote dashboard
        return redirect('remote_dashboard')
    # Otherwise redirect to login
    return redirect('login')

urlpatterns = [
    # Home redirects to admin or remote dashboard based on authentication
    path('', home_redirect, name='home'),
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('core.urls')),
    
    # Remote access app
    path('remote/', include('ha_remote.urls')),
    
    # Authentication endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Login page for remote access
    path('login/', TemplateView.as_view(template_name='ha_remote/login.html'), name='login'),
    
    # Remote dashboard
    path('dashboard/', TemplateView.as_view(template_name='ha_remote/dashboard.html'), name='remote_dashboard'),
]