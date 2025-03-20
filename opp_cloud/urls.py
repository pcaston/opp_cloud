"""
opp_cloud/urls.py
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
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.shortcuts import redirect
from django.views.generic import TemplateView

# Handle the root URL - redirect to admin or remote access dashboard
def home_redirect(request):
    if request.user.is_authenticated:
        # If user is authenticated, redirect to remote dashboard
        return redirect('ha_dashboard')  # Change this to use your view function
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
    
    # Login page for remote access
    path('login/', auth_views.LoginView.as_view(template_name='ha_remote/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

]