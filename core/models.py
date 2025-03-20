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
     
class EnergyPrice(models.Model):
    """Class representing Energy Prices"""
    buy_price = models.DecimalField(max_digits=10, decimal_places=4)
    sell_price = models.DecimalField(max_digits=10, decimal_places=4)
    timestamp = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()

    def __str__(self) -> str:
        return f"Buy: {self.buy_price}, Sell: {self.sell_price}"
    
class Site(models.Model):
    """Class representing a Home Assistant Energy Management Site"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    # WebSocket connection
    instance_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    ws_connected = models.BooleanField(default=False)
    last_connected = models.DateTimeField(null=True, blank=True)
    
    # Reference to the registered websocket connection in memory
    # This is a transient property, not stored in the database
    @property
    def websocket_connection(self):
        """Get the active websocket connection for this site."""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        # Generate the expected group name based on how you're storing connections
        # This might need adjustment based on your actual implementation
        group_name = f"site_{self.id}"
        
        # Check if there's an active connection
        channel_layer = get_channel_layer()
        if channel_layer:
            # This is a placeholder - you'll need to implement how to check
            # for an active connection in your channel layer
            return group_name
        return None
    
    def __str__(self) -> str:
        return f"{self.name} ({self.user})"