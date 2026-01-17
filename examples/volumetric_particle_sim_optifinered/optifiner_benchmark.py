#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os

# Add the path to the particle_sim.py to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from particle_sim import ParticleSimulation, get_fps
except ImportError as e:
    print(f"Error importing particle_sim: {e}", file=sys.stderr)
    sys.exit(1)

def run_functional_test() -> bool:
    """Run a basic functional test to ensure the simulation starts and cleans up."""
    try:
        # Run in benchmark mode for a very short duration to just check startup
        sim = ParticleSimulation(benchmark_mode=True, benchmark_duration=0.1)
        sim.run()
        sim.cleanup()
        return True
    except Exception as e:
        print(f"Functional test failed: {e}", file=sys.stderr)
        return False

def measure_performance(duration: float = 5.0) -> float:
    """Measure the FPS of the particle simulation."""
    sim = None
    try:
        sim = ParticleSimulation(benchmark_mode=True, benchmark_duration=duration)
        sim.run()
        fps_score = get_fps()
        return fps_score
    except Exception as e:
        print(f"Performance measurement failed: {e}", file=sys.stderr)
        return 0.0 # Return 0.0 or handle as an error
    finally:
        if sim:
            sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    score = None
    test_gate = False
    message = "Benchmark failed."
    
    try:
        # Functional test
        test_gate = run_functional_test()
        if not test_gate:
            message = "Functional test failed. Cannot proceed with performance measurement."
            raise RuntimeError(message)

        # Performance measurement
        score = measure_performance(duration=5.0) # Run for 5 seconds to get a stable FPS
        if score > 0:
            message = f"Benchmark passed. FPS: {score:.2f}"
        else:
            message = "Benchmark failed: FPS score is 0 or less."
            test_gate = False # If score is 0, it's likely a failure
            
    except Exception as e:
        message = str(e)
        test_gate = False
        score = None # Ensure score is None on error

    result = {
        "score": score,
        "metric_name": "FPS",
        "test_gate": test_gate,
        "metrics": {},
        "message": message
    }
    
    print(json.dumps(result))
    sys.exit(0 if test_gate and score is not None else 1)

if __name__ == "__main__":
    main()
