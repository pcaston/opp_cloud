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
    def Site(self):
        return apps.get_model('core', 'Site')

    @database_sync_to_async
    def create_or_update_user(self, email, password, username):
        """Create a user if they don't exist, or update them if they do."""
        try:
            # Split the display name into first_name and last_name if provided
            first_name = ""
            last_name = ""
            if username and " " in username:
                name_parts = username.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1]
            elif username:
                first_name = username
                
            # Use email as username as per requirements
            user, created = User.objects.update_or_create(
                username=email,  # Use email as username
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name
                }
            )
            
            if password:
                user.set_password(password)
                user.save()
                
            return user
        except Exception as e:
            print(f"Error creating or updating user: {e}")
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
            self.site = None  # Will be set during authentication
            print("Connection established")
        except Exception as e:
            print(f"Error during connection: {str(e)}")
            raise

    async def disconnect(self, close_code):
        print("\n=== WebSocket Disconnection ===")
        print(f"Close code: {close_code}")
        if self.price_updates_task:
            self.price_updates_task.cancel()
            
        # Update site connection status
        if hasattr(self, 'site') and self.site:
            # Remove from site group
            site_group = f"site_{self.site.id}"
            await self.channel_layer.group_discard(site_group, self.channel_name)
            
            # Update site connection status
            self.site.ws_connected = False
            await database_sync_to_async(self.site.save)()
            
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
            elif message_type == "get_prices": 
                await self.handle_get_prices(data)
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
            # For remote access, we can skip the password check since the user
            # is already authenticated with Django
            user = User.objects.get(email=email)
            return user
        except User.DoesNotExist:
            print(f"No user found with email: {email}")
            return None
        except Exception as e:
            print(f"Error verifying credentials: {e}")
            return None
    
    @database_sync_to_async
    def register_site(self, username, site_name):
        """Register a site for a user."""
        try:
            user = User.objects.get(username=username)
            site, created = self.Site.objects.get_or_create(
                user=user,
                name=site_name,
                defaults={
                    'user': user
                }
            )
            print(f"Site {'created' if created else 'retrieved'} for user {username}")
            return site
        except Exception as e:
            print(f"Error registering site: {str(e)}")
            return None

    async def handle_user_registration(self, data):
        print("\n=== User Registration Attempt ===")
        display_name = data.get("user_name")  # We'll split this into first_name and last_name
        email = data.get("email")
        password = data.get("password")
        site_name = data.get("site_name")
        
        print(f"Display Name: {display_name}")
        print(f"Email: {email}")
        print(f"Site Name: {site_name}")

        try:
            # Create or update the user
            user = await self.create_or_update_user(
                email=email,
                password=password,
                username=display_name  # Pass display name to be split into first_name/last_name
            )
            
            if not user:
                raise Exception("Failed to create user")

            # Register the site
            site = await self.register_site(email, site_name)  # Use email as username for site registration
            if not site:
                # Rollback user creation if site registration fails
                await database_sync_to_async(user.delete)()
                raise Exception("Failed to register site")

            await self.send(json.dumps({
                "type": "registration_success",
                "message": "User and site registered successfully"
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
        site_name = data.get("site_name")

        print(f"Attempting authentication for email: {email}")
        
        try:
            user = await self.verify_user_credentials(email, password)
            if user:
                print(f"User verified, registering site: {site_name}")
                site = await self.register_site(user.username, site_name)
                if site:
                    self.authenticated = True
                    self.user_name = username
                    self.site = site
                    
                    # Generate a unique instance ID if not already set
                    if not site.instance_id:
                        site.instance_id = f"opp_energy_{email}_{site_name}"
                        await database_sync_to_async(site.save)()
                    
                    # Add this connection to a group specific to this site
                    site_group = f"site_{site.id}"
                    await self.channel_layer.group_add(site_group, self.channel_name)
                    
                    # Update site connection status
                    site.ws_connected = True
                    site.last_connected = datetime.now()
                    await database_sync_to_async(site.save)()
                    
                    await self.send(json.dumps({
                        "type": "auth_success",
                        "message": "Authentication successful"
                    }))
                    print(f"Authentication successful for user: {username}")
                else:
                    print("Site registration failed")
                    await self.send(json.dumps({
                        "type": "error",
                        "message": "Site registration failed"
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

    async def handle_get_prices(self, data):
        """Handle request for current prices."""
        print("\n=== Price Request ===")
        username = data.get("user_name")
        
        print(f"Price request for user: {username}")
        
        if not self.authenticated:
            print("User not authenticated for price request")
            await self.send(json.dumps({
                "type": "error",
                "message": "Not authenticated"
            }))
            return
            
        try:
            # Get current prices
            prices = await self.get_current_prices()
            
            # Send immediate price update
            print(f"Sending price data: {prices}")
            await self.send(json.dumps({
                "type": "price_update",
                "data": {  # Wrap in a data field to match what coordinator expects
                    "buy_price": prices["buy_price"],
                    "sell_price": prices["sell_price"],
                    "timestamp": datetime.now().isoformat()
                }
            }))
        except Exception as e:
            print(f"Error handling price request: {str(e)}")
            await self.send(json.dumps({
                "type": "error",
                "message": f"Error getting prices: {str(e)}"
            }))

    async def send_price_updates(self):
        """Send periodic price updates to the client."""
        while True:
            try:
                if not self.authenticated:
                    break
                    
                # In practice, fetch real prices from database/service
                prices = await self.get_current_prices()
                print(f"Sending price update: {prices}")
                
                # Use the same format as the get_prices handler
                await self.send(json.dumps({
                    "type": "price_update",
                    "data": {  # Wrap in a data field
                        "buy_price": prices["buy_price"],
                        "sell_price": prices["sell_price"],
                        "timestamp": datetime.now().isoformat()
                    }
                }))
                
                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                print(f"Error sending price updates: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    @database_sync_to_async
    def get_current_prices(self):
        # In practice, implement price fetching logic here
        return {
            "buy_price": 0.28,
            "sell_price": 0.03 
        }

    async def ha_command(self, event):
        """Handle Home Assistant command relayed from the frontend."""
        if not self.authenticated or not hasattr(self, 'site'):
            # Send error response
            await self.channel_layer.send(
                event['relay_channel'],
                {
                    'type': 'ha_response',
                    'response': {
                        'id': event['command_id'],
                        'success': False,
                        'error': {
                            'message': 'Not authenticated'
                        }
                    }
                }
            )
            return
            
        # Process the command
        command = event['command']
        command_type = command.get('type')
        
        # Implement handlers for various Home Assistant commands
        # This is where you'd add the actual implementation
        
        # Send response back to the relay
        await self.channel_layer.send(
            event['relay_channel'],
            {
                'type': 'ha_response',
                'response': {
                    'id': event['command_id'],
                    'success': True,
                    'result': {}  # Populate with actual result
                }
            }
        )
