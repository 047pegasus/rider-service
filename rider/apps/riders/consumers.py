from channels.generic.websocket import AsyncWebsocketConsumer


class RiderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        await self.close()

    async def receive(self, text_data):
        await self.send(text_data)

    async def send_message(self, event):
        await self.send(text_data=event["text"])
