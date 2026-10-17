import os
import requests
from dotenv import load_dotenv
load_dotenv()

CLOUDFLARE_ACCOUNT_ID = os.environ["CLOUDFLARE_ACCOUNT_ID"]
CLOUDFLARE_API_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

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

    return embeddings
