from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel,Field
from apps.ytvideo.models import YtVideoChunks
from apps.ytvideo.RAG.llm import get_model



class ConceptsValidator(BaseModel):
    Concept:str fi
class State(BaseModel):
    youtube_id: str
    chunks: list
    Concepts : list

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

def get_topics(state:State) -> dict:
    llm = get_model("openai/gpt-oss-20b")
