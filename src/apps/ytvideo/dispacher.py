from .models import OutboxEvent
from .worker import process_youtube_video
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
import uuid
from datetime import timedelta


def dispacher():
    now = timezone.now()

    with transaction.atomic():
        events = (
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(
                Q(
                    status=OutboxEvent.Status.PENDING,
                    available_at__lte=now,
                )
                | Q(
                    status=OutboxEvent.Status.PROCESSING,
                    lock_until__lte=now,
                )
            )
            .order_by("created_at")
        )[:20]
        for event in events:

            event.status = OutboxEvent.Status.PENDING
            event.processing_token = uuid.uuid4()
            event.attempts += 1
            event.lock_until = timezone.now() + timedelta(minutes=15)
            event.save(
                update_fields=[
                    "status",
                    "processing_token",
                    "attempts",
                    "lock_until",
                ]
            )
