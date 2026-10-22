
import json
import os
from pathlib import Path


def main():
    workspace = Path("/workspace")

    submission_path = workspace / "submission.py"
    input_path = workspace / "input.json"

    source_code = submission_path.read_text()
    test_input = json.loads(input_path.read_text())

    namespace = {"__name__": "submission"}

    exec(compile(source_code, "submission.py", "exec"), namespace)

    function_name = os.environ.get("FUNCTION_NAME", "solution")
    solution = namespace.get(function_name)

    if not callable(solution):
        raise ValueError(
            f"Expected function {function_name!r} was not found"
        )

    if not isinstance(test_input, dict):
        raise ValueError("Test input must be a JSON object")

    result = solution(**test_input)

    print(json.dumps({"ok": True, "result": result}))


if __name__ == "__main__":
    main()
