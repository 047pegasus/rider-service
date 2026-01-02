import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.riders.models import Rider
from apps.riders.services import rider_service


class RiderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.rider_id = self.scope["url_route"]["kwargs"]["ride_id"]
        self.group_name = f"rider_{self.rider_id}"
        
        # Verify rider exists
        rider_exists = await self.rider_exists(self.rider_id)
        if not rider_exists:
            await self.close()
            return
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Send initial rider location
        location = await self.get_rider_location(self.rider_id)
        if location:
            await self.send(text_data=json.dumps({
                "type": "location_update",
                "data": location
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            
            if message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
            elif message_type == "location_update":
                # Rider device sending location update via WebSocket
                location_data = data.get("data", {})
                if location_data:
                    from apps.riders.services import rider_service
                    delivery_id = location_data.get("delivery_id")
                    rider_service.update_rider_location(
                        rider_id=self.rider_id,
                        location_data=location_data,
                        delivery_id=delivery_id
                    )
        except json.JSONDecodeError:
            pass

    async def location_update(self, event):
        """Send location update to WebSocket"""
        await self.send(text_data=json.dumps({
            "type": "location_update",
            "data": event["data"]
        }))

    async def delivery_assigned(self, event):
        """Send delivery assignment notification"""
        await self.send(text_data=json.dumps({
            "type": "delivery_assigned",
            "data": event["data"]
        }))

    @database_sync_to_async
    def rider_exists(self, rider_id):
        try:
            Rider.objects.get(id=rider_id)
            return True
        except Rider.DoesNotExist:
            return False

    @database_sync_to_async
    def get_rider_location(self, rider_id):
        return rider_service.get_rider_location(str(rider_id))
 