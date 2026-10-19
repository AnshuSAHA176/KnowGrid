from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from apps.ytvideo.models import YtVideoChunks
from apps.ytvideo.RAG.llm import get_model


class ConceptsValidator(BaseModel):
    concept: str = Field(
        description="One distinct, technically meaningful concept supported by the transcript."
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
