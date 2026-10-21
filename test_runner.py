from runner.runner_manager import run_submission

result = run_submission(
    source_code="""
def solution(name):
    while True:
        pass
""",
    test_input={"name": "Alice"},
)

print(result)