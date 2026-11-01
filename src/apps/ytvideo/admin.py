from django.contrib import admin
from .models import YtVideo,YtVideoChunks,Conversation,OutboxEvent

admin.site.register(YtVideoChunks)
admin.site.register(YtVideo)
admin.site.register(Conversation)
admin.site.register(OutboxEvent)