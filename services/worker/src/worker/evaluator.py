"""Queue-based evaluator for running benchmarks on host machine.

This module provides a singleton evaluator that:
1. Processes evaluation requests in a queue
2. Prevents simultaneous evaluations
3. Runs benchmarks on the host machine (not in containers)

This is important because:
- Browser-based benchmarks need host access
- Complex setups (pygame, etc.) run better without containers
- We can visualize everything as it runs
"""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


from worker.tools.evaluate import BENCHMARK_TIMEOUT


@dataclass
class EvaluationRequest:
    """A request to evaluate a workspace."""
    
    request_id: str
    workspace_path: str
    evaluator_path: str
    timeout: int = BENCHMARK_TIMEOUT
    callback: Callable[[dict[str, Any]], None] | None = None
    
    # Result is set after evaluation completes
    result: dict[str, Any] | None = None
    completed: threading.Event = field(default_factory=threading.Event)


@dataclass
class EvaluationResult:
    """Result from an evaluation."""
    
    success: bool
    score: float | None
    passed: bool | None = None
    tests_passed: int | None = None
    tests_total: int | None = None
    metrics: dict[str, Any] | None = None
    message: str | None = None
    metric_name: str | None = None
    higher_is_better: bool | None = None  # True = higher is better (FPS), False = lower is better (cycles)
    error: str | None = None
    raw_output: str | None = None
    duration_seconds: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "score": self.score,
            "passed": self.passed,
            "tests_passed": self.tests_passed,
            "tests_total": self.tests_total,
            "metrics": self.metrics,
            "message": self.message,
            "metric_name": self.metric_name,
            "higher_is_better": self.higher_is_better,
            "error": self.error,
            "raw_output": self.raw_output,
            "duration_seconds": self.duration_seconds,
        }


