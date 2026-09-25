from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from .chat_service import ChatValidationError, mark_chat_read, send_chat_message, user_can_access_chat
from .models import Chat


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.group_name = f"chat_{self.chat_id}"
        if not await self._can_connect():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._mark_read()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") != "message":
            await self.send_json({"type": "error", "message": "Noma’lum amal."})
            return
        try:
            payload = await self._create_message(content.get("text", ""))
        except ChatValidationError as error:
            await self.send_json({"type": "error", "code": error.code, "message": error.message})
            return
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "chat.message", "payload": payload},
        )

    async def chat_message(self, event):
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _can_connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            return False
        chat = Chat.objects.select_related("seller__user").filter(pk=self.chat_id).first()
        return chat is not None and user_can_access_chat(user, chat)

    @database_sync_to_async
    def _mark_read(self):
        chat = Chat.objects.select_related("seller__user").get(pk=self.chat_id)
        return mark_chat_read(chat, self.scope["user"])

    @database_sync_to_async
    def _create_message(self, text):
        message = send_chat_message(self.chat_id, self.scope["user"], text)
        created_at = timezone.localtime(message.created_at)
        return {
            "type": "message",
            "id": message.pk,
            "text": message.text,
            "sender_id": message.sender_id,
            "sender_name": message.sender.get_full_name() or message.sender.email,
            "created_at": created_at.isoformat(),
            "time": created_at.strftime("%H:%M"),
        }
