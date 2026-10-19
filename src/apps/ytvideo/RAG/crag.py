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

    chat_history: list[dict] = Field(default_factory=list)
    search_query: str = ""
    chunks: list[dict] = Field(default_factory=list)
    quality: Literal["good", "retry"] = "retry"
    answer: str = ""
    retry_count: int = 0



class ContextualizedQuery(BaseModel):
    search_query: str = Field(
        description="A standalone search query that preserves the user's intent."
    )


class Correctivevalidator(BaseModel):
    quality: Literal["good", "retry"]


class RetryQuery(BaseModel):
    rewritten_query: str = Field(
        description="An improved semantic search query."
    )


class GeneratedAnswer(BaseModel):
    answer: str = Field(
        description="An answer grounded in transcript chunks with timestamps."
    )



def resolve_context(state: State) -> dict:
    # A new question doesn't need conversation context.
    if not state.chat_history:
        return {"search_query": state.user_query}

    model = get_model()
    structured_llm = model.with_structured_output(ContextualizedQuery)

    result = structured_llm.invoke([
        SystemMessage(content="""
You are KnowGrid's conversation context resolver.

Your task is to turn the user's latest question into a standalone
search query suitable for semantic retrieval over a YouTube transcript.

Rules:
1. Use conversation history only to understand references, omitted
   subjects, and follow-up questions.
2. Preserve the latest question's original intent.
3. Resolve references such as "it", "that", "why", and "what about it"
   using previous messages when the reference is clear.
4. Focus on the latest user question. Do not answer it.
5. Do not treat previous assistant answers as verified transcript evidence.
6. Do not add unsupported facts or introduce a different question.
7. If the latest question is already standalone, keep its meaning
   and wording as close to the original as possible.
8. Return one concise, standalone search query.
"""),
        HumanMessage(content=f"""
Recent conversation history:
{state.chat_history}

Latest user question:
{state.user_query}

Rewrite the latest question into a standalone search query.
"""),
    ])

    return {"search_query": result.search_query.strip()}




def retrive(state: State) -> dict:
    close_old_connections()

    query = state.search_query or state.user_query

    user_embedding = user_embedding_generator(user_query=query)

    chunks = list(
        YtVideoChunks.objects
        .filter(video_id=state.youtube_id)
        .annotate(
            distance=CosineDistance("embeddings", user_embedding)
        )
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

    result = structured_llm.invoke([
        SystemMessage(content="""
You evaluate the quality of retrieved transcript chunks in KnowGrid.

Determine whether the chunks contain sufficient evidence to answer
the user's latest question in its conversation context.

Return "good" when the chunks provide relevant, sufficient evidence.
Return "retry" when the chunks are unrelated, incomplete, or insufficient.

Evaluate the actual content, not just keyword overlap.
Do not use outside knowledge to fill gaps.
Conversation history may clarify the user's intent, but it is not
evidence that a claim appears in the transcript.

Return only the required structured output.
"""),
        HumanMessage(content=f"""
Recent conversation history:
{state.chat_history}

Original user question:
{state.user_query}

Standalone search query:
{state.search_query or state.user_query}

Retrieved transcript chunks:
{state.chunks}
"""),
    ])

    return {"quality": result.quality}




def retry(state: State) -> dict:
    model = get_model()

    # Plain text output avoids depending on Groq tool calling here.
    result = model.invoke([
        SystemMessage(content="""
You rewrite search queries for KnowGrid's CRAG pipeline.

The previous retrieval did not provide sufficient evidence.

Rules:
1. Preserve the user's original intent.
2. Use conversation history to understand the question.
3. Use relevant terminology from retrieved chunks when helpful.
4. Correct the search query to improve semantic retrieval.
5. Do not answer the question.
6. Do not invent facts or timestamps.
7. Return only one concise standalone search query.
"""),
        HumanMessage(content=f"""
Recent conversation history:
{state.chat_history}

Original user question:
{state.user_query}

Previous search query:
{state.search_query or state.user_query}

Retrieved transcript chunks:
{state.chunks}

Write an improved search query.
"""),
    ])

    rewritten_query = result.content.strip()

    # Avoid accidentally retrying with an empty query.
    if not rewritten_query:
        rewritten_query = state.search_query or state.user_query

    return {
        "search_query": rewritten_query,
        "retry_count": state.retry_count + 1,
        "quality": "retry",
    }




def generation(state: State) -> dict:
    model = get_model()
    structured_llm = model.with_structured_output(GeneratedAnswer)

    result = structured_llm.invoke([
        SystemMessage(content="""
You are KnowGrid, an educational assistant that answers questions
using retrieved YouTube transcript passages.

Rules:
1. Answer the latest user question in its conversation context.
2. Use conversation history to understand follow-up questions.
3. Use only the retrieved transcript chunks as factual evidence.
4. Do not treat previous assistant answers as evidence.
5. Explain concepts clearly and directly.
6. Do not invent facts, examples, or details.
7. Cite supporting passages using their supplied start_time and end_time.
8. Timestamps are in seconds. Format them as [MM:SS–MM:SS].
9. Place citations beside the claims they support.
10. Never invent or alter timestamps.
11. If the chunks do not support an answer, clearly state that
    the available transcript excerpts do not provide enough information.
12. Avoid unnecessary repetition.
"""),
        HumanMessage(content=f"""
Recent conversation history:
{state.chat_history}

Latest user question:
{state.user_query}

Search query used:
{state.search_query or state.user_query}

Retrieved transcript chunks:
{state.chunks}

Use the chunks to answer the latest question. Cite their timestamps.
"""),
    ])

    return {"answer": result.answer}


# -------------------------
# 6. Insufficient evidence
# -------------------------

def insufficient_evidence(state: State) -> dict:
    return {
        "answer": (
            "I couldn't find enough relevant evidence in this video's "
            "transcript to answer your question reliably. Try rephrasing "
            "your question or asking about a more specific concept."
        )
    }


# -------------------------
# 7. Conditional routing
# -------------------------

def route_after_grading(
    state: State,
) -> Literal["generation", "retry", "insufficient_evidence"]:

    if state.quality == "good":
        return "generation"
    print(f"ATTEMTED :- {state.retry_count}")
    if state.retry_count < MAX_RETRIES:
        return "retry"

    return "insufficient_evidence"


# -------------------------
# 8. Build graph
# -------------------------

def crag():
    graph = StateGraph(State)

    graph.add_node("resolve_context", resolve_context)
    graph.add_node("retrive", retrive)
    graph.add_node("corrective", corrective)
    graph.add_node("retry", retry)
    graph.add_node("generation", generation)
    graph.add_node("insufficient_evidence", insufficient_evidence)

    graph.add_edge(START, "resolve_context")
    graph.add_edge("resolve_context", "retrive")
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

    graph.add_edge("retry", "retrive")
    graph.add_edge("generation", END)
    graph.add_edge("insufficient_evidence", END)

    return graph.compile()