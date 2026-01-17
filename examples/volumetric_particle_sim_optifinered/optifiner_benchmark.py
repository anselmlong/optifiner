#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os

# Add the workspace directory to the Python path to import particle_sim
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from particle_sim import ParticleSimulation, get_fps

def run_functional_test() -> bool:
    """
    Runs a short simulation to check for crashes or immediate errors.
    Returns True if the simulation runs without exceptions, False otherwise.
    """
    print("Running functional test...", file=sys.stderr)
    sim = None
    try:
        sim = ParticleSimulation()
        # Run for a very short duration to ensure initialization and first few frames work
        sim.run(duration=0.5) 
        print("Functional test passed.", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Functional test failed: {e}", file=sys.stderr)
        return False
    finally:
        if sim:
            sim.cleanup()

def measure_performance(duration: int = 5) -> float:
    """
    Measures the average FPS over a given duration.
    """
    print(f"Measuring performance for {duration} seconds...", file=sys.stderr)
    sim = None
    try:
        sim = ParticleSimulation()
        # Reset FPS counter for accurate measurement
        global _frame_count, _fps_start_time, _current_fps
        _frame_count = 0
        _fps_start_time = time.time()
        _current_fps = 0.0

        sim.run(duration=duration)
        
        final_fps = get_fps()
        print(f"Performance measurement complete. Final FPS: {final_fps}", file=sys.stderr)
        return final_fps
    except Exception as e:
        print(f"Performance measurement failed: {e}", file=sys.stderr)
        return 0.0 # Return 0 or handle as an error
    finally:
        if sim:
            sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    score = None
    test_gate = False
    message = "Benchmark failed."
    
    try:
        # Functional Test
        test_gate = run_functional_test()
        
        if not test_gate:
            message = "Functional test failed. Cannot proceed with performance measurement."
        else:
            # Performance Measurement
            fps_score = measure_performance(duration=5) # Measure over 5 seconds
            score = fps_score
            message = f"Benchmark completed. FPS: {score:.2f}"
            
    except Exception as e:
        message = f"An unexpected error occurred: {e}"
        test_gate = False
        score = None # Ensure score is None on unexpected error
        
    finally:
        result = {
            "score": score,
            "metric_name": "FPS",
            "test_gate": test_gate,
            "metrics": {},
            "message": message
        }
        
        if quiet:
            print(json.dumps(result))
        else:
            print(json.dumps(result, indent=4))
        
        sys.exit(0 if test_gate and score is not None else 1)

if __name__ == "__main__":
    main()
