from celery import shared_task
from .models import Submission
from runner.runner_manager import run_submission


@shared_task(bind=True,ignore_result=True)
def execute_code(self,submission_id):
    submission = Submission.objects.get(id=submission_id)
    submission.status = Submission.StatusChoices.RUNNING
    submission.save(update_fields=['status'])
    test_cases = submission.challenge.testcases.all()

    for test_case in test_cases:
        result = run_submission(
            source_code=submission.source_code,
            test_input=test_case.input_data,
        )
        print(result)