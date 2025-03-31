from django.urls import path
from . import views

urlpatterns = [
    path('wstest/', views.wstest, name='wstest'),
    path('register_site/', views.register_site, name='register_site'),
    path('update_price/', views.update_price, name='update_price'),
]