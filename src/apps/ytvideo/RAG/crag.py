from apps.ytvideo.models import YtVideoChunks
from langgraph.graph import StateGraph, END, START, add_messages
from pydantic import BaseModel
from typing import Annotated
from pgvector.django import CosineDistance
from .generate_embedding import user_embedding_generator
from .llm import get_model

from langchain_core.messages import SystemMessage, HumanMessage
from typing import Literal


class State(BaseModel):
    user_query: str
    chunks: list
    youtube_id: str
    quality: str


class Correctivevalidator(BaseModel):
    quality: Literal["good", "retry"]


def retrive(state: State):
    user_embedding = user_embedding_generator(user_query=state.user_query)
    chunks = (
        YtVideoChunks.objects.filter(video=state.youtube_id)
        .annotate(distance=CosineDistance("embeddings", user_embedding))
        .order_by("distance")[:5]
    )
    return {"chunks": chunks}




def corrective(state: State) -> dict:
    model = get_model()
    structured_llm = model.with_structured_output(Correctivevalidator)

    result = structured_llm.invoke([
        SystemMessage(content="""
You are a retrieval quality evaluator in a Corrective RAG (CRAG) pipeline.

Your task is to evaluate whether the retrieved transcript chunks provide
sufficient, relevant evidence to answer the user's query.

Evaluation rules:
1. GOOD:
   - The chunks directly answer the query, or contain sufficient evidence
     to construct a reliable answer.
   - The evidence is relevant to the specific question.

2. RETRY:
   - The chunks are unrelated to the query.
   - The chunks are only loosely related or provide insufficient evidence.
   - The answer would require guessing or information not present in the chunks.

Important:
- Judge the evidence, not just keyword overlap.
- Do not use outside knowledge to fill gaps.
- If the evidence is ambiguous or insufficient, choose RETRY.
- Return only the structured output required by the schema.
"""),
        HumanMessage(content=f"""
User query:
{state.user_query}

Retrieved transcript chunks:
{state.chunks}
""")
    ])

    return {
        "quality": result.quality
    }