class EvaluatorQueue:
    """Singleton queue-based evaluator that prevents simultaneous evaluations.
    
    This ensures that only one evaluation runs at a time, which is critical for:
    - Browser-based benchmarks that need exclusive display access
    - Games that might conflict with each other
    - Accurate performance measurements
    """
    
    _instance: "EvaluatorQueue | None" = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the evaluator queue."""
        if self._initialized:
            return
        
        self._queue: queue.Queue[EvaluationRequest] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._running = False
        self._current_evaluation: EvaluationRequest | None = None
        self._initialized = True
    
    def start(self):
        """Start the evaluation worker thread."""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
    
    def stop(self):
        """Stop the evaluation worker thread."""
        self._running = False
        # Add sentinel to unblock queue
        self._queue.put(None)  # type: ignore
        
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
            self._worker_thread = None
    
    def _worker_loop(self):
        """Main worker loop that processes evaluation requests."""
        while self._running:
            try:
                request = self._queue.get(timeout=1)
                
                if request is None:  # Sentinel for shutdown
                    continue
                
                self._current_evaluation = request
                
                try:
                    result = self._run_evaluation(request)
                    request.result = result
                    
                    if request.callback:
                        request.callback(result)
                finally:
                    request.completed.set()
                    self._current_evaluation = None
                    
            except queue.Empty:
                continue
            except Exception as e:
                # Log error but keep running
                print(f"Evaluator worker error: {e}", file=sys.stderr)
    
    def _run_evaluation(self, request: EvaluationRequest) -> dict[str, Any]:
        """Run a single evaluation.
        
        Args:
            request: The evaluation request.
            
        Returns:
            Evaluation result dictionary.
        """
        start_time = time.time()
        
        evaluator_path = Path(request.evaluator_path)
        workspace_path = Path(request.workspace_path)
        
        if not evaluator_path.exists():
            return EvaluationResult(
                success=False,
                score=None,
                error=f"Evaluator not found: {evaluator_path}",
            ).to_dict()
        
        if not workspace_path.exists():
            return EvaluationResult(
                success=False,
                score=None,
                error=f"Workspace not found: {workspace_path}",
            ).to_dict()
        
        # Determine how to run the evaluator
        if evaluator_path.suffix == ".py":
            cmd = [self._get_python_executable(), str(evaluator_path), "--quiet"]
        elif evaluator_path.suffix == ".sh":
            cmd = ["bash", str(evaluator_path)]
        elif evaluator_path.suffix in (".js", ".mjs"):
            cmd = ["node", str(evaluator_path)]
        else:
            cmd = [str(evaluator_path)]
        
        try:
            env = {**os.environ, "WORKSPACE_ROOT": str(workspace_path)}
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=request.timeout,
                cwd=str(workspace_path),
                env=env,
            )
            
            duration = time.time() - start_time
            
            if result.returncode != 0:
                error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
                return EvaluationResult(
                    success=False,
                    score=None,
                    error=f"Evaluator failed (exit {result.returncode}): {error_output[:500]}",
                    raw_output=result.stdout,
                    duration_seconds=duration,
                ).to_dict()
            
            output = result.stdout.strip()
            
            # Try to parse JSON output
            data = self._parse_output(output)
            
            if data is None:
                return EvaluationResult(
                    success=False,
                    score=None,
                    error=f"Could not parse evaluator output: {output[:200]}",
                    raw_output=output,
                    duration_seconds=duration,
                ).to_dict()
            
            score = data.get("score")
            if score is None:
                return EvaluationResult(
                    success=False,
                    score=None,
                    error="Evaluator output missing 'score' field",
                    raw_output=output,
                    duration_seconds=duration,
                ).to_dict()
            
            # higher_is_better must be explicitly set by benchmark script
            # Default to True if not specified (common case: FPS, throughput)
            metric_name = data.get("metric_name")
            higher_is_better = data.get("higher_is_better", True)
            
            return EvaluationResult(
                success=True,
                score=float(score),
                passed=data.get("passed"),
                tests_passed=data.get("tests_passed"),
                tests_total=data.get("tests_total"),
                metrics=data.get("metrics"),
                message=data.get("message"),
                metric_name=metric_name,
                higher_is_better=higher_is_better,
                raw_output=output,
                duration_seconds=duration,
            ).to_dict()
            
        except subprocess.TimeoutExpired as e:
            # Collect partial output from the timed-out process
            partial_output = None
            if e.output:
                partial_output = e.output if isinstance(e.output, str) else e.output.decode("utf-8", errors="replace")
            if e.stderr:
                stderr_text = e.stderr if isinstance(e.stderr, str) else e.stderr.decode("utf-8", errors="replace")
                if partial_output:
                    partial_output = f"{partial_output}\n--- STDERR ---\n{stderr_text}"
                else:
                    partial_output = stderr_text
            
            # Print partial output for debugging
            if partial_output:
                print(f"\n[TIMEOUT] Partial output before timeout:\n{partial_output}\n", file=sys.stderr)
            
            return EvaluationResult(
                success=False,
                score=None,
                error=f"Evaluator timed out after {request.timeout} seconds",
                raw_output=partial_output,
                duration_seconds=time.time() - start_time,
            ).to_dict()
            
        except Exception as e:
            return EvaluationResult(
                success=False,
                score=None,
                error=f"Error running evaluator: {e}",
                duration_seconds=time.time() - start_time,
            ).to_dict()
    
    def _parse_output(self, output: str) -> dict[str, Any] | None:
        """Parse evaluator output, handling garbage prefixes like pygame welcome.
        
        Args:
            output: Raw stdout from the evaluator.
            
        Returns:
            Parsed JSON dict or None if parsing fails.
        """
        # Try direct parse first
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in output
        json_start = output.find("{")
        if json_start >= 0:
            try:
                return json.loads(output[json_start:])
            except json.JSONDecodeError:
                pass
        
        # Try to extract a number as fallback
        import re
        numbers = re.findall(r"[-+]?\d*\.?\d+", output)
        if numbers:
            return {"score": float(numbers[0]), "raw": output}
        
        return None
    
    def _get_python_executable(self) -> str:
        """Get the Python executable to use."""
        if sys.executable:
            return sys.executable
        if shutil.which("python3"):
            return "python3"
        if shutil.which("python"):
            return "python"
        return "python3"
    
    def evaluate(
        self,
        workspace_path: str,
        evaluator_path: str,
        timeout: int = BENCHMARK_TIMEOUT,
        wait: bool = True,
    ) -> dict[str, Any] | None:
        """Submit an evaluation request.
        
        Args:
            workspace_path: Path to the workspace to evaluate.
            evaluator_path: Path to the evaluator script.
            timeout: Evaluation timeout in seconds.
            wait: If True, block until evaluation completes. If False, return None immediately.
            
        Returns:
            Evaluation result dict if wait=True, None if wait=False.
        """
        if not self._running:
            self.start()
        
        request = EvaluationRequest(
            request_id=f"eval_{time.time()}",
            workspace_path=workspace_path,
            evaluator_path=evaluator_path,
            timeout=timeout,
        )
        
        self._queue.put(request)
        
        if wait:
            request.completed.wait()
            return request.result
        
        return None
    
    def evaluate_sync(
        self,
        workspace_path: str,
        evaluator_path: str,
        timeout: int = BENCHMARK_TIMEOUT,
    ) -> dict[str, Any]:
        """Synchronously evaluate a workspace (blocks until complete).
        
        This is a convenience method that always waits for the result.
        
        Args:
            workspace_path: Path to the workspace to evaluate.
            evaluator_path: Path to the evaluator script.
            timeout: Evaluation timeout in seconds.
            
        Returns:
            Evaluation result dict.
        """
        result = self.evaluate(workspace_path, evaluator_path, timeout, wait=True)
        return result or {"success": False, "score": None, "error": "No result returned"}
    
    @property
    def is_busy(self) -> bool:
        """Check if an evaluation is currently running."""
        return self._current_evaluation is not None
    
    @property
    def queue_size(self) -> int:
        """Get the number of pending evaluations."""
        return self._queue.qsize()


# Global singleton instance
_evaluator: EvaluatorQueue | None = None


def get_evaluator() -> EvaluatorQueue:
    """Get the global evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = EvaluatorQueue()
        _evaluator.start()
    return _evaluator


def evaluate(
    workspace_path: str,
    evaluator_path: str,
    timeout: int = BENCHMARK_TIMEOUT,
) -> dict[str, Any]:
    """Evaluate a workspace using the global evaluator queue.
    
    This ensures evaluations are processed one at a time.
    
    Args:
        workspace_path: Path to the workspace to evaluate.
        evaluator_path: Path to the evaluator script.
        timeout: Evaluation timeout in seconds.
        
    Returns:
        Evaluation result dict.
    """
    return get_evaluator().evaluate_sync(workspace_path, evaluator_path, timeout)
