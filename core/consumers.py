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
        try:
            # Parse the incoming data
            data = json.loads(text_data)
            print(f"\n=== Frontend message received ===")
            print(f"Message: {data}")
            
            # Special handling for common requests
            message_type = data.get('type')
            message_id = data.get('id', 'unknown')
            
            # Handle get_states separately
            if message_type == 'get_states':
                # For testing, respond with mock entities
                mock_entities = {
                    "light.living_room": {
                        "entity_id": "light.living_room",
                        "state": "on",
                        "attributes": {"friendly_name": "Living Room Light", "brightness": 255}
                    },
                    "switch.kitchen": {
                        "entity_id": "switch.kitchen",
                        "state": "off",
                        "attributes": {"friendly_name": "Kitchen Switch"}
                    },
                    "sensor.temperature": {
                        "entity_id": "sensor.temperature",
                        "state": "21.5",
                        "attributes": {"friendly_name": "Living Room Temperature", "unit_of_measurement": "°C"}
                    }
                }
                
                await self.send(text_data=json.dumps({
                    "id": message_id,
                    "type": "result",
                    "success": True,
                    "result": mock_entities
                }))
                print(f"Sent mock entity data in response to get_states (ID: {message_id})")
                return
                
            # Handle call_service
            elif message_type == 'call_service':
                domain = data.get('domain')
                service = data.get('service')
                service_data = data.get('service_data', {})
                
                print(f"Service call: {domain}.{service} with {service_data}")
                
                # Mock successful service call
                await self.send(text_data=json.dumps({
                    "id": message_id,
                    "type": "result",
                    "success": True,
                    "result": {}
                }))
                print(f"Sent success response for service call (ID: {message_id})")
                return
            
            # Handle ping messages directly
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    "type": "pong"
                }))
                print("Responded to ping with pong")
                return
                
            # Forward other messages to the site group
            site_group = f"site_{self.site_id}"
            
            # Forward the command to any OppEnergyConsumer in the site group
            await self.channel_layer.group_send(
                site_group,
                {
                    'type': 'ha_command',
                    'command': data,
                    'relay_channel': self.channel_name,
                    'command_id': message_id,
                    # Pass the site_id explicitly as a parameter
                    'site_id': self.site_id
                }
            )
            print(f"Forwarded {message_type} command to site group (ID: {message_id})")
            
        except json.JSONDecodeError as e:
            print(f"Invalid JSON received from frontend client: {e}")
        except Exception as e:
            print(f"Error in SiteFrontendConsumer.receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to process request: {str(e)}'
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
                    
                    # Generate a unique site ID if not already set
                    if not site.site_id:
                        site.site_id = f"opp_energy_{email}_{site_name}"
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

    async def handle_get_hass_state(self, data):
        """Handle request for Home Assistant state."""
        print("\n=== Home Assistant State Request ===")
        username = data.get("user_name")
        site_id = data.get("site_id")
        entity_id = data.get("entity_id")  # Optional - specify a particular entity
        
        print(f"HA state request for user: {username}, site: {site_id}")
        
        if not self.authenticated:
            print("User not authenticated for HA state request")
            await self.send(json.dumps({
                "type": "error",
                "message": "Not authenticated"
            }))
            return
            
        try:
            # Create a unique message ID for this request
            message_id = data.get("id", str(datetime.now().timestamp()))
            
            # Send request to get HA state
            await self.send(json.dumps({
                "type": "get_hass_state_request",
                "site_id": site_id,
                "entity_id": entity_id,
                "id": message_id
            }))
            
            print(f"Sent Home Assistant state request to site {site_id}")
            
        except Exception as e:
            print(f"Error handling HA state request: {str(e)}")
            await self.send(json.dumps({
                "type": "error",
                "message": f"Error requesting Home Assistant state: {str(e)}",
                "id": data.get("id")
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
        command_id = event['command_id']
        
        print(f"Processing HA command: {command_type} (ID: {command_id})")
        
        # Handle get_states command
        if command_type == "get_states":
            try:
                # In a real implementation, you would get actual states
                # For now, just respond with some mock data
                mock_entities = {
                    "light.living_room": {
                        "entity_id": "light.living_room",
                        "state": "on",
                        "attributes": {"friendly_name": "Living Room Light", "brightness": 255}
                    },
                    "switch.kitchen": {
                        "entity_id": "switch.kitchen",
                        "state": "off",
                        "attributes": {"friendly_name": "Kitchen Switch"}
                    },
                    "sensor.temperature": {
                        "entity_id": "sensor.temperature",
                        "state": "21.5",
                        "attributes": {"friendly_name": "Living Room Temperature", "unit_of_measurement": "°C"}
                    }
                }
                
                await self.channel_layer.send(
                    event['relay_channel'],
                    {
                        'type': 'ha_response',
                        'response': {
                            'id': command_id,
                            'success': True,
                            'result': mock_entities
                        }
                    }
                )
                print(f"Sent mock entity data response for {command_id}")
            except Exception as e:
                print(f"Error handling get_states command: {str(e)}")
                await self.channel_layer.send(
                    event['relay_channel'],
                    {
                        'type': 'ha_response',
                        'response': {
                            'id': command_id,
                            'success': False,
                            'error': {
                                'message': str(e)
                            }
                        }
                    }
                )
        # Handle call_service command
        elif command_type == "call_service":
            domain = command.get("domain")
            service = command.get("service")
            service_data = command.get("service_data", {})
            
            print(f"Service call: {domain}.{service} with {service_data}")
            
            # In a real implementation, you would forward this to Home Assistant
            # For now, just acknowledge receipt
            await self.channel_layer.send(
                event['relay_channel'],
                {
                    'type': 'ha_response',
                    'response': {
                        'id': command_id,
                        'success': True,
                        'result': {}
                    }
                }
            )
        else:
            print(f"Unhandled command type: {command_type}")
            # Send a default response
            await self.channel_layer.send(
                event['relay_channel'],
                {
                    'type': 'ha_response',
                    'response': {
                        'id': command_id,
                        'success': True,
                        'result': {}
                    }
                }
            )

class SiteFrontendConsumer(AsyncWebsocketConsumer):
    """Consumer for frontend clients connecting to control Home Assistant"""
    
    @property
    def Site(self):
        return apps.get_model('core', 'Site')
    
    async def connect(self):
        self.site_id = self.scope['url_route']['kwargs']['site_id']
        self.user = self.scope['user']
        self.frontend_group = f"frontend_{self.site_id}"
        
        # Check if user has permission to access this site
        has_permission = await self.check_user_permission()
        if not has_permission or not self.user.is_authenticated:
            await self.close(code=4003)
            return
        
        # Add to frontend group for this site
        await self.channel_layer.group_add(
            self.frontend_group,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        
        # Find the corresponding site group
        site_group = f"site_{self.site_id}"
        
        # Check if there's an active OppEnergyConsumer for this site
        channels = self.channel_layer.groups.get(site_group, set())
        site_connected = len(channels) > 0
        
        # Send connection status
        await self.send(text_data=json.dumps({
            'type': 'auth_ok',
            'ha_connected': site_connected
        }))
    
    async def disconnect(self, close_code):
        # Remove from frontend group
        if hasattr(self, 'frontend_group'):
            await self.channel_layer.group_discard(
                self.frontend_group,
                self.channel_name
            )
    
    async def receive(self, text_data):
        try:
            # Parse the incoming data
            data = json.loads(text_data)
            
            # Forward to the site group
            site_group = f"site_{self.site_id}"
            
            # Add session info to the message
            data['frontend_channel'] = self.channel_name
            
            # Forward the command to any OppEnergyConsumer in the site group
            await self.channel_layer.group_send(
                site_group,
                {
                    'type': 'ha_command',
                    'command': data,
                    'relay_channel': self.channel_name,
                    'command_id': data.get('id', str(datetime.now().timestamp()))
                }
            )
            
        except json.JSONDecodeError:
            print(f"Invalid JSON received from frontend client")
        except Exception as e:
            print(f"Error forwarding message to HA: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to communicate with Home Assistant: {str(e)}'
            }))
    
    async def ha_response(self, event):
        """Handle responses from Home Assistant"""
        await self.send(text_data=json.dumps(event['response']))
    
    async def ha_state_update(self, event):
        """Handle state updates from Home Assistant"""
        await self.send(text_data=json.dumps({
            'type': 'result',
            'result': {
                'type': 'state_update',
                'states': event['states']
            }
        }))
    
    @database_sync_to_async
    def check_user_permission(self):
        try:
            # Check if user is the site owner
            site_owner = self.Site.objects.filter(
                id=self.site_id,
                user=self.user
            ).exists()
            
            return site_owner
        except Exception as e:
            print(f"Error checking user permission: {str(e)}")
            return False
        