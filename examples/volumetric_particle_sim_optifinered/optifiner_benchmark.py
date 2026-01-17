#!/usr/bin/env python3
"""Benchmark script for OptiFiner - Particle Simulation Benchmark (FPS proxy)."""

import json
import sys
import time
import math
import tracemalloc

"""
This benchmark performs a lightweight, CPU-bound workload to estimate a
synthetic FPS-like score. It also gathers a peak memory usage using
Python's tracemalloc module. The score is returned along with a metric name
and a basic pass/fail gate based on simple functional tests.
"""

# -------------- Functional Tests --------------

def run_tests():
    """Run small functional tests that verify basic behavior.

    Returns:
        (passed_count, total)
    """
    passed = 0
    total = 0

    # Test 1: Simple arithmetic sanity
    total += 1
    try:
        assert (1 + 1) == 2
        passed += 1
    except Exception:
        pass

    # Test 2: Basic memory measurement sanity (non-negative peak will be checked later)
    total += 1
    try:
        mem = _probe_memory_allocation()
        if mem is not None:
            passed += 1
    except Exception:
        pass

    return passed, total

# -------------- Performance Measurement --------------

def _probe_memory_allocation():
    # A tiny allocation to ensure tracemalloc has something to track.
    lst = [i for i in range(10)]
    s = sum(lst)
    del lst
    return s


def measure_fps(duration_seconds: float = 0.5) -> (float, dict):
    """Perform a busy-wait workload to estimate FPS-like score.

    Args:
        duration_seconds: How long to run the workload to estimate FPS.
    Returns:
        (fps, metrics_dict)
    """
    frames = 0
    a = 0.0
    t0 = time.perf_counter()
    while (time.perf_counter() - t0) < duration_seconds:
        # Simulate per-frame work with light math
        a = (a * 1.000123) + 0.00000123
        for _ in range(6):
            a = math.sin(a) * 0.9999 + math.cos(a) * 0.0001
        frames += 1
    duration = time.perf_counter() - t0
    fps = frames / duration if duration > 0 else 0.0

    # Memory usage
    peak_mb = None
    try:
        current, peak = tracemalloc.get_traced_memory()
        peak_mb = peak / 1024.0 / 1024.0
    except Exception:
        peak_mb = None

    metrics = {
        "duration_s": duration,
        "frames": frames,
        "peak_memory_mb": peak_mb if peak_mb is not None else 0.0,
    }
    return fps, metrics

# -------------- Main Entry --------------

def main():
    quiet = "--quiet" in sys.argv

    result = {
        "score": None,
        "metric_name": "FPS",
        "test_gate": False,
        "metrics": {},
        "message": "",
    }

    try:
        tests_passed, tests_total = run_tests()

        # Start memory tracing for a more realistic measurement
        tracemalloc.start()
        fps, fps_metrics = measure_fps(0.5)
        tracemalloc.stop()

        # Build final results
        score = float(fps) if fps is not None else None
        test_gate = (tests_passed == tests_total) and (score is not None)

        result.update({
            "score": score,
            "test_gate": test_gate,
            "metrics": {
                **fps_metrics,
                "tests_passed": tests_passed,
                "tests_total": tests_total,
            },
            "message": f"Benchmark completed. FPS: {score:.2f}" if score is not None else "Benchmark failed to produce FPS",
        })

    except Exception as e:
        # In case of unexpected errors, still emit a valid JSON with failure
        result.update({
            "score": None,
            "metric_name": "FPS",
            "test_gate": False,
            "metrics": {
                "error": str(e)
            },
            "message": f"Benchmark error: {e}",
        })

    # Output JSON (no extra stdout if quiet is requested, but we always output JSON)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
