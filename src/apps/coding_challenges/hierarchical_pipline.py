
from typing import Any

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from apps.ytvideo.models import YtVideoChunks
from apps.ytvideo.RAG.llm import get_model


class ConceptsValidator(BaseModel):
    concept: str = Field(
        description=(
            "One distinct, technically meaningful concept supported by the "
            "transcript. Return an empty string if no relevant concept exists."
        )
    )


class MergedConcepts(BaseModel):
    concepts: list[str] = Field(
        description=(
            "A deduplicated list of distinct, technically meaningful "
            "programming concepts extracted from the video."
        )
    )


class State(BaseModel):
    youtube_id: str
    chunks: list[str] = Field(default_factory=list)
    concepts: list[Any] = Field(default_factory=list)


def load_transcript_chunks(state: State) -> dict:
    chunks = list(
        YtVideoChunks.objects.filter(
            video__youtube_id=state.youtube_id
        )
        .order_by("start_time")
        .values_list("text", flat=True)
    )

    return {"chunks": chunks}


def merge_small_chunks(state: State) -> dict:
    merged_chunks = []
    i = 0

    while i < len(state.chunks):
        chunk = state.chunks[i]

        while len(chunk) < 300 and i + 1 < len(state.chunks):
            i += 1
            chunk = " ".join([chunk, state.chunks[i]])

        merged_chunks.append(chunk)
        i += 1

    return {"chunks": merged_chunks}


def get_topics(state: State) -> dict:
    if not state.chunks:
        return {"concepts": []}

    llm = get_model("openai/gpt-oss-20b")
    structured_llm = llm.with_structured_output(ConceptsValidator)

    system_message = SystemMessage(
        content="""
You are a technical concept extraction assistant for KnowGrid.

Identify the single most important programming concept in each
transcript chunk.

Rules:
1. Extract only concepts explicitly supported by the transcript.
2. Focus on specific technical concepts, APIs, functions, algorithms,
   programming techniques, and problem-solving methods.
3. Prefer precise concepts over broad topics.
4. Return exactly one concept per response.
5. Do not invent technical details.
6. Ignore greetings, advertisements, repetition, and filler.
7. If multiple concepts appear, choose the most important one.
8. If no meaningful technical concept exists, set the concept field
   to an empty string. Do not return an explanation or plain text.
9. Make the concept self-contained and concise.
10. Do not generate challenges, solutions, or test cases.

Always return the required structured output.
"""
    )

    concepts = []

    for chunk in state.chunks:
        result = structured_llm.invoke(
            [
                system_message,
                HumanMessage(
                    content=(
                        "Extract the most important technical concept "
                        "from this transcript chunk:\n\n"
                        f"{chunk}"
                    )
                ),
            ]
        )

        concept = result.concept.strip()

        if concept:
            concepts.append(ConceptsValidator(concept=concept))

    return {"concepts": concepts}


def merge_concepts(state: State) -> dict:
    # Normalize and remove empty concepts before calling the LLM.
    unique_input = list(
        dict.fromkeys(
            item.concept.strip()
            if isinstance(item, ConceptsValidator)
            else str(item).strip()
            for item in state.concepts
            if (
                item.concept.strip()
                if isinstance(item, ConceptsValidator)
                else str(item).strip()
            )
        )
    )

    if not unique_input:
        return {"concepts": []}

    llm = get_model("openai/gpt-oss-20b")
    structured_llm = llm.with_structured_output(MergedConcepts)

    system_message = SystemMessage(
        content="""
You are a technical concept consolidation assistant for KnowGrid.

Consolidate the supplied programming concepts.

Rules:
1. Merge concepts that describe the same underlying technical idea.
2. Remove exact and semantic duplicates.
3. Preserve distinct concepts even when they are related.
4. Keep each concept concise, precise, and technically meaningful.
5. Preserve the original technical meaning.
6. Never invent unsupported concepts.
7. Return a flat list of unique concept strings.
8. Do not generate challenges, explanations, solutions, or test cases.
9. Preserve useful technical names, APIs, and function names.
10. If the input contains no valid concepts, return an empty list.

Always return the required structured output.
"""
    )

    human_message = HumanMessage(
        content=f"Consolidate these extracted concepts:\n{unique_input}"
    )

    result = structured_llm.invoke([system_message, human_message])

    # Clean the output in case the model returns blank or duplicate entries.
    cleaned_concepts = list(
        dict.fromkeys(
            concept.strip()
            for concept in result.concepts
            if isinstance(concept, str) and concept.strip()
        )
    )

    return {"concepts": cleaned_concepts}


def get_hierarchical_pipeline():
    builder = StateGraph(State)

    builder.add_node("load_chunks", load_transcript_chunks)
    builder.add_node("merge_small_chunks", merge_small_chunks)
    builder.add_node("get_topics", get_topics)
    builder.add_node("merge_concepts", merge_concepts)

    builder.add_edge(START, "load_chunks")
    builder.add_edge("load_chunks", "merge_small_chunks")
    builder.add_edge("merge_small_chunks", "get_topics")
    builder.add_edge("get_topics", "merge_concepts")
    builder.add_edge("merge_concepts", END)

    return builder.compile()
