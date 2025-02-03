import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import HomeAssistantInstance, EnergyPrice

class OppEnergyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.instance_id = self.scope['url_route']['kwargs']['instance_id']
        self.room_group_name = f'opp_energy_{self.instance_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        
        if await self.authenticate_instance():
            await self.accept()
        else:
            await self.close()