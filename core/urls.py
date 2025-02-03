from django.urls import path
from . import views

urlpatterns = [
    path('register_instance/', views.register_instance, name='register_instance'),
    path('update_price/', views.update_price, name='update_price'),
]