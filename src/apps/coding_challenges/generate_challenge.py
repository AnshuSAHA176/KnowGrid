
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class GeneratedTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_data: dict[str, Any]
    expected_output: Any
    is_hidden: bool = True


class GeneratedChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    difficulty: Literal["easy", "medium", "hard"]
    constraints: str
    starter_code: str
    reference_solution: str
    test_cases: list[GeneratedTestCase] = Field(min_length=1)


class GeneratedChallenges(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenges: list[GeneratedChallenge]



from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException

from apps.ytvideo.RAG.llm import get_model


def generate_challenges(
    concepts: list[str],
) -> list[GeneratedChallenge]:

    if not concepts:
        return []

    llm = get_model("openai/gpt-oss-20b")

    structured_llm = llm.with_structured_output(
        GeneratedChallenges,
        method="json_schema",
    )

    system_prompt = SystemMessage(
        content="""
You are KnowGrid's coding challenge generator.

Select only useful, practically testable programming concepts
from the supplied list.

For every challenge, return these fields separately:
- title
- description
- difficulty
- constraints
- starter_code
- reference_solution
- test_cases

Rules:
1. difficulty must be easy, medium, or hard.
2. description contains ONLY the problem statement and examples.
3. constraints contains ONLY the constraints.
4. starter_code contains executable Python function signatures
   with TODO/pass placeholders, never the reference solution.
5. reference_solution contains the complete Python implementation.
6. test_cases is a list of objects, each containing input_data,
   expected_output, and is_hidden.
7. input_data must be a JSON object containing the function arguments.
8. expected_output must match the reference solution.
9. Use deterministic problems and include normal and edge cases.
10. Do not put Markdown containing the entire challenge inside description.
11. Do not omit any required field.
12. Do not invent concepts beyond the supplied list.
13. Return an empty challenges list only if none of the concepts
    can reasonably produce a coding exercise.

Return only data matching the required schema.
"""
    )

    human_message = HumanMessage(
        content=(
            "Generate practical coding challenges for these concepts. "
            "Keep every field separate and populated:\n"
            f"{concepts}"
        )
    )

    try:
        result = structured_llm.invoke(
            [system_prompt, human_message]
        )
    except OutputParserException as exc:
        raise ValueError(
            "Groq returned challenge data that did not match "
            "the GeneratedChallenges schema."
        ) from exc

    return result.challenges
