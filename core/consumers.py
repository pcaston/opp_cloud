import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache  # Temporary storage for sessions
from .models import HomeAssistantInstance, EnergyPrice

class OppEnergyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("WebSocket connection established.")

    async def disconnect(self, close_code):
        print("WebSocket connection closed.")

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "register_device":
            await self.register_device(data)
        elif message_type == "login":
            await self.login(data)
        elif message_type == "get_registered_devices":
            await self.get_registered_devices()

    async def register_device(self, data):
        """Register a device for a user."""
        user_name = data.get("user_name")
        device_id = data.get("device_id")
        instance_id = data.get("instance_id")

        # Store in cache (Replace with DB in production)
        cache.set(f"device_{device_id}", {"user_name": user_name, "instance_id": instance_id})

        await self.send(json.dumps({"type": "registration_success", "message": "Device registered"}))

    async def login(self, data):
        """Authenticate a device based on stored session."""
        device_id = data.get("device_id")
        device_info = cache.get(f"device_{device_id}")

        if device_info:
            await self.send(json.dumps({
                "type": "login_success",
                "user_name": device_info["user_name"],
                "instance_id": device_info["instance_id"]
            }))
        else:
            await self.send(json.dumps({"type": "error", "message": "Device not registered"}))

    async def get_registered_devices(self):
        """Retrieve all registered devices."""
        devices = [key.split("_")[1] for key in cache.keys("device_*")]
        await self.send(json.dumps({"type": "device_list", "devices": devices}))
