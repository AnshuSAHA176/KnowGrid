from celery import shared_task
from django.db import transaction

from apps.ytvideo.models import YtVideo
from .hierarchical_pipline import get_hierarchical_pipeline
from .generate_challenge import generate_challenges
from .models import CodingChallenge, TestCase


@transaction.atomic
def save_challenges(
    youtube_id: str,
    concepts: list[str],
):
    video = YtVideo.objects.get(youtube_id=youtube_id)

    challenges = generate_challenges(concepts=concepts)
    print(f"Generated challenges: {len(challenges)}")
    challenge_instances = [
        CodingChallenge(
            video=video,
            title=challenge.title,
            description=challenge.description,
            difficulty=challenge.difficulty,
            constraints=challenge.constraints,
            starter_code=challenge.starter_code,
            reference_solution=challenge.reference_solution,
        )
        for challenge in challenges
    ]

    saved_challenges = CodingChallenge.objects.bulk_create(
        challenge_instances
    )

    test_case_instances = [
        TestCase(
            challenge=challenge_instance,
            input_data=test_case.input_data,
            expected_output=test_case.expected_output,
            is_hidden=test_case.is_hidden,
        )
        for challenge_instance, generated_challenge in zip(
            saved_challenges, challenges
        )
        for test_case in generated_challenge.test_cases
    ]

    TestCase.objects.bulk_create(test_case_instances)

    return saved_challenges


@shared_task(bind=True, ignore_result=True)
def coding_challange_create(self, youtube_id: str):
    result = get_hierarchical_pipeline().invoke({
        "youtube_id": youtube_id,
        "chunks": [],
        "concepts": [],
    })

    concepts = result["concepts"]
    print(f"Extracted concepts: {concepts}")

    challenges = generate_challenges(concepts=concepts)
   

    return save_challenges(
        youtube_id=youtube_id,
        concepts=concepts,
    )