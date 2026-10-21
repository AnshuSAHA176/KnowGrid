import json
import subprocess
import tempfile
from pathlib import Path
import uuid

def run_submission(source_code: str, test_input: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="knowgrid-") as temp_dir:
        workspace = Path(temp_dir)

        submission_path = workspace / "submission.py"
        input_path = workspace / "input.json"
        submission_path.write_text(source_code)
        input_path.write_text(json.dumps(test_input))
        container_name = f"knowgrid-run-{uuid.uuid4().hex}"
        command = [
            "docker", "run",
            "--name", container_name,
            "--rm",
            "--network", "none",
            "--memory", "128m",
            "--memory-swap", "128m",
            "--cpus", "0.5",
            "--pids-limit", "32",
            "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true",
            "--user", "10001:10001",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
            "--mount",
            f"type=bind,src={submission_path},dst=/workspace/submission.py,readonly",
            "--mount",
            f"type=bind,src={input_path},dst=/workspace/input.json,readonly",
            "knowgrid-python-runner:latest",
        ]

        
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

        except subprocess.TimeoutExpired:
            subprocess.run(
                ["docker", "kill", container_name],
                capture_output=True,
                timeout=3,
                check=False,
            )

            return {
                "ok": False,
                "error": "Execution timed out",
            }

        finally:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                timeout=3,
                check=False,
            )

        if completed.returncode !=0:
            return {
                "ok":False,
                "error": completed.stderr[:4000] or "Execution failed",
            }
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            return  {
                "ok": False,
                "error": "Runner returned invalid JSON",
            }
