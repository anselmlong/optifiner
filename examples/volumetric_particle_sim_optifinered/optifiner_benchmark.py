#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os

# Add the current directory to the Python path to import particle_sim
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from particle_sim import ParticleSimulation, get_current_fps, reset_fps_counter
    import pygame
except ImportError as e:
    print(json.dumps({
        "score": None,
        "metric_name": "error",
        "test_gate": False,
        "message": f"Failed to import particle_sim or pygame: {e}. Please ensure dependencies are installed."
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
    Measure the FPS of the particle simulation.
    Runs the simulation for a specified duration and returns the average FPS.
    """
    sim = None
    try:
        sim = ParticleSimulation()
        # Reset FPS counter for accurate measurement during benchmark run
        reset_fps_counter()

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
        # Run functional tests
        test_gate_passed = run_functional_tests()
        result["test_gate"] = test_gate_passed
        
        if not test_gate_passed:
            result["message"] = "Functional tests failed."
            print(json.dumps(result))
            sys.exit(1)

        # Measure performance
        fps_score, extra_metrics = measure_performance(duration=5.0) # Run for 5 seconds
        result["score"] = fps_score
        result["metrics"].update(extra_metrics)
        
        if fps_score > 0:
            result["message"] = f"Benchmark passed. FPS: {fps_score:.2f}"
        else:
            result["test_gate"] = False
            result["message"] = "Benchmark failed: FPS score is 0 or less."
            sys.exit(1)
            
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        result["score"] = None
        result["metric_name"] = "error"
        result["test_gate"] = False
        result["message"] = f"An unexpected error occurred: {str(e)}"
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
