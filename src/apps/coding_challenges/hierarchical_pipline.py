from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from apps.ytvideo.models import YtVideoChunks
from apps.ytvideo.RAG.llm import get_model


class ConceptsValidator(BaseModel):
    concept: str = Field(
        description="One distinct, technically meaningful concept supported by the transcript."
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
    chunks: list
    concepts: list


def load_transcript_chunks(state: State) -> dict:
    chunks = YtVideoChunks.objects.filter(
        video__youtube_id=state.youtube_id
    ).values_list("text", flat=True)
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


from langchain_core.messages import SystemMessage, HumanMessage


def get_topics(state: State) -> dict:
    llm = get_model("openai/gpt-oss-20b")
    structure_llm = llm.with_structured_output(ConceptsValidator)

    system_message = SystemMessage(content="""
You are a technical concept extraction assistant for KnowGrid,
a platform that turns programming tutorials into practical coding challenges.

Your task is to identify the most important programming concepts
explained in the provided transcript chunk.

Rules:
1. Extract only concepts supported by the provided text.
2. Focus on specific technical concepts, programming techniques,
   APIs, functions, algorithms, and problem-solving methods.
3. Prefer precise concepts over broad topics.
4. Each output must describe exactly one distinct concept.
5. Do not invent concepts, examples, or technical details.
6. Ignore greetings, advertisements, unrelated conversation,
   repetition, and filler.
7. If the chunk contains multiple meaningful concepts, identify
   the most important one for this extraction step.
8. If the chunk contains no meaningful technical concept,
   return a concise indication that no relevant concept was found.
9. Use clear, self-contained wording so concepts from different
   chunks can be merged and deduplicated later.
10. Do not generate coding challenges, solutions, or test cases.
    This step is only for concept extraction.
""")

    concepts = []

    for chunk in state.chunks:
        result = structure_llm.invoke(
            [
                system_message,
                HumanMessage(
                    content=f"Extract the technical concept from this transcript chunk:\n\n{chunk}"
                ),
            ]
        )
        concepts.append(result)

    return {"concepts": concepts}


from langchain_core.messages import SystemMessage, HumanMessage
from apps.ytvideo.RAG.llm import get_model


def merge_concepts(state: State) -> dict:
    if not state.concepts:
        return {"concepts": []}

    llm = get_model("openai/gpt-oss-20b")
    structured_llm = llm.with_structured_output(MergedConcepts)

    # Convert Pydantic objects into plain strings.
    concepts = [
        item.concept if isinstance(item, ConceptsValidator)
        else str(item)
        for item in state.concepts
    ]

    system_message = SystemMessage(content="""
You are a technical concept consolidation assistant for KnowGrid.

Your task is to consolidate programming concepts extracted from
different chunks of a YouTube tutorial.

Rules:
1. Merge concepts that describe the same underlying technical idea.
2. Remove exact and semantic duplicates.
3. Preserve distinct concepts, even when they are related.
4. Keep each concept concise, precise, and technically meaningful.
5. Preserve the original technical meaning; do not invent concepts.
6. Do not add information that is unsupported by the input.
7. Return a flat list of unique concepts.
8. Do not generate coding challenges, explanations, solutions,
   or test cases.
9. Preserve useful technical names, APIs, and function names.
""")

    human_message = HumanMessage(
        content=f"Consolidate these extracted concepts:\n{concepts}"
    )

    result = structured_llm.invoke([system_message, human_message])

    return {"concepts": result.concepts}

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
