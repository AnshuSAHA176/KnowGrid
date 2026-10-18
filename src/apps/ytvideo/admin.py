from django.contrib import admin
from .models import YtVideo,YtVideoChunks,Conversation

admin.site.register(YtVideoChunks)
admin.site.register(YtVideo)
admin.site.register(Conversation)