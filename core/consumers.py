import json
from datetime import datetime
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()  # This will get your CustomUser model

""" OPP Energey Consumer """
class OppEnergyConsumer(AsyncWebsocketConsumer):
    @property
    def Device(self):
        return apps.get_model('core', 'Device')

    @database_sync_to_async
    def create_user(self, email, password, username):
        """Create a user."""
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password  # create_user handles password hashing
            )
            return user
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
        
    async def connect(self):
        print("\n=== WebSocket Connection Attempt ===")
        try:
            await self.accept()
            print("WebSocket connection successfully accepted")
            self.authenticated = False
            self.price_updates_task = None
            self.ping_timeout_task = None
            self.last_ping = datetime.now()
            print("Connection established")
        except Exception as e:
            print(f"Error during connection: {str(e)}")
            raise

    async def disconnect(self, close_code):
        print("\n=== WebSocket Disconnection ===")
        print(f"Close code: {close_code}")
        if self.price_updates_task:
            self.price_updates_task.cancel()
        if hasattr(self, 'user_name'):
            print(f"User disconnected: {self.user_name}")

    async def receive(self, text_data):
        print("\n=== Received WebSocket Message ===")
        print(f"Raw message: {text_data}")
        
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            print(f"Message type: {message_type}")
            print(f"Message data: {data}")
            if message_type == "ping":
                await self.handle_ping()
            elif message_type == "user_registration":
                await self.handle_user_registration(data)
            elif message_type == "authenticate":
                await self.handle_authentication(data)
            elif message_type == "subscribe_prices":
                await self.handle_price_subscription(data)
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
                "message": f"Internal server error: {str(e)}"
            }))

    @database_sync_to_async
    def verify_user_credentials(self, email, password):
        """Verify user credentials against the database."""
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            print(f"No user found with email: {email}")
            return None
        except Exception as e:
            print(f"Error verifying credentials: {e}")
            return None

    @database_sync_to_async
    def register_device(self, username, device_name):
        """Register a device for a user."""
        try:
            user = User.objects.get(username=username)
            device, created = self.Device.objects.get_or_create(
                user=user,
                name=device_name,
                defaults={
                    'user': user
                }
            )
            print(f"Device {'created' if created else 'retrieved'} for user {username}")
            return device
        except Exception as e:
            print(f"Error registering device: {str(e)}")
            return None

    async def handle_user_registration(self, data):
        print("\n=== User Registration Attempt ===")
        username = data.get("user_name")
        email = data.get("email")
        password = data.get("password")
        device_name = data.get("device_name")
        
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Device Name: {device_name}")

        try:
            # Create the user
            user = await self.create_user(
                email=email,
                password=password,
                username=username
            )
            
            if not user:
                raise Exception("Failed to create user")

            # Register the device
            device = await self.register_device(username, device_name)
            if not device:
                # Rollback user creation if device registration fails
                await database_sync_to_async(user.delete)()
                raise Exception("Failed to register device")

            await self.send(json.dumps({
                "type": "registration_success",
                "message": "User and device registered successfully"
            }))
            
        except Exception as e:
            print(f"Error during registration: {str(e)}")
            await self.send(json.dumps({
                "type": "error",
                "message": f"Registration failed: {str(e)}"
            }))

    async def handle_authentication(self, data):
        """Handle authentication request."""
        print("\n=== Authentication Attempt ===")
        username = data.get("user_name")
        email = data.get("email")
        password = data.get("password")
        device_name = data.get("device_name")

        print(f"Attempting authentication for email: {email}")
        
        try:
            user = await self.verify_user_credentials(email, password)
            if user:
                print(f"User verified, registering device: {device_name}")
                device = await self.register_device(user.username, device_name)
                if device:
                    self.authenticated = True
                    self.user_name = username
                    
                    await self.send(json.dumps({
                        "type": "auth_success",
                        "message": "Authentication successful"
                    }))
                    print(f"Authentication successful for user: {username}")
                else:
                    print("Device registration failed")
                    await self.send(json.dumps({
                        "type": "error",
                        "message": "Device registration failed"
                    }))
            else:
                print("Invalid credentials")
                await self.send(json.dumps({
                    "type": "error",
                    "message": "Invalid credentials"
                }))
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            await self.send(json.dumps({
                "type": "error",
                "message": f"Authentication error: {str(e)}"
            }))

    async def handle_ping(self):
        """Handle ping message from client."""
        self.last_ping = datetime.now()
        await self.send(json.dumps({"type": "pong"}))

    async def handle_price_subscription(self, data):
        """Handle price subscription request."""
        if not self.authenticated:
            await self.send(json.dumps({
                "type": "error",
                "message": "Not authenticated"
            }))
            return

        # Cancel existing price updates task if it exists
        if self.price_updates_task:
            self.price_updates_task.cancel()

        # Start new price updates task
        self.price_updates_task = asyncio.create_task(self.send_price_updates())

    async def send_price_updates(self):
        """Send periodic price updates to the client."""
        while True:
            try:
                if not self.authenticated:
                    break
                # In practice, fetch real prices from database/service
                prices = await self.get_current_prices()
                print(f"Sending price update: {prices}")
                await self.send(json.dumps({
                    "type": "price_update",
                    "buy_price": prices["buy_price"],
                    "sell_price": prices["sell_price"],
                    "timestamp": datetime.now().isoformat()
                }))
                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                print(f"Error sending price updates: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    @database_sync_to_async
    def get_current_prices(self):
        # In practice, implement price fetching logic here
        return {
            "buy_price": 0.03,  # Example price
            "sell_price": 0.28  # Example price
        }
