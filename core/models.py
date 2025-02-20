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
    buy_price = models.DecimalField(max_digits=10, decimal_places=4)
    sell_price = models.DecimalField(max_digits=10, decimal_places=4)
    timestamp = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()


class User(models.Model):
    user_name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Use proper password hashing
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user_name
    
class Device(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.user.user_name})"