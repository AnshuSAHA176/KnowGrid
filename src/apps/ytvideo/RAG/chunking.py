import numpy as np
from .generate_embedding import generate_embedding


def chunking(sagments: list[dict]):
    sagments_embeddings = [generate_embedding(sagment["text"]) for sagment in sagments]
    sentence_embeddings = np.array(sagments_embeddings, dtype=np.float32)
    norms = np.linalg.norm(sagments_embeddings, axis=1, keepdims=True)
    sentence_embeddings = sentence_embeddings / np.maximum(norms, 1e-12)
    similarity = []
    for i in range(len(sagments) - 1):
        score = np.dot(sagments_embeddings[i], sagments_embeddings[i + 1])
        similarity.append(float(score))
    similarity = np.array(similarity, dtype=np.float32)
    threshold = np.percentile(similarity, 20)
    boundarys = []
    for i, similar in enumerate(similarity):
        if similar <= threshold:
            boundary.append(i + 1)
    chunks = []
    start = 0
    for boundary in boundarys:
        chunk_sentences = sagments[start:boundary]
        if not chunk_sentences:
            continue
        chunk_text = " ".join(sentacne["text"] for sentacne in chunk_sentences)
        chunks.append(
            {
                "text": chunk_text,
                "start": sagments[start]["start"],
                "end": sagments[boundary + 1]["start"],
                "duration": sum([sentance["duration"] for sentance in chunk_sentences]),
            }
        )
        start = boundary
    if start < len(sagments):
        chunk_sentences = sagments[start:]
        chunk_text = " ".join(sentence["text"] for sentence in chunk_sentences)
        chunks.append(
            {
                "text": chunk_text,
                "start": sagments[start]["start"],
                "end": sagments[boundary + 1]["start"],
                "duration": sum([sentance["duration"] for sentance in chunk_sentences]),
            }
        )
    return chunks
