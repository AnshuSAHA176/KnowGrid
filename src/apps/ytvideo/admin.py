from django.contrib import admin
from .models import YtVideo,YtVideoChunks

admin.site.register(YtVideoChunks)
admin.site.register(YtVideo)