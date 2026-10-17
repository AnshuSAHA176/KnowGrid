from urllib.parse import urlparse, parse_qs
import yt_dlp
import json
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from .RAG.chunking import chunking

import re
from typing import Any


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        video_id = parse_qs(parsed.query).get("v", [""])[0]

    elif host == "youtu.be" or host == "www.youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]

    elif host in {"youtube.com", "www.youtube.com"}:
        video_id = parsed.path.split("/")[-1]

    else:
        raise ValueError("Unsupported YouTube URL")

    if len(video_id) != 11:
        raise ValueError("Invalid YouTube video ID")

    return video_id


def get_video_metadata(url: str) -> dict:
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


def save_video_data(metadata: dict, transcript: dict) -> None:
    output_dir = Path("data/videos")
    output_dir.mkdir(parents=True, exist_ok=True)

    video_id = metadata["video_id"]

    output = {
        "metadata": metadata,
        "transcript": transcript,
    }

    output_path = output_dir / f"{video_id}.json"

    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved to: {output_path}")


def get_transcript(video_id: str) -> dict:
    api = YouTubeTranscriptApi()

    transcript = api.fetch(
        video_id,
        languages=["en", "hi"],
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
    segments: list[dict[str, Any]],
    language: str,
) -> list[dict[str, Any]]:
    if language not in {"en", "hi"}:
        raise ValueError(f"Unsupported language: {language}")

    normalized = []

    for segment in segments:
        text = segment.get("text")

        if not isinstance(text, str):
            continue

        # Language-independent cleanup
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            continue

        start = segment.get("start")
        duration = segment.get("duration")

        # Validate timestamps
        if (
            not isinstance(start, (int, float))
            or isinstance(start, bool)
            or not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or start < 0
            or duration < 0
        ):
            continue

        normalized.append(
            {
                "start": float(start),
                "duration": float(duration),
                "end": float(start + duration),
                "text": text,
                "language": language,
            }
        )

    return normalized


if __name__ == "__main__":
    url = input("Enter YouTube URL: ").strip()

    try:
        video_id = extract_video_id(url)
        metadata = get_video_metadata(url)
        transcript = get_transcript(video_id)

        normalized_segments = normalize_segments(
            segments=transcript["segments"],
            language=transcript["language"],
        )

        transcript["segments"] = normalized_segments

        save_video_data(
            metadata=metadata,
            transcript=transcript,
        )
        chunks = chunking(sagments=transcript['segments'])


        
    except Exception as exc:
        print(f"Processing failed: {type(exc).__name__}: {exc}")