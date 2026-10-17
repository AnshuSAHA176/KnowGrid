
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
        host = parsed.hostname or ""
        video_id = ""

        if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif host in {"youtu.be", "www.youtu.be"}:
            video_id = parsed.path.strip("/").split("/")[0]
        else:
            raise ValueError("Unsupported YouTube URL")

        if len(video_id) != 11:
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

    def save_video_data(self, metadata: dict, transcript: dict) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        video_id = metadata["video_id"]
        output_path = self.output_dir / f"{video_id}.json"

        output_path.write_text(
            json.dumps(
                {"metadata": metadata, "transcript": transcript},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return output_path

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

        self.save_video_data(metadata, transcript)

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
