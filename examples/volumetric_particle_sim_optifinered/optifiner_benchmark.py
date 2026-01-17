#!/usr/bin/env python3
"""Benchmark script for OptiFiner Particle Simulation (FPS benchmark)."""

import json
import sys
import time
import os
from typing import Dict, Any

# Import the modded codebase module to benchmark
_start_load = time.time()
try:
    import particle_sim as PS  # type: ignore
except Exception as e:
    # If import fails, we still produce a JSON with error
    def _to_json_error(msg: str) -> str:
        return json.dumps({
            "score": None,
            "metric_name": "FPS",
            "test_gate": False,
            "metrics": {
                "memory_mb": 0.0,
                "load_time_ms": (time.time() - _start_load) * 1000.0
            },
            "message": msg
        })
    if "--quiet" in sys.argv:
        print(_to_json_error("import_error"))
    else:
        print(_to_json_error("import_error"))
    sys.exit(1)
_load_time_ms = (time.time() - _start_load) * 1000.0

# Optional: measure memory usage if psutil is available
def _get_memory_mb() -> float:
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024.0 * 1024.0)
    except Exception:
        return 0.0

# Functional tests: verify the simulate_frames API exists and can run a tiny frame batch
def run_tests() -> (int, int):
    tests_passed = 0
    tests_total = 0

    tests_total += 1
    try:
        # Run a very small, quick simulation to ensure API works
        if not hasattr(PS, 'simulate_frames'):
            raise AttributeError('simulate_frames API not found in particle_sim')
        PS.simulate_frames(2, dt=1.0/60.0)
        tests_passed += 1
    except Exception as e:
        # Print to stderr for debugging, but still return JSON later
        print(f"Test 1 failed: {e}", file=sys.stderr)
    return tests_passed, tests_total

# Performance measurement: compute FPS by simulating a number of frames
def measure_performance(frames: int = 60) -> (float, Dict[str, Any]):
    start = time.time()
    PS.simulate_frames(frames, dt=1.0/60.0)
    end = time.time()
    # Best-effort: use wall-clock based FPS estimate
    actual_fps = frames / max(1e-9, (end - start))
    mem = _get_memory_mb()
    load_ms = _load_time_ms
    return float(actual_fps), {
        "actual_fps": actual_fps,
        "frames": frames,
        "memory_mb": mem,
        "load_time_ms": load_ms
    }

def main():
    quiet = "--quiet" in sys.argv

    try:
        tests_passed, tests_total = run_tests()
        score, extra = measure_performance(60)

        test_gate = (tests_passed == tests_total) and (score is not None)
        result: Dict[str, Any] = {
            "score": float(score) if score is not None else None,
            "metric_name": "FPS",
            "test_gate": bool(test_gate),
            "metrics": {
                "memory_mb": extra.get("memory_mb", 0.0),
                "load_time_ms": extra.get("load_time_ms", _load_time_ms),
                "frames_measured": extra.get("frames", 60)
            },
            "message": f"Tests {tests_passed}/{tests_total}; FPS={score:.2f}"
        }

        # Ensure a valid JSON output format even when quiet is required
        print(json.dumps(result))
        # Exit code 0 only if benchmark gate passes
        sys.exit(0 if result["test_gate"] else 1)

    except Exception as e:
        result = {
            "score": None,
            "metric_name": "FPS",
            "test_gate": False,
            "metrics": {
                "memory_mb": _get_memory_mb(),
                "load_time_ms": _load_time_ms
            },
            "message": str(e)
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
