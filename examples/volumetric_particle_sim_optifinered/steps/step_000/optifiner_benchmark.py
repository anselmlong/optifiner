#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os

# Add the current directory to the Python path to import particle_sim
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from particle_sim import ParticleSimulation, get_current_fps
    import pygame
except ImportError as e:
    print(json.dumps({
        "score": None,
        "metric_name": "error",
        "test_gate": False,
        "message": f"Failed to import particle_sim or pygame: {e}. Make sure dependencies are installed."
    }))
    sys.exit(1)

def run_functional_tests() -> bool:
    """
    Run basic functional tests.
    For this simulation, a basic test is to ensure it can initialize and run for a short period without crashing.
    """
    try:
        sim = ParticleSimulation()
        # Run for a very short duration to ensure initialization and first few frames work
        sim.run(duration=0.1) 
        sim.cleanup()
        return True
    except Exception as e:
        print(f"Functional test failed: {e}", file=sys.stderr)
        return False

def measure_performance(duration: float = 5.0) -> tuple[float, dict]:
    """
    Measure the average FPS over a given duration.
    """
    sim = None
    try:
        sim = ParticleSimulation()
        # Reset FPS counter for accurate measurement
        global _frame_count, _fps_start_time, _current_fps
        _frame_count = 0
        _fps_start_time = time.time()
        _current_fps = 0.0

        sim.run(duration=duration)
        
        # Get the final FPS reading
        fps = get_current_fps()
        
        return fps, {}
    except Exception as e:
        print(f"Performance measurement failed: {e}", file=sys.stderr)
        return 0.0, {"error": str(e)}
    finally:
        if sim:
            sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    result = {
        "score": None,
        "metric_name": "FPS",
        "test_gate": False,
        "metrics": {},
        "message": ""
    }

    try:
        # Functional tests
        test_gate_passed = run_functional_tests()
        result["test_gate"] = test_gate_passed
        if not test_gate_passed:
            result["message"] = "Functional tests failed."
            print(json.dumps(result))
            sys.exit(1)

        # Performance measurement
        fps_score, extra_metrics = measure_performance(duration=5.0) # Measure over 5 seconds
        result["score"] = fps_score
        result["metrics"].update(extra_metrics)
        result["message"] = f"All tests passed. Average FPS: {fps_score:.2f}"
        
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        result["score"] = None
        result["metric_name"] = "error"
        result["test_gate"] = False
        result["message"] = str(e)
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
