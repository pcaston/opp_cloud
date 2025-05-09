# ha_remote/consumers.py
### Frontend
# The `SiteFrontendConsumer` in the core module handles direct web browser connections using the Django app's UI.
#  Allows web users to view and control their Home Assistant sites through opp_cloud.
# - **URL Pattern**: `ws/frontend/<str:site_id>/`

# ### Remote
# - The `HomeAssistantRelayConsumer` in the ha_remote module serves as a relay or bridge between the application and Home Assistant.
# - Handles connections that relay commands between your web application and a remote Home Assistant instance.
# - cts as an intermediary that forwards commands from web clients to Home Assistant and returns responses.
# - `ws/ha/remote/<str:site_id>/`.



import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from core.models import Site

# Import the integration's domain
OPP_ENERGY_DOMAIN = 'opp_energy'

_LOGGER = logging.getLogger(__name__)

class HomeAssistantRelayConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that relays commands to the existing OppEnergyConsumer
    for a specific site.
    """
    
    async def connect(self):
        # Get site ID from URL path
        self.site_id = self.scope['url_route']['kwargs']['site_id']
        self.user = self.scope['user']
        
        # Check if user is authenticated and has access to this site
        if not self.user.is_authenticated:
            await self.close(code=4003)  # Unauthorized
            return
            
        # Verify user has access to this site
        has_access = await self.verify_site_access()
        if not has_access:
            await self.close(code=4004)  # Forbidden
            return
        
        # Get the coordinator for this site
        self.coordinator = await self.get_site_coordinator()
        if not self.coordinator:
            _LOGGER.error(f"No coordinator found for site {self.site_id}")
            await self.close(code=4005)  # No coordinator
            return
            
        # Accept the connection
        await self.accept()
        
        # Join site-specific group
        self.site_group = f"site_{self.site_id}"
        await self.channel_layer.group_add(self.site_group, self.channel_name)
        
        # Set up session tracking
        self.session_id = f"web_{self.channel_name}"
        self.subscriptions = []
        
        # Send initial connection status
        await self.send(text_data=json.dumps({
            "type": "auth_ok",
            "ha_connected": self.coordinator._is_connected()
        }))
        
    @database_sync_to_async
    def verify_site_access(self):
        """Verify user has access to the specified site."""
        try:
            site = get_object_or_404(Site, id=self.site_id, user=self.user)
            self.site = site
            return True
        except:
            return False
    
    @database_sync_to_async
    def get_site_coordinator(self):
        """Get the OppEnergyDataUpdateCoordinator for this site."""
        # Get Home Assistant instance
        from django.apps import apps
        
        try:
            hass_app = apps.get_app_config('ha_remote')
            if not hasattr(hass_app, 'hass'):
                _LOGGER.error("Home Assistant instance not available")
                return None
                
            hass = hass_app.hass
            
            # Check if integration is loaded
            if OPP_ENERGY_DOMAIN not in hass.data:
                _LOGGER.error(f"Integration {OPP_ENERGY_DOMAIN} not loaded in Home Assistant")
                return None
                
            # Find coordinator for this site
            for entry_id, data in hass.data[OPP_ENERGY_DOMAIN].items():
                if hasattr(data, 'site_name') and data.site_name == self.site.name:
                    return data
                    
            _LOGGER.error(f"No coordinator found for site {self.site.name}")
            
        except Exception as e:
            _LOGGER.error(f"Error getting coordinator: {str(e)}")
            
        return None
            
    async def disconnect(self, close_code):
        # Leave site-specific group
        if hasattr(self, 'site_group'):
            await self.channel_layer.group_discard(self.site_group, self.channel_name)
            
        # Clean up event subscriptions
        if hasattr(self, 'coordinator') and hasattr(self, 'subscriptions'):
            for subscription_id in self.subscriptions:
                if hasattr(self.coordinator, '_event_subscriptions') and subscription_id in self.coordinator._event_subscriptions:
                    unsub = self.coordinator._event_subscriptions.pop(subscription_id)
                    if callable(unsub):
                        unsub()
            
    async def receive(self, text_data):
        """
        Receive command from frontend and relay to the OppEnergyDataUpdateCoordinator.
        """
        try:
            message = json.loads(text_data)
            message_type = message.get('type')
            message_id = message.get('id')
            
            # Handle different message types
            if message_type == 'get_states':
                await self.handle_get_states(message_id)
            elif message_type == 'call_service':
                await self.handle_call_service(message)
            elif message_type == 'subscribe_events':
                await self.handle_subscribe_events(message)
            else:
                # Forward to coordinator
                await self.forward_to_coordinator(message)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Invalid JSON'
            }))
        except Exception as e:
            _LOGGER.error(f"Error processing message: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'id': message.get('id') if 'message' in locals() else None,
                'error': str(e)
            }))
    
    async def handle_get_states(self, message_id):
        """Handle get_states command."""
        try:
            if not self.coordinator:
                raise ValueError("Coordinator not available")
            
            # Get states using the coordinator
            states = await self.coordinator._handle_get_states({})
            
            # Send the response
            await self.send(text_data=json.dumps({
                "type": "result",
                "id": message_id,
                "result": states
            }))
            
        except Exception as e:
            _LOGGER.error(f"Error getting states: {str(e)}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "id": message_id,
                "error": str(e)
            }))
    
    async def handle_call_service(self, message):
        """Handle call_service command."""
        try:
            if not self.coordinator:
                raise ValueError("Coordinator not available")
            
            # Extract parameters
            domain = message.get('domain')
            service = message.get('service')
            service_data = message.get('service_data', {})
            
            if not domain or not service:
                raise ValueError("Domain and service are required")
            
            # Call the service using coordinator
            result = await self.coordinator._handle_call_service({
                "domain": domain,
                "service": service,
                "service_data": service_data
            })
            
            # Send the response
            await self.send(text_data=json.dumps({
                "type": "result",
                "id": message.get('id'),
                "result": result
            }))
            
        except Exception as e:
            _LOGGER.error(f"Error calling service: {str(e)}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "id": message.get('id'),
                "error": str(e)
            }))
    
    async def handle_subscribe_events(self, message):
        """Handle subscribe_events command."""
        try:
            if not self.coordinator:
                raise ValueError("Coordinator not available")
            
            # Extract parameters
            event_type = message.get('event_type', 'state_changed')
            
            # Subscribe to events using coordinator
            result = await self.coordinator._handle_subscribe_events({
                "session_id": self.session_id,
                "event_type": event_type
            })
            
            # Store subscription ID
            subscription_id = result.get('subscription_id')
            if subscription_id:
                self.subscriptions.append(subscription_id)
                
                # Set up event handler to receive events
                # The coordinator will forward events to us through the channel layer
                
            # Send confirmation response
            await self.send(text_data=json.dumps({
                "type": "result",
                "id": message.get('id'),
                "result": {"subscribed": True, "subscription_id": subscription_id}
            }))
            
        except Exception as e:
            _LOGGER.error(f"Error subscribing to events: {str(e)}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "id": message.get('id'),
                "error": str(e)
            }))
    
    async def forward_to_coordinator(self, message):
        """Forward message to the coordinator."""
        try:
            if not self.coordinator:
                raise ValueError("Coordinator not available")
            
            # Add session information
            message["session_id"] = self.session_id
            
            # Send to coordinator and get response
            response = await self.coordinator._send_message_with_response(message)
            
            # Send response back to client
            await self.send(text_data=json.dumps({
                "type": "result",
                "id": message.get('id'),
                "result": response
            }))
            
        except Exception as e:
            _LOGGER.error(f"Error forwarding message to coordinator: {str(e)}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "id": message.get('id'),
                "error": str(e)
            }))
            
    async def ha_command(self, event):
        """Handle relayed command."""
        # This is used when other systems need to relay commands through this consumer
        pass
            
    async def ha_response(self, event):
        """Handle response from coordinator."""
        # Send response back to frontend
        await self.send(text_data=json.dumps(event['response']))
        
    async def ha_event(self, event):
        """Handle event from Home Assistant."""
        # Forward event to frontend
        await self.send(text_data=json.dumps({
            "type": event['event_type'],
            "data": event['data']
        }))