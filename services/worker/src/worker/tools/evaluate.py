"""Evaluate tool for the evolution agent - runs the benchmark script and returns score.

The benchmark script is ALWAYS at a fixed location:
    <workspace_root>/optifiner_benchmark.py

Agents must write the benchmark script to this location. They should NEVER
run it directly using python or bash commands - only use this evaluate tool.

Required output format from the benchmark script:
{
    "score": <number>,           # Primary metric value (required, non-null)
    "metric_name": "<string>",   # Name of the metric, e.g. "FPS", "throughput", "cycles" (required)
    "test_gate": <boolean>,      # Must be true for benchmark to pass (required)
    "higher_is_better": <bool>,  # REQUIRED: True if higher scores are better (FPS), False if lower is better (cycles)
    "metrics": {...},            # Optional additional metrics
    "message": "<string>"        # Optional human-readable message
}

The benchmark is considered successful when:
1. test_gate is true
2. score is not null

Metric Direction (MUST be explicitly set by benchmark script):
- higher_is_better=true: Higher scores are better (FPS, throughput, ops/sec)
- higher_is_better=false: Lower scores are better (cycles, latency, execution time)

IMPORTANT: The benchmark script MUST explicitly set higher_is_better.
Do NOT rely on auto-detection - always specify it explicitly in your benchmark output.

Once both conditions are met, the benchmark agent's job is complete and
the code becomes the base for evolution agents.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from worker.workspace import BENCHMARK_SCRIPT_NAME, get_workspace, get_workspace_root

# Timeout for running benchmarks - 30 seconds
# This is intentionally short to prevent runaway benchmarks and keep iteration fast
BENCHMARK_TIMEOUT = 30

# Thread-local evaluator settings
# Using threading.local() ensures each thread (agent) has its own evaluator config
# This prevents race conditions when running multiple agents in parallel
_thread_local = threading.local()


def set_evaluator(path: str | None, timeout: int = BENCHMARK_TIMEOUT):
    """Set an evaluator path override for the current thread.
    
    By default, the evaluate tool uses <workspace_root>/optifiner_benchmark.py.
    Call this function to override with a different evaluator script.
    
    Args:
        path: Path to the evaluator script, or None to use the default.
        timeout: Evaluation timeout in seconds (default: BENCHMARK_TIMEOUT = 30s).
    """
    _thread_local.evaluator_path_override = path
    _thread_local.evaluator_timeout = timeout


def set_benchmark_dev_mode(is_dev: bool):
    """Set whether we're in benchmark development mode for the current thread.
    
    In benchmark dev mode (True): timeout tells agent to retry and fix the benchmark
    In improver mode (False): timeout is a hard fail
    
    Args:
        is_dev: True for benchmark builder agent, False for improver agents.
    """
    _thread_local.is_benchmark_dev_mode = is_dev


def get_evaluator() -> str | None:
    """Get the current evaluator path override for the current thread, if any."""
    return getattr(_thread_local, 'evaluator_path_override', None)


def _get_evaluator_timeout() -> int:
    """Get the current evaluator timeout for the current thread."""
    return getattr(_thread_local, 'evaluator_timeout', BENCHMARK_TIMEOUT)


def _is_dev_mode() -> bool:
    """Check if we're in benchmark dev mode for the current thread."""
    return getattr(_thread_local, 'is_benchmark_dev_mode', False)


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
    higher_is_better: bool = True  # True = higher scores better (FPS), False = lower better (cycles)
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
    
    # higher_is_better must be explicitly set by the benchmark script
    # Default to True if not specified (common case: FPS, throughput, etc.)
    higher_is_better = data.get("higher_is_better", True)
    
    return BenchmarkResult(
        score=data.get("score"),
        metric_name=metric_name,
        test_gate=bool(test_gate),
        higher_is_better=bool(higher_is_better),
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


def _get_benchmark_path_and_cwd() -> tuple[Path, Path]:
    """Get the benchmark script path and the working directory for execution.
    
    Returns:
        Tuple of (benchmark_path, cwd_path).
        - benchmark_path: Absolute path to the benchmark script to run
        - cwd_path: Working directory where the benchmark should be executed
    """
    workspace_root = get_workspace_root()
    
    # Check if there's an evaluator override
    override = get_evaluator()
    if override:
        # External evaluator - run it from the workspace root
        return Path(override).resolve(), workspace_root
    
    # Default: use the benchmark in the workspace
    benchmark_path = workspace_root / BENCHMARK_SCRIPT_NAME
    return benchmark_path, workspace_root


@tool(args_schema=EvaluateInput)
def evaluate(message: str = "") -> str:
    """Evaluate the codebase by running the benchmark script.

    The benchmark script is at: <workspace_root>/optifiner_benchmark.py
    (or a custom path if configured via set_evaluator)
    
    DO NOT run the benchmark script directly with python or bash commands.
    Always use this evaluate tool instead.

    The benchmark script must output JSON with this format:
    {
        "score": <number>,         # Primary metric value (required, non-null)
        "metric_name": "<string>", # Name like "FPS", "throughput", "cycles" (required)
        "test_gate": <boolean>,    # Must be true for success (required)
        "higher_is_better": <bool>,# true if higher scores are better, false if lower is better (required)
        "metrics": {...},          # Optional additional metrics
        "message": "<string>"      # Optional message
    }

    The benchmark passes when test_gate=true AND score is not null.

    Args:
        message: Optional description of changes made before evaluation.

    Returns:
        Evaluation result with score, test_gate status, and metrics.
    """
    benchmark_path, cwd = _get_benchmark_path_and_cwd()
    
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
        
        timeout = _get_evaluator_timeout()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            env={**os.environ, "WORKSPACE_ROOT": str(cwd)},
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
        
    except subprocess.TimeoutExpired as e:
        timeout = _get_evaluator_timeout()
        
        # Capture any partial output that was produced before the timeout
        partial_stdout = ""
        partial_stderr = ""
        if e.stdout:
            partial_stdout = e.stdout if isinstance(e.stdout, str) else e.stdout.decode('utf-8', errors='replace')
        if e.stderr:
            partial_stderr = e.stderr if isinstance(e.stderr, str) else e.stderr.decode('utf-8', errors='replace')
        
        # Build partial output section for debugging
        partial_output_section = ""
        if partial_stdout or partial_stderr:
            partial_output_section = "\n--- Partial Output (captured before timeout) ---\n"
            if partial_stdout:
                partial_output_section += f"STDOUT:\n{partial_stdout[:2000]}\n"
            if partial_stderr:
                partial_output_section += f"STDERR:\n{partial_stderr[:2000]}\n"
            partial_output_section += "--- End Partial Output ---\n"
        
        if _is_dev_mode():
            # In benchmark dev mode: agent can fix the benchmark
            return (
                f"Error: Benchmark timed out after {timeout} seconds.\n\n"
                f"[BENCHMARK FAILED - timeout]\n"
                f"The benchmark script MUST exit within {timeout} seconds. If it doesn't exit "
                f"(return/complete) within this time limit, the evaluation automatically fails.\n\n"
                f"Please optimize the benchmark script to complete faster and ensure it exits cleanly.\n"
                f"{partial_output_section}"
                f"Tips:\n"
                f"- Reduce the number of frames/iterations being measured\n"
                f"- Use a shorter measurement window\n"
                f"- Ensure the benchmark calls sys.exit() or returns after measurement\n"
                f"- Check for infinite loops or blocking operations"
            )
        else:
            # In improver mode: hard fail, benchmark should already work
            return (
                f"Error: Benchmark timed out after {timeout} seconds.\n\n"
                f"[BENCHMARK FAILED - timeout]\n"
                f"The benchmark script did not exit within the {timeout}s time limit.\n"
                f"This evaluation is considered a FAIL. Your changes may have caused "
                f"an infinite loop or severe performance regression.\n"
                f"{partial_output_section}"
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
        
    except subprocess.TimeoutExpired as e:
        # Capture partial output for debugging
        partial_output = ""
        if e.stdout:
            stdout_str = e.stdout if isinstance(e.stdout, str) else e.stdout.decode('utf-8', errors='replace')
            partial_output += f" Partial stdout: {stdout_str[:500]}"
        if e.stderr:
            stderr_str = e.stderr if isinstance(e.stderr, str) else e.stderr.decode('utf-8', errors='replace')
            partial_output += f" Partial stderr: {stderr_str[:500]}"
        return BenchmarkResult(error=f"Timed out after {BENCHMARK_TIMEOUT} seconds. The benchmark script must exit within {BENCHMARK_TIMEOUT}s.{partial_output}")
    except Exception as e:
        return BenchmarkResult(error=str(e))
