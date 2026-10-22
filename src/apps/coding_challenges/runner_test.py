from celery import shared_task
from .models import Submission

from pathlib import Path
import sys

PROJECTROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECTROOT))

from runner.runner_manager import run_submission, get_function_name

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@shared_task(bind=True, ignore_result=True)
def execute_code(self, submission_id):
    submission = Submission.objects.get(id=submission_id)

    submission.status = Submission.StatusChoices.RUNNING
    submission.save(update_fields=["status"])

    try:
        function_name = get_function_name(submission.challenge.starter_code)

        test_cases = submission.challenge.testcases.all()
        total_tests = test_cases.count()
        passed_tests = 0

        for test_case in test_cases:
            result = run_submission(
                source_code=submission.source_code,
                test_input=test_case.input_data,
                function_name=function_name,
            )

            if not result.get("ok"):
                print("Runtime error:", result.get("error"))
                continue

            actual_output = result["result"]
            expected_output = test_case.expected_output

            if actual_output == expected_output:
                passed_tests += 1

        if total_tests > 0 and passed_tests == total_tests:
            submission.status = Submission.StatusChoices.ACCEPTED
        else:
            submission.status = Submission.StatusChoices.FAILED

        print(f"Passed {passed_tests}/{total_tests} test cases")

        submission.passed_tests = passed_tests
        submission.total_tests = total_tests
        submission.save(update_fields=["status", "passed_tests", "total_tests"])
        channel_layer = get_channel_layer()

        payload = {
            "submission_id": str(submission.id),
            "status": submission.status,
            "passed_tests": submission.passed_tests,
            "total_tests": submission.total_tests,
        }
        async_to_sync(channel_layer.group_send)(
            f"submission_{submission_id}",
            {
                "type": "send_event",
                "message": payload,
            },
        )
    except Exception as e:
        print("Submission execution failed:", e)
        submission.status = Submission.StatusChoices.FAILED
        submission.save(update_fields=["status"])
