#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os

# Add the path to the particle_sim.py to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import particle_sim
except ImportError:
    # Fallback for when the script is run from a different directory
    sys.path.insert(0, os.getcwd())
    import particle_sim


def main():
    quiet = "--quiet" in sys.argv
    
    score = None
    metric_name = "FPS"
    test_gate = False
    metrics = {}
    message = "Benchmark failed."

    sim = None # Initialize sim to None
    try:
        # Initialize simulation once
        sim = particle_sim.ParticleSimulation()

        # Step 1: Run functional tests
        print("Running functional test...", file=sys.stderr)
        particle_sim.set_benchmark_mode(True, frames=10)
        sim.run()
        # Check if sim.running is False, indicating it completed the frames
        test_gate = not sim.running # If sim.running is False, it means it completed the benchmark frames
        if not test_gate:
            message = "Functional test did not complete expected frames."
            sys.exit(1)
        print("Functional test passed.", file=sys.stderr)

        # Step 2: Measure performance
        duration_frames = 100 # Reduced for debugging
        print(f"Measuring performance over {duration_frames} frames...", file=sys.stderr)
        
        # Reset FPS counters for accurate measurement
        particle_sim._frame_count = 0
        particle_sim._fps_start_time = time.time()
        particle_sim._current_fps = 0.0

        particle_sim.set_benchmark_mode(True, frames=duration_frames)
        sim.running = True # Reset running flag for the next run
        start_time = time.time()
        sim.run()
        end_time = time.time()

        if not sim.running: # Check if sim completed the benchmark frames
            total_frames = duration_frames
            total_time = end_time - start_time
            
            if total_time > 0:
                score = total_frames / total_time
            else:
                score = 0.0
            
            print(f"Performance measurement complete. Average FPS: {score:.2f}", file=sys.stderr)
        else:
            message = "Performance measurement did not complete expected frames."
            test_gate = False
            sys.exit(1)

        if score is not None and score > 0:
            message = f"Benchmark passed. Average FPS: {score:.2f}"
        else:
            message = "Performance measurement failed or returned zero FPS."
            test_gate = False
            sys.exit(1)

    except Exception as e:
        message = f"An unexpected error occurred: {str(e)}"
        test_gate = False
        score = None
        sys.exit(1)
    finally:
        if sim:
            sim.cleanup()
        result = {
            "score": score,
            "metric_name": metric_name,
            "test_gate": test_gate,
            "metrics": metrics,
            "message": message
        }
        print(json.dumps(result))
        if not test_gate or score is None:
            sys.exit(1)
        else:
            sys.exit(0)

if __name__ == "__main__":
    main()
