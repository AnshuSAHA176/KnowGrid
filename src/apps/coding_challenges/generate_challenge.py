from pydantic import BaseModel, Field


class GeneratedTestCase(BaseModel):
    input_data: dict = Field(
        description="Input arguments for a test case"
    )
    expected_output: str = Field(
        description="Expected output from the submitted solution"
    )
    is_hidden: bool = Field(default=True)


class GeneratedChallenge(BaseModel):
    title: str
    description: str
    difficulty: str = Field(
        description="One of: easy, medium, hard"
    )
    constraints: str
    supported_languages: list[str] = Field(
        description="Languages this challenge supports"
    )
    starter_code: dict[str, str] = Field(
        description="Starter code keyed by language, e.g. python or javascript"
    )
    reference_solution: dict[str, str] = Field(
        description="Reference solution keyed by language"
    )
    test_cases: list[GeneratedTestCase]

from langchain_core.messages import SystemMessage, HumanMessage
from apps.ytvideo.RAG.llm import get_model


SUPPORTED_LANGUAGES = ["python", "javascript", "java", "cpp"]


def generate_challenge(
    concept: str,
    context: list[str],
) -> GeneratedChallenge:
    llm = get_model("openai/gpt-oss-20b")
    structured_llm = llm.with_structured_output(GeneratedChallenge)

    system_message = SystemMessage(content=f"""
You are a programming challenge designer for KnowGrid.

Generate one high-quality coding challenge based on the supplied
programming concept and tutorial excerpts.

Rules:
1. Base the challenge on the supplied concept and context.
2. Write a clear, self-contained problem statement.
3. Define precise constraints, input format, and output format.
4. Choose an appropriate difficulty: easy, medium, or hard.
5. Generate starter code and a reference solution for each of these
   languages: {", ".join(SUPPORTED_LANGUAGES)}.
6. Ensure every language uses the same problem requirements and
   equivalent function signatures or input/output contracts.
7. Use valid, idiomatic syntax for each language.
8. Generate test cases covering normal cases, edge cases, and
   boundary conditions.
9. Ensure expected outputs are consistent across languages.
10. Do not invent concepts unsupported by the supplied material.
11. Never put reference solutions in starter code.
12. Return structured data matching the requested schema.
""")

    human_message = HumanMessage(content=f"""
Concept:
{concept}

Supporting tutorial excerpts:
{chr(10).join(context)}

Generate one language-independent coding challenge.
""")

    return structured_llm.invoke([
        system_message,
        human_message,
    ])