"""Define Django ORM models"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class CustomUser(AbstractUser):
    """Custom user model extending Django's AbstractUser"""
    created_at = models.DateTimeField(auto_now_add=True)
    # Add additional fields for custom user here

    def __str__(self) -> str:
        return str(self.username)

class HomeAssistantInstance(models.Model):
    """Class representing a Home Assistant Instance"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    instance_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    api_token = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    last_connected = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.instance_id})"
      
class EnergyPrice(models.Model):
    """Class representing Energy Prices"""
    buy_price = models.DecimalField(max_digits=10, decimal_places=4)
    sell_price = models.DecimalField(max_digits=10, decimal_places=4)
    timestamp = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()

    def __str__(self) -> str:
        return f"Buy: {self.buy_price}, Sell: {self.sell_price}"
    
class Device(models.Model):
    """Class representing a Home Assistant Energy Management Site"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self) -> str:
        return f"{self.name} ({self.user})"