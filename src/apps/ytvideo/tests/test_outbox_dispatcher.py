
import uuid

from datetime import timedelta
from unittest.mock import patch

from django.test import TransactionTestCase
from django.utils import timezone

from apps.ytvideo.models import OutboxEvent
from apps.ytvideo.dispacher import dispacher
from unittest.mock import patch
from django.db.models.query import QuerySet

class OutboxDispatcherTests(TransactionTestCase):

    def create_event(
        self,
        index,
        status=OutboxEvent.Status.PENDING,
        attempts=0,
        lock_until=None,
    ):
        video_id = f"test_video_{index}"

        return OutboxEvent.objects.create(
            event_type="VIDEO_PROCESS_REQUESTED",
            aggregate_id=uuid.uuid4(),
            payload={
                "video_id": video_id,
                "url": f"https://youtu.be/{video_id}",
            },
            status=status,
            attempts=attempts,
            lock_until=lock_until,
        )

    # T01: Pending event gets published successfully.

    @patch("apps.ytvideo.dispacher.process_youtube_video.delay")
    def test_pending_event_published_successfully(self, publish):

        event = self.create_event(1)

        dispacher()

        publish.assert_called_once_with(
            video_id="test_video_1",
            url="https://youtu.be/test_video_1",
        )

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PUBLISHED,
        )

        self.assertIsNotNone(event.published_at)
        self.assertIsNone(event.processing_token)
        self.assertIsNone(event.lock_until)

    # T02: Broker failure schedules a retry.

    @patch("apps.ytvideo.dispacher.process_youtube_video.delay")
    def test_broker_failure_schedules_retry(self, publish):

        event = self.create_event(2)

        publish.side_effect = Exception("Broker unavailable")

        dispacher()

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PENDING,
        )

        self.assertEqual(event.attempts, 1)
        self.assertEqual(event.last_error, "Broker unavailable")

        self.assertIsNotNone(event.available_at)
        self.assertIsNone(event.processing_token)
        self.assertIsNone(event.lock_until)

    # T03: Event becomes FAILED after maximum attempts.

    @patch("apps.ytvideo.dispacher.process_youtube_video.delay")
    def test_event_failed_after_maximum_attempts(self, publish):

        event = self.create_event(
            3,
            attempts=3,
        )

        publish.side_effect = Exception("Broker unavailable")

        dispacher()

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.FAILED,
        )

        self.assertEqual(event.attempts, 4)
        self.assertEqual(event.last_error, "Broker unavailable")

        self.assertIsNone(event.processing_token)
        self.assertIsNone(event.lock_until)

    # T04: Expired processing event can be reclaimed.

    @patch("apps.ytvideo.dispacher.process_youtube_video.delay")
    def test_expired_event_is_reclaimed(self, publish):

        event = self.create_event(
            4,
            status=OutboxEvent.Status.PROCESSING,
            attempts=1,
            lock_until=timezone.now() - timedelta(minutes=5),
        )

        old_token = uuid.uuid4()

        event.processing_token = old_token
        event.save(update_fields=["processing_token"])

        dispacher()

        publish.assert_called_once()

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PUBLISHED,
        )

        self.assertEqual(event.attempts, 2)
        self.assertIsNone(event.processing_token)

    # T05: An event with an active lease must not be reclaimed.

    @patch("apps.ytvideo.dispacher.process_youtube_video.delay")
    def test_active_processing_event_is_not_reclaimed(self, publish):

        event = self.create_event(
            5,
            status=OutboxEvent.Status.PROCESSING,
            attempts=1,
            lock_until=timezone.now() + timedelta(minutes=10),
        )

        token = uuid.uuid4()

        event.processing_token = token
        event.save(update_fields=["processing_token"])

        dispacher()

        publish.assert_not_called()

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PROCESSING,
        )

        self.assertEqual(event.processing_token, token)
        self.assertEqual(event.attempts, 1)




    @patch("apps.ytvideo.dispacher.process_youtube_video.delay")
    def test_T06_duplicate_delivery_after_finalization_failure(self, publish):

        event = self.create_event(6)

        original_update = QuerySet.update

        def fail_published_update(queryset, **kwargs):
            if kwargs.get("status") == OutboxEvent.Status.PUBLISHED:
                raise Exception("PostgreSQL unavailable")

            return original_update(queryset, **kwargs)

        # First dispatch: broker accepts, PostgreSQL finalization fails.
        with patch.object(
            QuerySet,
            "update",
            autospec=True,
            side_effect=fail_published_update,
        ):
            with self.assertRaises(Exception):
                dispacher()

        publish.assert_called_once()

        event.refresh_from_db()

        # Event must remain PROCESSING because publishing succeeded.
        self.assertEqual(
            event.status,
            OutboxEvent.Status.PROCESSING,
        )

        # Simulate the processing lease expiring.
        event.lock_until = timezone.now() - timedelta(seconds=1)
        event.save(update_fields=["lock_until"])

        # Second dispatch reclaims and republishes the event.
        dispacher()

        self.assertEqual(publish.call_count, 2)

        # Both publications must represent the same logical job.
        self.assertEqual(
            publish.call_args_list[0],
            publish.call_args_list[1],
        )

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PUBLISHED,
        )
