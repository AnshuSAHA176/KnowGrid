
import json

from channels.generic.websocket import AsyncWebsocketConsumer


class SendEventConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        submission_id = self.scope["url_route"]["kwargs"]["submission_id"]

        # Use the same group name as the Celery task
        self.group_name = f"submission_{submission_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )
        await self.accept()
        await self.send(text_data='connect')

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def send_event(self, event):
        await self.send(
            text_data=json.dumps(event["message"])
        )

