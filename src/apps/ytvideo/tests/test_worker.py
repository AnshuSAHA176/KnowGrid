
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.ytvideo.models import YtVideo, YtVideoChunks
from apps.ytvideo.worker import process_youtube_video


class WorkerIdempotencyTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="worker_test@example.com",
            password="test-password",
        )

        self.youtube_id = "dQw4w9WgXcQ"
        self.url = f"https://youtu.be/{self.youtube_id}"

        self.video = YtVideo.objects.create(
            youtube_id=self.youtube_id,
            user=self.user,
            status=YtVideo.ProcessingStatus.READY,
            metadata={"title": "Test video"},
        )

    def test_T07_ready_video_is_not_processed_again(self):
        initial_status = self.video.status
        initial_token = self.video.processing_token
        initial_chunks = YtVideoChunks.objects.filter(
            video=self.video
        ).count()

        process_youtube_video.run(
            video_id=self.youtube_id,
            url=self.url,
        )

        self.video.refresh_from_db()

        self.assertEqual(self.video.status, initial_status)
        self.assertEqual(self.video.processing_token, initial_token)
        self.assertEqual(
            YtVideoChunks.objects.filter(video=self.video).count(),
            initial_chunks,
        )

    def test_T08_active_lease_prevents_second_worker(self):
        token = 5

        self.video.status = YtVideo.ProcessingStatus.PROCESSING
        self.video.processing_token = token
        self.video.lock_until = timezone.now() + timedelta(minutes=10)

        self.video.save(update_fields=[
            "status",
            "processing_token",
            "lock_until",
        ])

        process_youtube_video.run(
            video_id=self.youtube_id,
            url=self.url,
        )

        self.video.refresh_from_db()

        self.assertEqual(
            self.video.status,
            YtVideo.ProcessingStatus.PROCESSING,
        )
        self.assertEqual(self.video.processing_token, token)
        self.assertGreater(self.video.lock_until, timezone.now())

    def test_T09_expired_lease_allows_new_worker(self):
        old_token = 5

        self.video.status = YtVideo.ProcessingStatus.PROCESSING
        self.video.processing_token = old_token
        self.video.lock_until = timezone.now() - timedelta(minutes=5)

        self.video.save(update_fields=[
            "status",
            "processing_token",
            "lock_until",
        ])

        process_youtube_video.run(
            video_id=self.youtube_id,
            url=self.url,
        )

        self.video.refresh_from_db()

        self.assertEqual(
            self.video.processing_token,
            old_token + 1,
        )
        self.assertEqual(
            self.video.status,
            YtVideo.ProcessingStatus.READY,
        )
        self.assertIsNone(self.video.lock_until)
