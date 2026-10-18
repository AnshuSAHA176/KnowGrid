from typing import Literal

from pydantic import BaseModel, Field
from django.db import close_old_connections
from pgvector.django import CosineDistance

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage

from apps.ytvideo.models import YtVideoChunks
from .generate_embedding import user_embedding_generator
from .llm import get_model

MAX_RETRIES = 2


class State(BaseModel):
    user_query: str
    youtube_id: str

    search_query: str = ""
    chunks: list[dict] = Field(default_factory=list)
    quality: Literal["good", "retry"] = "retry"
    answer: str = ""
    retry_count: int = 0


class Correctivevalidator(BaseModel):
    quality: Literal["good", "retry"]


class RetryQuery(BaseModel):
    rewritten_query: str = Field(description="An improved semantic search query.")


class GeneratedAnswer(BaseModel):
    answer: str = Field(
        description="An answer grounded in transcript chunks with timestamps."
    )


def retrive(state: State) -> dict:
    close_old_connections()

    query = state.search_query or state.user_query

    user_embedding = user_embedding_generator(user_query=query)

    chunks = list(
        YtVideoChunks.objects.filter(video_id=state.youtube_id)
        .annotate(distance=CosineDistance("embeddings", user_embedding))
        .order_by("distance")[:5]
        .values(
            "text",
            "start_time",
            "end_time",
            "distance",
        )
    )

    return {"chunks": chunks}


def corrective(state: State) -> dict:
    if not state.chunks:
        return {"quality": "retry"}

    model = get_model()
    structured_llm = model.with_structured_output(Correctivevalidator)

    result = structured_llm.invoke(
        [
            SystemMessage(content="""
You are the retrieval evaluator for KnowGrid's CRAG pipeline.

Determine whether the retrieved YouTube transcript chunks contain
sufficient evidence to answer the original user question.

Return "good" when:
- The chunks directly answer the question, or provide enough evidence
  to construct a reliable answer.
- The evidence is relevant to the user's actual information need.

Return "retry" when:
- The chunks are unrelated or only loosely related.
- Important information needed to answer is missing.
- Answering would require unsupported assumptions.

Evaluate semantic meaning, not just keyword overlap.
Do not use outside knowledge to fill gaps.
The timestamps identify where the passages occur; they do not
establish whether the content is relevant.

Return only the required structured output.
"""),
            HumanMessage(content=f"""
Original user question:
{state.user_query}

Retrieved transcript chunks:
{state.chunks}
"""),
        ]
    )

    return {"quality": result.quality}


def retry(state: State) -> dict:
    model = get_model()
    structured_llm = model.with_structured_output(RetryQuery)

    result = structured_llm.invoke(
        [
            SystemMessage(content="""
You rewrite search queries for KnowGrid's CRAG pipeline.

The previous retrieval did not provide sufficient evidence.

Your task:
1. Preserve the original user's intent.
2. Examine the retrieved transcript chunks and identify the retrieval gap.
3. Use relevant terminology and concepts from the transcript where useful.
4. Create a concise query that is likely to retrieve better evidence.
5. Do not answer the question.
6. Do not invent facts or timestamps.
7. Do not merely repeat the original query unchanged.
8. Return one standalone semantic search query.
"""),
            HumanMessage(content=f"""
Original user question:
{state.user_query}

Previous search query:
{state.search_query or state.user_query}

Retrieved transcript chunks:
{state.chunks}

Rewrite the search query to improve the next retrieval attempt.
"""),
        ]
    )

    return {
        "search_query": result.rewritten_query,
        "retry_count": state.retry_count + 1,
        "quality": "retry",
    }


def generation(state: State) -> dict:
    model = get_model()
    structured_llm = model.with_structured_output(GeneratedAnswer)

    result = structured_llm.invoke(
        [
            SystemMessage(content="""
You are KnowGrid, an educational assistant that answers questions
using retrieved YouTube transcript passages.

Rules:
1. Answer the original user question, not the rewritten search query.
2. Use only the evidence in the provided transcript chunks.
3. Explain concepts clearly and directly.
4. Do not invent facts, examples, or details.
5. Cite supporting passages using their supplied start_time and end_time.
6. Timestamps are in seconds. Convert them to [MM:SS–MM:SS].
7. Put citations next to the claims they support.
8. Never invent or alter timestamps.
9. If the evidence is insufficient, clearly say that the available
   transcript excerpts do not provide enough information.
10. Avoid unnecessary repetition.
"""),
            HumanMessage(content=f"""
Original user question:
{state.user_query}

Accepted transcript chunks:
{state.chunks}

Each chunk contains text, start_time, end_time, and distance.
Use start_time and end_time for citations. Do not cite distance.

Generate the final answer.
"""),
        ]
    )

    return {"answer": result.answer}


def insufficient_evidence(state: State) -> dict:
    return {
        "answer": (
            "I couldn't find enough relevant evidence in this video's "
            "transcript to answer your question reliably. Try rephrasing "
            "your question or asking about a more specific concept."
        )
    }


def route_after_grading(
    state: State,
) -> Literal["generation", "retry", "insufficient_evidence"]:

    if state.quality == "good":
        return "generation"

    if state.retry_count < MAX_RETRIES:
        return "retry"

    return "insufficient_evidence"


def crag():
    graph = StateGraph(State)

    graph.add_node("retrive", retrive)
    graph.add_node("corrective", corrective)
    graph.add_node("retry", retry)
    graph.add_node("generation", generation)
    graph.add_node("insufficient_evidence", insufficient_evidence)

    graph.add_edge(START, "retrive")
    graph.add_edge("retrive", "corrective")

    graph.add_conditional_edges(
        "corrective",
        route_after_grading,
        {
            "generation": "generation",
            "retry": "retry",
            "insufficient_evidence": "insufficient_evidence",
        },
    )

    # Re-run retrieval using the rewritten query.
    graph.add_edge("retry", "retrive")

    graph.add_edge("generation", END)
    graph.add_edge("insufficient_evidence", END)

    return graph.compile()
