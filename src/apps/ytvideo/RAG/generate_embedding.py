import os
import requests
from dotenv import load_dotenv
from hashlib import sha256
from django.core.cache import cache
import time
from django.utils import timezone
from datetime import timedelta
import uuid
from django_redis import get_redis_connection

redis_client = get_redis_connection("default")
load_dotenv()

CLOUDFLARE_ACCOUNT_ID = os.environ["CLOUDFLARE_ACCOUNT_ID"]
CLOUDFLARE_API_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]


def generate_hash(chunks: list[str], model=str) -> str:
    combined_chunks = " ".join(chunks)
    combined_data = f"{model} {combined_chunks}"
    return sha256(combined_data.encode("utf-8")).hexdigest()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    cache_key = generate_hash(chunks=texts, model="bge-m3")
    cache_data = cache.get(cache_key)

    if cache_data:
        return cache_data

    lock_key = f"{cache_key}:lock"
    owner = uuid.uuid4()
    get_permission = cache.add(lock_key, owner, timeout=60 * 2)
    try:
        if not get_permission:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                cache_data = cache.get(cache_key)
                if cache_data:
                    return cache_data
                if cache.add(lock_key, owner, timeout=60 * 3):
                    return call_embedding_cache(cache_key=cache_key,texts=texts)
                time.sleep(4)
            raise TimeoutError("Embedding generation timed out")
        return call_embedding_cache(cache_key=cache_key,texts=texts)
    finally:
        if cache.get(lock_key) == owner:
            cache.delete(lock_key)

def call_embedding_cache(cache_key, texts):
    cache_data = cache.get(key=cache_key)
    if cache_data:
        return cache_data

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/baai/bge-m3"
    )

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"text": texts},
        timeout=(10, 60),
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise RuntimeError(data)

    embeddings = data["result"]["data"]

    if len(embeddings) != len(texts):
        raise RuntimeError("Embedding count does not match input count")
    cache.set(key=cache_key, value=embeddings, timeout=60 * 30)
    return embeddings


def user_embedding_generator(user_query: str) -> list[float]:

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/baai/bge-m3"
    )

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "text": [user_query],
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise RuntimeError(data)

    return data["result"]["data"][0]
