from celery import shared_task
from django.db import transaction

from .models import YtVideo, YtVideoChunks
from .transcipts_extract import YouTubeProcessor
from .RAG.generate_embedding import generate_embeddings


@shared_task(
    bind=True,
    max_retries=3,
    name="ytvideo.process_video",
)
def process_youtube_video(self, video_id: str, url: str) -> dict:
    try:
        video = YtVideo.objects.get(youtube_id=video_id)
        video.status = YtVideo.ProcessingStatus.PROCESSING
        video.save(update_fields=["status", "updated_at"])
        print(video.youtube_id)
        processor = YouTubeProcessor()
        result = processor.process(url)
        print(result['metadata'])
        chunks = result["chunks"]
        print(len(chunks))
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = generate_embeddings(chunk_texts)

        with transaction.atomic():
            for chunk, embedding in zip(chunks, embeddings):
                YtVideoChunks.objects.create(
                    video=video,
                    text=chunk["text"],
                    embeddings=embedding,
                    start_time=chunk["start"],
                    end_time=chunk["end"],
                )

            video.metadata = result["metadata"]
            video.status = YtVideo.ProcessingStatus.READY
            video.save(update_fields=["status", "updated_at", "metadata"])
        return {
            "video_id": video_id,
            "chunks_generated": len(chunks),
            "status": "ready",
        }

    except Exception as exc:
        try:
            video = YtVideo.objects.get(youtube_id=video_id)
            video.status = YtVideo.ProcessingStatus.FAILED
            video.save(update_fields=["status", "updated_at"])
        except YtVideo.DoesNotExist:
            pass

        raise self.retry(exc=exc, countdown=2**self.request.retries)
