"""Evaluate tool for the evolution agent - runs benchmark evaluator and returns score."""

import json
import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

WORKSPACE_ROOT = Path("/app")
DEFAULT_TIMEOUT = 120

# Global evaluator path - set by CLI
_evaluator_path: str | None = None
_evaluator_timeout: int = DEFAULT_TIMEOUT


def set_evaluator(path: str, timeout: int = DEFAULT_TIMEOUT):
    """Set the evaluator script path globally."""
    global _evaluator_path, _evaluator_timeout
    _evaluator_path = path
    _evaluator_timeout = timeout


def get_evaluator() -> str | None:
    """Get the current evaluator path."""
    return _evaluator_path


class EvaluateInput(BaseModel):
    """Input schema for the evaluate tool."""

    message: str = Field(
        default="",
        description="Optional message describing what changes were made before evaluation.",
    )


def _resolve_path(file_path: str | None) -> Path:
    """Resolve the file path, defaulting to workspace root."""
    if file_path is None:
        return WORKSPACE_ROOT
    path = Path(file_path)
    if not path.is_absolute():
        path = WORKSPACE_ROOT / path
    return path


@tool(args_schema=EvaluateInput)
def evaluate(message: str = "") -> str:
    """Evaluate the current codebase and return a score.

    Runs the configured evaluator script on the codebase. The evaluator should
    output a JSON object with at least a "score" field.

    Expected evaluator output format:
    {
        "score": 60.5,
        "metrics": {"fps": 60.5, "memory_mb": 128},
        "passed": true,
        "message": "All tests passed"
    }

    Args:
        message: Optional description of changes made before evaluation.

    Returns:
        Evaluation result with score, or error message.
    """
    global _evaluator_path, _evaluator_timeout

    if _evaluator_path is None:
        return "Error: No evaluator configured. The evaluator script must be set by the CLI."

    evaluator = Path(_evaluator_path)
    if not evaluator.exists():
        return f"Error: Evaluator script not found: {evaluator}"

    workspace = os.environ.get("WORKSPACE_ROOT", str(WORKSPACE_ROOT))

    try:
        # Determine how to run the evaluator based on extension
        if evaluator.suffix == ".py":
            cmd = ["python", str(evaluator)]
        elif evaluator.suffix == ".sh":
            cmd = ["bash", str(evaluator)]
        elif evaluator.suffix in (".js", ".mjs"):
            cmd = ["node", str(evaluator)]
        else:
            # Try to run as executable
            cmd = [str(evaluator)]

        # Run the evaluator
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_evaluator_timeout,
            cwd=workspace,
            env={**os.environ, "WORKSPACE_ROOT": workspace},
        )

        # Check for errors
        if result.returncode != 0:
            error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
            return f"Evaluation failed (exit code {result.returncode}):\n{error_output}"

        # Parse output
        output = result.stdout.strip()

        # Try to parse as JSON
        try:
            data = json.loads(output)
            score = data.get("score")

            if score is None:
                return f"Error: Evaluator output missing 'score' field. Output:\n{output}"

            # Build result message
            result_parts = [f"Score: {score}"]

            if "metrics" in data:
                metrics_str = ", ".join(f"{k}={v}" for k, v in data["metrics"].items())
                result_parts.append(f"Metrics: {metrics_str}")

            if "message" in data:
                result_parts.append(f"Message: {data['message']}")

            if "passed" in data:
                result_parts.append(f"Passed: {data['passed']}")

            return "\n".join(result_parts)

        except json.JSONDecodeError:
            # If not JSON, try to extract a number from the output
            import re

            numbers = re.findall(r"[-+]?\d*\.?\d+", output)
            if numbers:
                score = float(numbers[0])
                return f"Score: {score}\nRaw output: {output}"
            else:
                return f"Error: Could not parse evaluator output as score:\n{output}"

    except subprocess.TimeoutExpired:
        return f"Error: Evaluation timed out after {_evaluator_timeout} seconds."
    except PermissionError:
        return f"Error: Permission denied running evaluator: {evaluator}"
    except Exception as e:
        return f"Error running evaluator: {e}"
