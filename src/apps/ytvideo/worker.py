from celery import shared_task
from django.db import transaction

from .models import YtVideo, YtVideoChunks
from .transcipts_extract import YouTubeProcessor
from .RAG.generate_embedding import generate_embeddings, splitchunks
from django.utils import timezone
from datetime import timedelta


class ApplicationError(Exception):
    """Base exception for my custom application errors."""

    pass


# Specific exception for Celery tasks
class TaskProcessingError(ApplicationError):
    """Raised when a background task fails due to business logic."""

    def __init__(self, message):
        super().__init__(message)


@shared_task(
    bind=True,
    max_retries=3,
    name="ytvideo.process_video",
)
def process_youtube_video(self, video_id: str, url: str) -> dict:
    token = None
    try:
        with transaction.atomic():
            video = YtVideo.objects.select_for_update().get(youtube_id=video_id)
            if video.status == YtVideo.ProcessingStatus.READY:
                return {"status": "ready"}

            if video.lock_until and video.lock_until > timezone.now():
                return {"status": "already_processing"}

            video.status = YtVideo.ProcessingStatus.PROCESSING
            video.lock_until = timezone.now() + timedelta(minutes=10)
            video.processing_token += 1
            token = video.processing_token
            video.save(
                update_fields=["status", "updated_at", "lock_until", "processing_token"]
            )
        print(video.youtube_id)
        processor = YouTubeProcessor()
        result = processor.process(url)
        
        chunks = result["chunks"]
        print(len(chunks))
        chunk_texts = [chunk["text"] for chunk in chunks]

        split_batches = splitchunks(chunks=chunk_texts)
        if not split_batches:
            return
        embeddings = generate_embeddings(split_batches[0])

        for batch_inx in range(1, len(split_batches)):
            embeddings.extend(generate_embeddings(split_batches[batch_inx]))
    

        with transaction.atomic():
            video = YtVideo.objects.select_for_update().get(youtube_id=video_id)

            if video.processing_token != token:
                raise ValueError("Processing ownership lost")

            YtVideoChunks.objects.bulk_create(
                [
                    YtVideoChunks(
                        video=video,
                        chunk_index=index,
                        text=chunk["text"],
                        embeddings=embedding,
                        start_time=chunk["start"],
                        end_time=chunk["end"],
                    )
                    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings))
                ]
            )
            video.metadata = result["metadata"]
            video.status = YtVideo.ProcessingStatus.READY
            video.lock_until = None
            video.save(update_fields=["status", "updated_at", "metadata", "lock_until"])
        return {
            "video_id": video_id,
            "chunks_generated": len(chunks),
            "status": "ready",
        }

    except Exception as exc:
        ownership_lost = False
        with transaction.atomic():
            video = YtVideo.objects.select_for_update().get(youtube_id=video_id)
            if token is not None and video.processing_token != token:
                ownership_lost = True
            else:
                video.lock_until = None
                save_fields = ["lock_until", "updated_at"]
                if self.request.retries >= self.max_retries:
                    video.status = YtVideo.ProcessingStatus.FAILED
                    save_fields.append("status")
                video.save(update_fields=save_fields)
        if ownership_lost:
            raise TaskProcessingError(
                message="worker loos ownership",
            )

        if self.request.retries >= self.max_retries:
            raise exc

        raise self.retry(exc=exc, countdown=2**self.request.retries)
