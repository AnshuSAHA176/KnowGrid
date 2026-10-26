from concurrent.futures import ThreadPoolExecutor
import django

django.setup()

from apps.ytvideo.RAG.generate_embedding import generate_embeddings

texts = ["What is"] * 5

with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [
        executor.submit(generate_embeddings, texts)
        for _ in range(2)
    ]

    results = [future.result() for future in futures]

print("Both calls returned:", len(results))
print("Results match:", results[0] == results[1])