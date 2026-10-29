
from django.test import TestCase
from django_redis import get_redis_connection

from apps.ytvideo.services import check_slot, release_slot
from apps.ytvideo.services import MAX_PENDING_JOBS


class AdmissionControlTests(TestCase):
    def setUp(self):
        self.redis = get_redis_connection("default")
        self.counter_key = "admission:video"
        self.reserved_key = "admission:video:reserved"

        self.redis.delete(self.counter_key, self.reserved_key)

    def tearDown(self):
        self.redis.delete(self.counter_key, self.reserved_key)

    def test_first_job_is_accepted(self):
        result = check_slot("test_video_1")
        self.assertEqual(result, "accepted")

    def test_duplicate_job_does_not_consume_another_slot(self):
        first = check_slot("test_video_2")
        second = check_slot("test_video_2")

        self.assertEqual(first, "accepted")
        self.assertEqual(second, "already_in_queue")

        slot = int(self.redis.hget(self.counter_key, "slot"))
        self.assertEqual(slot, 1)

    def test_capacity_full_rejects_new_job(self):
        self.redis.hset(self.counter_key, "slot", MAX_PENDING_JOBS)

        result = check_slot("test_video_3")

        self.assertEqual(result, "capacity_full")

    def test_release_removes_reservation_and_decrements_slot(self):
        check_slot("test_video_4")

        result = release_slot("test_video_4")

        self.assertEqual(result, "job_removed")
        self.assertEqual(
            int(self.redis.hget(self.counter_key, "slot")),
            0,
        )
        self.assertFalse(
            self.redis.sismember(self.reserved_key, "test_video_4")
        )

    def test_releasing_same_job_twice_does_not_decrement_twice(self):
        check_slot("test_video_5")

        first = release_slot("test_video_5")
        second = release_slot("test_video_5")

        self.assertEqual(first, "job_removed")
        self.assertEqual(second, "job_id_not_in_queue")
        self.assertEqual(
            int(self.redis.hget(self.counter_key, "slot")),
            0,
        )
