"""Evaluate tool for the evolution agent - runs the benchmark script and returns score.

The benchmark script is ALWAYS at a fixed location:
    <workspace_root>/optifiner_benchmark.py

Agents must write the benchmark script to this location. They should NEVER
run it directly using python or bash commands - only use this evaluate tool.

Required output format from the benchmark script:
{
    "score": <number>,           # Primary metric value (required, non-null)
    "metric_name": "<string>",   # Name of the metric, e.g. "FPS", "throughput" (required)
    "test_gate": <boolean>,      # Must be true for benchmark to pass (required)
    "metrics": {...},            # Optional additional metrics
    "message": "<string>"        # Optional human-readable message
}

The benchmark is considered successful when:
1. test_gate is true
2. score is not null

Once both conditions are met, the benchmark agent's job is complete and
the code becomes the base for evolution agents.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from worker.tools.path_utils import get_workspace_root, get_benchmark_script_path
from worker.workspace import BENCHMARK_SCRIPT_NAME

# Timeout for running benchmarks - 30 seconds
# This is intentionally short to prevent runaway benchmarks and keep iteration fast
BENCHMARK_TIMEOUT = 30

# Legacy timeout for backwards compatibility
DEFAULT_TIMEOUT = 120

# Global evaluator path override - if set, uses this instead of the standard benchmark path
_evaluator_path_override: str | None = None
_evaluator_timeout: int = BENCHMARK_TIMEOUT

# Flag to indicate benchmark development mode vs improver agent mode
# In benchmark dev mode: timeout tells agent to retry (they can fix the benchmark)
# In improver mode: timeout is a hard fail (benchmark should already work)
_is_benchmark_dev_mode: bool = False


def set_evaluator(path: str | None, timeout: int = BENCHMARK_TIMEOUT):
    """Set an evaluator path override.
    
    By default, the evaluate tool uses <workspace_root>/optifiner_benchmark.py.
    Call this function to override with a different evaluator script.
    
    Args:
        path: Path to the evaluator script, or None to use the default.
        timeout: Evaluation timeout in seconds (default: BENCHMARK_TIMEOUT = 30s).
    """
    global _evaluator_path_override, _evaluator_timeout
    _evaluator_path_override = path
    _evaluator_timeout = timeout


def set_benchmark_dev_mode(is_dev: bool):
    """Set whether we're in benchmark development mode.
    
    In benchmark dev mode (True): timeout tells agent to retry and fix the benchmark
    In improver mode (False): timeout is a hard fail
    
    Args:
        is_dev: True for benchmark builder agent, False for improver agents.
    """
    global _is_benchmark_dev_mode
    _is_benchmark_dev_mode = is_dev


def get_evaluator() -> str | None:
    """Get the current evaluator path override, if any."""
    return _evaluator_path_override


class EvaluateInput(BaseModel):
    """Input schema for the evaluate tool."""

    message: str = Field(
        default="",
        description="Optional message describing what changes were made before evaluation.",
    )


class BenchmarkResult(BaseModel):
    """Structured benchmark result."""
    
    score: float | None = None
    metric_name: str = "score"
    test_gate: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    error: str | None = None
    
    @property
    def is_valid(self) -> bool:
        """Check if the benchmark passed (test_gate=True, score not null, and score not 0)."""
        return self.test_gate and self.score is not None and self.score != 0


def _get_python_executable() -> str:
    """Get the Python executable to use for running scripts."""
    if sys.executable:
        return sys.executable
    if shutil.which("python3"):
        return "python3"
    if shutil.which("python"):
        return "python"
    return "python3"


def _parse_benchmark_output(output: str) -> BenchmarkResult:
    """Parse the benchmark script output into a structured result.
    
    Args:
        output: Raw stdout from the benchmark script.
        
    Returns:
        Parsed BenchmarkResult.
    """
    # Try to parse as JSON
    data = None
    try:
        data = json.loads(output.strip())
    except json.JSONDecodeError:
        # Try to find JSON object in output (skip any prefix garbage like pygame messages)
        json_start = output.find("{")
        if json_start >= 0:
            # Find the matching closing brace
            brace_count = 0
            json_end = json_start
            for i, c in enumerate(output[json_start:], json_start):
                if c == '{':
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            try:
                data = json.loads(output[json_start:json_end])
            except json.JSONDecodeError:
                pass
    
    if data is None:
        return BenchmarkResult(
            error=f"Could not parse benchmark output as JSON. The output was:\n{output[:500]}"
        )
    
    # 'score' is the only truly required field
    if "score" not in data:
        return BenchmarkResult(
            error="Benchmark output missing required 'score' field"
        )
    
    # For backwards compatibility, derive metric_name and test_gate if not present
    metric_name = data.get("metric_name")
    if not metric_name:
        # Try to infer from other fields
        if "fps" in data:
            metric_name = "FPS"
        elif "metrics" in data and "fps" in data.get("metrics", {}):
            metric_name = "FPS"
        else:
            metric_name = "score"
    
    # test_gate: if not present, derive from 'passed' field or assume True if score exists
    test_gate = data.get("test_gate")
    if test_gate is None:
        test_gate = data.get("passed", True)  # Legacy format used 'passed'
    
    return BenchmarkResult(
        score=data.get("score"),
        metric_name=metric_name,
        test_gate=bool(test_gate),
        metrics=data.get("metrics", {}),
        message=data.get("message", ""),
    )


def _format_result(result: BenchmarkResult) -> str:
    """Format a BenchmarkResult for display to the agent.
    
    Args:
        result: Parsed benchmark result.
        
    Returns:
        Formatted string for the agent.
    """
    if result.error:
        return (
            f"Benchmark Error: {result.error}\n\n"
            f"[BENCHMARK FAILED - error]\n"
            f"Please fix the benchmark script and try again."
        )
    
    parts = []
    
    # Always show "Score: X" for compatibility with score extraction
    if result.score is not None:
        parts.append(f"Score: {result.score}")
        # Also show metric name if different from generic "score"
        if result.metric_name and result.metric_name.lower() != "score":
            parts.append(f"Metric: {result.metric_name}")
    else:
        parts.append("Score: null (INVALID)")
    
    # Test gate status (show as Passed for backwards compat)
    if result.test_gate:
        parts.append("Passed: true")
    else:
        parts.append("Passed: false")
    
    # Additional metrics
    if result.metrics:
        metrics_str = ", ".join(f"{k}={v}" for k, v in result.metrics.items())
        parts.append(f"Metrics: {metrics_str}")
    
    # Optional message
    if result.message:
        parts.append(f"Message: {result.message}")
    
    # Validity summary
    if result.is_valid:
        parts.append("\n[BENCHMARK PASSED]")
    else:
        reasons = []
        if not result.test_gate:
            reasons.append("tests failed")
        if result.score is None:
            reasons.append("score is null")
        elif result.score == 0:
            reasons.append("score is 0 (invalid benchmark - please fix and retry)")
        parts.append(f"\n[BENCHMARK FAILED - {', '.join(reasons)}]")
    
    return "\n".join(parts)


def _get_evaluator_path() -> Path:
    """Get the evaluator path to use.
    
    Returns the override path if set, otherwise the standard benchmark path.
    """
    if _evaluator_path_override:
        return Path(_evaluator_path_override)
    return get_benchmark_script_path()


@tool(args_schema=EvaluateInput)
def evaluate(message: str = "") -> str:
    """Evaluate the codebase by running the benchmark script.

    The benchmark script is at: <workspace_root>/optifiner_benchmark.py
    (or a custom path if configured via set_evaluator)
    
    DO NOT run the benchmark script directly with python or bash commands.
    Always use this evaluate tool instead.

    The benchmark script must output JSON with this format:
    {
        "score": <number>,        # Primary metric value (required, non-null)
        "metric_name": "<string>", # Name like "FPS", "throughput" (required)
        "test_gate": <boolean>,   # Must be true for success (required)
        "metrics": {...},         # Optional additional metrics
        "message": "<string>"     # Optional message
    }

    The benchmark passes when test_gate=true AND score is not null.

    Args:
        message: Optional description of changes made before evaluation.

    Returns:
        Evaluation result with score, test_gate status, and metrics.
    """
    benchmark_path = _get_evaluator_path()
    workspace_root = get_workspace_root()
    
    if not benchmark_path.exists():
        return (
            f"Error: Benchmark script not found at {benchmark_path}\n\n"
            f"You must create the benchmark script at this exact location:\n"
            f"  {benchmark_path}\n\n"
            f"The script must output JSON with: score, metric_name, test_gate fields."
        )
    
    try:
        # Run the benchmark script with --quiet flag
        cmd = [_get_python_executable(), str(benchmark_path), "--quiet"]
        print(f"[evaluate] Running: {benchmark_path}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_evaluator_timeout,
            cwd=str(workspace_root),
            env={**os.environ, "WORKSPACE_ROOT": str(workspace_root)},
        )
        
        # Check for execution errors
        if result.returncode != 0:
            error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
            return (
                f"Benchmark execution failed (exit code {result.returncode}):\n"
                f"{error_output[:2000]}\n\n"
                f"[BENCHMARK FAILED - execution error]\n"
                f"Please fix the benchmark script and try again."
            )
        
        # Parse and format the output
        output = result.stdout.strip()
        parsed = _parse_benchmark_output(output)
        return _format_result(parsed)
        
    except subprocess.TimeoutExpired:
        if _is_benchmark_dev_mode:
            # In benchmark dev mode: agent can fix the benchmark
            return (
                f"Error: Benchmark timed out after {_evaluator_timeout} seconds.\n\n"
                f"[BENCHMARK FAILED - timeout]\n"
                f"The benchmark must complete within {BENCHMARK_TIMEOUT} seconds.\n"
                f"Please optimize the benchmark script to run faster and try again.\n"
                f"Tips:\n"
                f"- Reduce the number of frames/iterations being measured\n"
                f"- Use a shorter measurement window\n"
                f"- Ensure the benchmark exits cleanly after measurement"
            )
        else:
            # In improver mode: hard fail, benchmark should already work
            return (
                f"Error: Benchmark timed out after {_evaluator_timeout} seconds.\n\n"
                f"[BENCHMARK FAILED - timeout]\n"
                f"The benchmark exceeded the {BENCHMARK_TIMEOUT}s time limit.\n"
                f"This evaluation is considered a FAIL. Your changes may have caused "
                f"an infinite loop or severe performance regression."
            )
    except PermissionError:
        return (
            f"Error: Permission denied running benchmark: {benchmark_path}\n\n"
            f"[BENCHMARK FAILED - permission error]\n"
            f"Please fix the permissions and try again."
        )
    except Exception as e:
        return (
            f"Error running benchmark: {e}\n\n"
            f"[BENCHMARK FAILED - error]\n"
            f"Please fix the issue and try again."
        )


def run_benchmark_for_validation(workspace_root: Path) -> BenchmarkResult:
    """Run the benchmark and return structured result (for internal use).
    
    This is used by the benchmark builder to verify the benchmark works
    before handing off to evolution agents.
    
    Args:
        workspace_root: Path to the workspace root.
        
    Returns:
        Structured BenchmarkResult.
    """
    benchmark_path = workspace_root / BENCHMARK_SCRIPT_NAME
    
    if not benchmark_path.exists():
        return BenchmarkResult(error=f"Benchmark script not found at {benchmark_path}")
    
    try:
        cmd = [_get_python_executable(), str(benchmark_path), "--quiet"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=BENCHMARK_TIMEOUT,
            cwd=str(workspace_root),
            env={**os.environ, "WORKSPACE_ROOT": str(workspace_root)},
        )
        
        if result.returncode != 0:
            error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
            return BenchmarkResult(error=f"Execution failed: {error_output[:500]}")
        
        return _parse_benchmark_output(result.stdout.strip())
        
    except subprocess.TimeoutExpired:
        return BenchmarkResult(error=f"Timed out after {BENCHMARK_TIMEOUT} seconds. Benchmark must complete within {BENCHMARK_TIMEOUT}s.")
    except Exception as e:
        return BenchmarkResult(error=str(e))
