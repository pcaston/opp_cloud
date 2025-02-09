import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache  # Temporary storage for sessions
from .models import HomeAssistantInstance, EnergyPrice

class OppEnergyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("\n=== WebSocket Connection Attempt ===")
        print(f"Scope URL Path: {self.scope['path']}")
        print(f"URL Route kwargs: {self.scope['url_route']['kwargs']}")
        print(f"Instance ID: {self.scope['url_route']['kwargs'].get('instance_id', 'Not provided')}")
        
        try:
            await self.accept()
            print("WebSocket connection successfully accepted")
            self.instance_id = self.scope['url_route']['kwargs'].get('instance_id')
            print(f"Connection established for instance_id: {self.instance_id}")
        except Exception as e:
            print(f"Error during connection: {str(e)}")
            raise

    async def disconnect(self, close_code):
        print("\n=== WebSocket Disconnection ===")
        print(f"Close code: {close_code}")
        if hasattr(self, 'instance_id'):
            print(f"Instance ID that disconnected: {self.instance_id}")

    async def receive(self, text_data):
        print("\n=== Received WebSocket Message ===")
        print(f"Raw message: {text_data}")
        
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            print(f"Message type: {message_type}")
            print(f"Message data: {data}")

            if message_type == "register_device":
                await self.register_device(data)
            elif message_type == "login":
                await self.login(data)
            elif message_type == "get_registered_devices":
                await self.get_registered_devices()
            else:
                print(f"Unknown message type: {message_type}")
                await self.send(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }))
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            await self.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON format"
            }))
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            await self.send(json.dumps({
                "type": "error",
                "message": "Internal server error"
            }))

    async def register_device(self, data):
        print("\n=== Device Registration Attempt ===")
        user_name = data.get("user_name")
        device_id = data.get("device_id")
        instance_id = data.get("instance_id")
        
        print(f"User Name: {user_name}")
        print(f"Device ID: {device_id}")
        print(f"Instance ID: {instance_id}")

        try:
            # Also store the device ID in a list of registered devices
            registered_devices = cache.get('registered_devices', set())
            registered_devices.add(device_id)
            cache.set('registered_devices', registered_devices)
            
            cache.set(f"device_{device_id}", {
                "user_name": user_name,
                "instance_id": instance_id
            })
            print(f"Device {device_id} successfully registered in cache")
            
            await self.send(json.dumps({
                "type": "registration_success",
                "message": "Device registered"
            }))
            print("Registration success message sent")
        except Exception as e:
            print(f"Error during device registration: {str(e)}")
            await self.send(json.dumps({
                "type": "error",
                "message": "Registration failed"
            }))

    async def login(self, data):
        print("\n=== Login Attempt ===")
        device_id = data.get("device_id")
        print(f"Device ID attempting login: {device_id}")

        try:
            device_info = cache.get(f"device_{device_id}")
            print(f"Device info from cache: {device_info}")

            if device_info:
                await self.send(json.dumps({
                    "type": "login_success",
                    "user_name": device_info["user_name"],
                    "instance_id": device_info["instance_id"]
                }))
                print("Login success message sent")
            else:
                print(f"No device found with ID: {device_id}")
                await self.send(json.dumps({
                    "type": "error",
                    "message": "Device not registered"
                }))
        except Exception as e:
            print(f"Error during login: {str(e)}")
            await self.send(json.dumps({
                "type": "error",
                "message": "Login failed"
            }))

    async def get_registered_devices(self):
        print("\n=== Retrieving Registered Devices ===")
        try:
            # Get the set of registered devices from cache
            devices = list(cache.get('registered_devices', set()))
            print(f"Found devices: {devices}")
            
            await self.send(json.dumps({
                "type": "device_list",
                "devices": devices
            }))
            print("Device list sent")
        except Exception as e:
            print(f"Error retrieving devices: {str(e)}")
            await self.send(json.dumps({
                "type": "error",
                "message": "Failed to retrieve devices"
            }))