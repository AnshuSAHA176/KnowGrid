
import numpy as np
from .generate_embedding import generate_embeddings


def chunking(sagments: list[dict]) -> list[dict]:
    if not sagments:
        return []

    if len(sagments) == 1:
        segment = sagments[0]
        return [{
            "text": segment["text"],
            "start": segment["start"],
            "end": segment.get(
                "end",
                segment["start"] + segment["duration"],
            ),
            "duration": segment["duration"],
        }]

    texts = [segment["text"] for segment in sagments]
    sagments_embeddings = generate_embeddings(texts)

    sentence_embeddings = np.array(
        sagments_embeddings,
        dtype=np.float32,
    )

    norms = np.linalg.norm(
        sentence_embeddings,
        axis=1,
        keepdims=True,
    )
    sentence_embeddings = sentence_embeddings / np.maximum(norms, 1e-12)

    similarity = []
    for i in range(len(sagments) - 1):
        score = np.dot(
            sentence_embeddings[i],
            sentence_embeddings[i + 1],
        )
        similarity.append(float(score))

    similarity = np.array(similarity, dtype=np.float32)
    threshold = np.percentile(similarity, 20)

    boundarys = []
    for i, similar in enumerate(similarity):
        if similar <= threshold:
            boundarys.append(i + 1)

    chunks = []
    start = 0

    for boundary in boundarys:
        chunk_sentences = sagments[start:boundary]
        if not chunk_sentences:
            continue

        chunk_text = " ".join(
            sentence["text"] for sentence in chunk_sentences
        )

        chunk_start = chunk_sentences[0]["start"]
        chunk_end = chunk_sentences[-1].get(
            "end",
            chunk_sentences[-1]["start"] + chunk_sentences[-1]["duration"],
        )

        chunks.append({
            "text": chunk_text,
            "start": chunk_start,
            "end": chunk_end,
            "duration": chunk_end - chunk_start,
        })

        start = boundary

    if start < len(sagments):
        chunk_sentences = sagments[start:]
        chunk_text = " ".join(
            sentence["text"] for sentence in chunk_sentences
        )

        chunk_start = chunk_sentences[0]["start"]
        chunk_end = chunk_sentences[-1].get(
            "end",
            chunk_sentences[-1]["start"] + chunk_sentences[-1]["duration"],
        )

        chunks.append({
            "text": chunk_text,
            "start": chunk_start,
            "end": chunk_end,
            "duration": chunk_end - chunk_start,
        })

    return chunks
