from django.db import models
from pgvector.django import VectorField
from django.conf import settings
import uuid
from django.utils import timezone


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
    processing_token = models.PositiveBigIntegerField(default=0)
    lock_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.youtube_id}"

    class Meta:
        indexes = [models.Index(fields=["-created_at"], name="ytvideo_created_idx")]


class YtVideoChunks(models.Model):
    video = models.ForeignKey(
        YtVideo,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    text = models.TextField()
    embeddings = VectorField(dimensions=1024)
    start_time = models.FloatField()
    end_time = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["video", "chunk_index"],
                name="unique_video_chunk_idx",
            )
        ]


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations"
    )
    video = models.ForeignKey(
        YtVideo, on_delete=models.CASCADE, related_name="conversations"
    )
    messages = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"User: {self.user.email} | Video: {self.video_id} | Conversation: {self.id}"

    class Meta:
        indexes = [models.Index(fields=["user", "video"], name="user_video_idx")]


class OutboxEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        PUBLISHED = "PUBLISHED", "Published"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100)
    aggregate_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    available_at = models.DateTimeField(default=timezone.now)
    processing_token = models.UUIDField(null=True, blank=True)
    lock_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "available_at"]),
            models.Index(fields=["status", "lock_until"]),
        ]
