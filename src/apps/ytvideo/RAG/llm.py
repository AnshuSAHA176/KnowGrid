from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
load_dotenv()


def get_model(model="openai/gpt-oss-120b"):
    if model == "openai/gpt-oss-20b":
        return ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0,
            max_tokens=4096,
            reasoning_effort="low",
            max_retries=2,
        )

    return ChatGroq(
        model=model,
        temperature=0,
        max_retries=2,
    )