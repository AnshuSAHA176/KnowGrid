from django.db import models
from pgvector.django import VectorField
from django.conf import settings
import uuid

class YtVideo(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"
    youtube_id = models.CharField(primary_key=True, max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploads"
    )
    status = models.CharField(
    max_length=20,
    choices=ProcessingStatus.choices,
    default=ProcessingStatus.PENDING,
    db_index=True,
)
    metadata = models.JSONField(default={})
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
    start_time = models.FloatField()
    end_time = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.video.youtube_id

    class Meta:
        indexes = [
            models.Index(
                fields=["start_time", "end_time"], name="start_time&end_time_inx"
            )
        ]


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='conversations')
    video = models.ForeignKey(YtVideo,on_delete=models.CASCADE,related_name='conversations')
    messages = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'user:- {self.user.email} | {self.question}'
    class Meta:
        indexes = [
            models.Index(fields=['user','video'],name='user_video_idx')

        ]
