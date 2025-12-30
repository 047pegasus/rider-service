from channels.generic.websocket import AsyncWebsocketConsumer


class OrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.order_id = self.scope["url_route"]["kwargs"]["order_id"]
        await self.channel_layer.group_add(f"order_{self.order_id}", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            f"order_{self.order_id}", self.channel_name
        )

    async def receive(self, text_data):
        await self.channel_layer.group_send(
            f"order_{self.order_id}", {"type": "order_update", "text": text_data}
        )

    async def order_update(self, event):
        await self.send(text_data=event["text"])
