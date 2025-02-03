from django.db import models
from django.contrib.auth.models import User

class HomeAssistantInstance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instance_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    api_token = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    last_connected = models.DateTimeField(auto_now=True)

class EnergyPrice(models.Model):
    instance = models.ForeignKey(HomeAssistantInstance, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=4)
    timestamp = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()