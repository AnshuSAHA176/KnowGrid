from django.db import models
from pgvector.django import VectorField
from django.conf import settings

class YtVideo(models.Model):
    youtube_id = models.CharField(primary_key=True, max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='uploads')
    metadata = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.youtube_id}"

    class Meta:
        indexes = [models.Index(fields=["-created_at"], name="ytvideo_created_idx")]


class YtVideoChunks(models.Model):
    video = models.ForeignKey(YtVideo, on_delete=models.CASCADE, related_name="chunks")
    text = models.TextField()
    embeddings = VectorField(dimensions=1024)
    create_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.video.youtube_id
    
