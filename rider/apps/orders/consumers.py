import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.orders.models import Order
from apps.orders.services import order_service


class OrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.order_id = self.scope["url_route"]["kwargs"]["order_id"]
        self.group_name = f"order_{self.order_id}"
        
        # Verify order exists
        order_exists = await self.order_exists(self.order_id)
        if not order_exists:
            await self.close()
            return
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Send initial order status
        order_data = await self.get_order_data(self.order_id)
        await self.send(text_data=json.dumps({
            "type": "order_status",
            "data": order_data
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            
            if message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def order_update(self, event):
        """Send order update to WebSocket"""
        await self.send(text_data=json.dumps(event["data"]))

    async def rider_assigned(self, event):
        """Send rider assignment notification"""
        await self.send(text_data=json.dumps({
            "type": "rider_assigned",
            "data": event["data"]
        }))

    async def location_update(self, event):
        """Send rider location update"""
        await self.send(text_data=json.dumps({
            "type": "location_update",
            "data": event["data"]
        }))

    @database_sync_to_async
    def order_exists(self, order_id):
        try:
            Order.objects.get(id=order_id)
            return True
        except Order.DoesNotExist:
            return False

    @database_sync_to_async
    def get_order_data(self, order_id):
        tracking_info = order_service.get_order_tracking_info(order_id)
        if tracking_info:
            return {
                "order_id": str(tracking_info["order"].id),
                "order_number": tracking_info["order_number"],
                "status": tracking_info["status"],
                "rider": {
                    "id": str(tracking_info["rider"].id) if tracking_info["rider"] else None,
                    "name": tracking_info["rider"].name if tracking_info["rider"] else None,
                    "phone": tracking_info["rider"].phone if tracking_info["rider"] else None,
                } if tracking_info["rider"] else None,
                "current_location": tracking_info["current_location"],
                "estimated_delivery": tracking_info["estimated_delivery"].isoformat() if tracking_info["estimated_delivery"] else None,
            }
        return None
