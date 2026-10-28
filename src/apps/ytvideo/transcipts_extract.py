
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from .RAG.chunking import chunking


class YouTubeProcessor:
    SUPPORTED_LANGUAGES = ["en", "hi"]

    def __init__(self, output_dir: str = "data/videos"):
        self.output_dir = Path(output_dir)

    def extract_video_id(self, url: str) -> str:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        video_id = None

        if hostname in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [None])[0]
            elif parsed.path.startswith(("/live/", "/embed/", "/shorts/")):
                video_id = parsed.path.split("/")[2]

        elif hostname == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]

        if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("Invalid YouTube video ID")

        return video_id
    def get_video_metadata(self, url: str) -> dict:
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "video_id": info.get("id"),
            "title": info.get("title"),
            "channel": info.get("channel"),
            "description": info.get("description"),
            "duration_seconds": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "webpage_url": info.get("webpage_url"),
        }

    def get_transcript(self, video_id: str) -> dict:
        transcript = YouTubeTranscriptApi().fetch(
            video_id,
            languages=self.SUPPORTED_LANGUAGES,
        )

        return {
            "language": transcript.language_code,
            "segments": [
                {
                    "start": snippet.start,
                    "duration": snippet.duration,
                    "text": snippet.text,
                }
                for snippet in transcript
            ],
        }

    def normalize_segments(
        self,
        segments: list[dict[str, Any]],
        language: str,
    ) -> list[dict[str, Any]]:
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")

        normalized = []

        for segment in segments:
            text = segment.get("text")
            start = segment.get("start")
            duration = segment.get("duration")

            if not isinstance(text, str):
                continue

            text = re.sub(r"\s+", " ", text).strip()

            if not text:
                continue

            if (
                not isinstance(start, (int, float))
                or isinstance(start, bool)
                or not isinstance(duration, (int, float))
                or isinstance(duration, bool)
                or start < 0
                or duration < 0
            ):
                continue

            normalized.append({
                "start": float(start),
                "duration": float(duration),
                "end": float(start + duration),
                "text": text,
                "language": language,
            })

        return normalized

    def process(self, url: str) -> dict:
        print("1. Extracting video ID", flush=True)
        video_id = self.extract_video_id(url)

        print("2. Fetching metadata", flush=True)
        metadata = self.get_video_metadata(url)
        print("2. Metadata fetched", flush=True)

        print("3. Fetching transcript", flush=True)
        transcript = self.get_transcript(video_id)
        print("3. Transcript fetched", flush=True)

        print("4. Normalizing transcript", flush=True)
        transcript["segments"] = self.normalize_segments(
            transcript["segments"],
            transcript["language"],
        )
       
      
        print("5. Generating chunks", flush=True)
        chunks = chunking(sagments=transcript["segments"])
        print(f"5. Generated {len(chunks)} chunks", flush=True)

        

        return {
            "metadata": metadata,
            "transcript": transcript,
            "chunks": chunks,
        }

if __name__ == "__main__":
    processor = YouTubeProcessor()
    url = input("Enter YouTube URL: ").strip()

    try:
        result = processor.process(url)
        print(f"Processed: {result['metadata']['title']}")
        print(f"Transcript segments: {len(result['transcript']['segments'])}")
        print(f"Chunks generated: {len(result['chunks'])}")
    except Exception as exc:
        print(f"Processing failed: {type(exc).__name__}: {exc}")
