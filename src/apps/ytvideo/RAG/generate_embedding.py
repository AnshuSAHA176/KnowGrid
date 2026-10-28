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


def splitchunks(chunks: list[str]) -> list:

    result = []

    for boundary in range(0, len(chunks), 40):
        result.append(chunks[boundary : boundary + 40])
    
    return result




def release_lock(lock_key: str, owner: str) -> bool:
    RELEASE_LOCK_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
"""
    return (
        redis_client.eval(
            RELEASE_LOCK_SCRIPT,
            1,
            lock_key,
            owner,
        )
        == 1
    )


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

    if cache_data is not None:
        return cache_data

    lock_key = f"{cache_key}:lock"
    owner = str(uuid.uuid4())
    get_permission = redis_client.set(lock_key, owner, nx=True, ex=120)
    try:
        if not get_permission:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                cache_data = cache.get(cache_key)
                if cache_data is not None:
                    return cache_data
                if redis_client.set(lock_key, owner, nx=True, ex=180):
                    get_permission = True
                    return call_embedding_cache(cache_key=cache_key, texts=texts)
                time.sleep(4)
            raise TimeoutError("Embedding generation timed out")
        return call_embedding_cache(cache_key=cache_key, texts=texts)
    finally:
        if get_permission:
            release_lock(lock_key=lock_key, owner=owner)


def call_embedding_cache(cache_key, texts):
    print("CLOUDFLARE API CALLED")
    cache_data = cache.get(cache_key)
    if cache_data is not None:
        return cache_data

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/baai/bge-m3"
    )
    if os.getenv("TEST_EMBEDDING_FAILURE") == "1":
            raise requests.ConnectionError("TEST: Cloudflare unavailable")
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
