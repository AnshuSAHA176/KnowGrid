from django.db import models
import uuid
from apps.ytvideo.models import YtVideo
from django.conf import settings


class CodingChallenge(models.Model):
    class DifficultyChoices(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    video = models.ForeignKey(YtVideo, on_delete=models.PROTECT, related_name="codings")
    title = models.CharField(max_length=300)
    description = models.TextField()
    difficulty = models.CharField(max_length=300, choices=DifficultyChoices.choices)
    constraints = models.TextField()
    starter_code = models.TextField()
    reference_solution = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TestCase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    challenge = models.ForeignKey(
        CodingChallenge, on_delete=models.CASCADE, related_name="testcases"
    )
    input_data = models.JSONField()
    expected_output = models.JSONField()
    is_hidden = models.BooleanField(default=True)

    def __str__(self):
        return self.challenge.title


class Submission(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        ACCEPTED = "accepted", "Accepted"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(
        settings.AUTH_USER_MODLE, on_delete=models.CASCADE, related_name="submissions"
    )
    challenge = models.ForeignKey(
        CodingChallenge, models.CASCADE, related_name="submissions"
    )
    source_code = models.TextField()
    status = models.CharField(
        max_length=200, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.challenge.title