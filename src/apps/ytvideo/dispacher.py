from .models import OutboxEvent
from .worker import process_youtube_video
from django.db.models import Q, F
from django.utils import timezone
from django.db import transaction
import uuid
from datetime import timedelta


def dispacher():
    now = timezone.now()

    with transaction.atomic():
        events = list(
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
            .order_by("created_at")[:20]
        )
        tokens = []
        for event in events:

            event.status = OutboxEvent.Status.PROCESSING
            token = uuid.uuid4()
            tokens.append(token)
            event.processing_token = token
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

    for event, token in zip(events, tokens):
      
        # 1. Only catch broker publishing failures.
        try:
            process_youtube_video.delay(
                video_id=event.payload["video_id"],
                url=event.payload["url"],
            )

        except Exception as exc:

            queryset = OutboxEvent.objects.filter(
                id=event.id,
                processing_token=token,
                status=OutboxEvent.Status.PROCESSING,
                lock_until__gt=timezone.now(),
            )

            if event.attempts >= 4:
                queryset.update(
                    status=OutboxEvent.Status.FAILED,
                    last_error=str(exc),
                    processing_token=None,
                    lock_until=None,
                )
            else:
                delay = 2 ** (event.attempts - 1)

                queryset.update(
                    status=OutboxEvent.Status.PENDING,
                    available_at=timezone.now() + timedelta(seconds=delay),
                    last_error=str(exc),
                    processing_token=None,
                    lock_until=None,
                )

                continue


                # 2. Database finalization happens OUTSIDE the broker exception handler.
        updated = OutboxEvent.objects.filter(
                    id=event.id,
                    processing_token=token,
                    status=OutboxEvent.Status.PROCESSING,
                    lock_until__gt=timezone.now(),
                ).update(
                    status=OutboxEvent.Status.PUBLISHED,
                    published_at=timezone.now(),
                    processing_token=None,
                    lock_until=None,
                )

        if updated == 0:
            continue