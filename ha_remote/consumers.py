# In a new file: ha_remote/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from core.models import Site

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
            
        # Accept the connection
        await self.accept()
        
        # Join site-specific group
        self.site_group = f"site_{self.site_id}"
        await self.channel_layer.group_add(self.site_group, self.channel_name)
        
    @database_sync_to_async
    def verify_site_access(self):
        """Verify user has access to the specified site."""
        try:
            site = get_object_or_404(Site, id=self.site_id, user=self.user)
            self.site = site
            return True
        except:
            return False
            
    async def disconnect(self, close_code):
        # Leave site-specific group
        if hasattr(self, 'site_group'):
            await self.channel_layer.group_discard(self.site_group, self.channel_name)
            
    async def receive(self, text_data):
        """
        Receive command from frontend and relay to the OppEnergyConsumer
        for this site.
        """
        try:
            data = json.loads(text_data)
            command_id = data.get('id')
            
            # Forward to site-specific group
            await self.channel_layer.group_send(
                self.site_group,
                {
                    'type': 'ha_command',
                    'command': data,
                    'relay_channel': self.channel_name,
                    'command_id': command_id
                }
            )
        except json.JSONDecodeError:
            await self.send(json.dumps({
                'success': False,
                'error': {
                    'message': 'Invalid JSON'
                }
            }))
            
    async def ha_command(self, event):
        """Handle relayed command."""
        # This is handled by OppEnergyConsumer, not this consumer
        pass
            
    async def ha_response(self, event):
        """Handle response from OppEnergyConsumer."""
        # Send response back to frontend
        await self.send(text_data=json.dumps(event['response']))