# KnowGrid

**Turn YouTube tutorials into interactive learning experiences.**

KnowGrid is an AI-powered learning platform designed to help people move beyond watching coding tutorials to actually understanding and applying what they learn.

The goal is to transform YouTube videos into searchable learning resources, enabling users to ask questions about tutorial content, locate explanations using timestamps, and eventually practice through coding challenges.

## Current Features

- **YouTube Metadata Extraction:** Extracts video titles, channel information, descriptions, duration, thumbnails, and URLs using `yt-dlp`.
- **Transcript Extraction:** Retrieves available YouTube transcripts in English and Hindi.
- **Transcript Normalization:** Cleans transcript text, validates timestamps, and standardizes segment data.
- **Semantic Chunking:** Uses embeddings and cosine similarity to identify potential topic boundaries in transcripts.
- **Timestamp Preservation:** Stores the start and end times of chunks to support timestamp-based retrieval.
- **Vector Embeddings:** Generates embeddings for chunks for future semantic search and retrieval.
- **Background Processing:** Uses Celery to process videos asynchronously.
- **Vector Storage:** Uses PostgreSQL with `pgvector` to store chunk embeddings.

## How It Works

1. A YouTube video URL is submitted.
2. The video ID and metadata are extracted.
3. Available transcripts are fetched and normalized.
4. Transcript segments are grouped into semantic chunks using embedding similarity.
5. Embeddings are generated for the resulting chunks.
6. Video metadata, processing status, chunk text, timestamps, and embeddings are stored in PostgreSQL.

## Chunking Strategy

KnowGrid uses an embedding-based semantic chunking approach.

1. Generate an embedding for each transcript segment.
2. Calculate cosine similarity between consecutive segment embeddings.
3. Calculate the 20th-percentile similarity threshold.
4. Treat similarity scores at or below the threshold as potential topic boundaries.
5. Group segments into chunks while preserving their text and timestamps.

This approach aims to create meaningful retrieval units rather than splitting transcripts solely by a fixed number of characters.

## Tech Stack

- **Language:** Python
- **Backend:** Django
- **Task Queue:** Celery
- **Message Broker:** Redis (planned/integration dependent)
- **Database:** PostgreSQL
- **Vector Search:** pgvector
- **Video Metadata:** yt-dlp
- **Transcript Extraction:** youtube-transcript-api
- **Embeddings:** Configured embedding model

## Project Structure

```text
KnowGrid/
├── src/
│   └── apps/
│       └── ytvideo/
│           ├── models.py
│           ├── tasks.py
│           ├── transcipts_extract.py
│           └── RAG/
│               ├── chunking.py
│               └── generate_embedding.py
├── data/
│   └── videos/
└── README.md
```

*The structure above reflects the current components discussed during development; your actual repository may contain additional files.*

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL with pgvector installed
- Redis and Celery, when running background tasks

### 1. Clone the repository

```bash
git clone https://github.com/AnshuSAHA176/KnowGrid.git
cd KnowGrid
```

### 2. Create and activate a virtual environment

```bash
uv venv
source .venv/bin/activate
```

### 3. Install dependencies

Install the dependencies declared in the project's dependency configuration. For example, if using `uv` with `pyproject.toml`:

```bash
uv sync
```

### 4. Configure PostgreSQL

Create a PostgreSQL database and enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Make sure the extension is enabled in the same database used by Django.

Configure your database credentials through environment variables or your local Django settings. Do not commit production passwords or secret keys.

### 5. Apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Start the Django development server

```bash
python manage.py runserver
```

### 7. Start Celery

Configure your Celery broker URL first, then run the worker using your project's Celery application module:

```bash
celery -A <your_celery_app> worker --loglevel=info
```

Replace `<your_celery_app>` with the actual Celery application module in your project.

## Roadmap

- [ ] Reliable asynchronous video-processing pipeline
- [ ] Robust retry handling and idempotent chunk storage
- [ ] Semantic search across processed tutorials
- [ ] Retrieval-augmented generation (RAG) for video-grounded Q&A
- [ ] Timestamp citations in generated answers
- [ ] AI-generated coding challenges
- [ ] Automated evaluation of coding solutions
- [ ] Personalized learning progress

## Project Status

**Early development.** The current focus is the video-processing pipeline, transcript normalization, semantic chunking, and vector storage. The complete learning and question-answering experience is still under development.

## Contributing

KnowGrid is an evolving project. Suggestions, bug reports, and contributions are welcome.

