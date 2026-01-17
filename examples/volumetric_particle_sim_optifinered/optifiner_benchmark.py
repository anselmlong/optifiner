#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os
import pygame

# Add the workspace directory to the Python path to import particle_sim
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from particle_sim import ParticleSimulation, NUM_PARTICLES

def run_tests() -> tuple[int, int]:
    """Run functional tests to verify the application works."""
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Particle count
    tests_total += 1
    sim = None
    try:
        sim = ParticleSimulation(headless=True)
        if sim.get_particle_count() == NUM_PARTICLES:
            tests_passed += 1
            print(f"Test 1 (Particle Count) passed: {sim.get_particle_count()} particles found.")
        else:
            print(f"Test 1 (Particle Count) failed: Expected {NUM_PARTICLES}, got {sim.get_particle_count()}", file=sys.stderr)
    except Exception as e:
        print(f"Test 1 (Particle Count) failed: {e}", file=sys.stderr)
    finally:
        if sim:
            sim.cleanup()
    
    # Test 2: Basic simulation run (ensure no crashes in headless mode)
    tests_total += 1
    sim = None
    try:
        sim = ParticleSimulation(headless=True)
        # Run for a very short duration to check for immediate crashes
        sim.run_headless_frames(60) # Run 60 frames (approx 1 second at 60 FPS)
        tests_passed += 1
        print("Test 2 (Basic Simulation Run) passed: Simulation ran without crashing in headless mode.")
    except Exception as e:
        print(f"Test 2 (Basic Simulation Run) failed: {e}", file=sys.stderr)
    finally:
        if sim:
            sim.cleanup()

    return tests_passed, tests_total

def measure_performance(num_frames_to_run: int = 10) -> tuple[float, dict]:
    """Measure the primary performance metric (FPS) by running a fixed number of frames."""
    sim = None
    try:
        sim = ParticleSimulation(headless=True)
        
        print(f"Measuring performance for {num_frames_to_run} frames in headless mode...")
        
        start_time = time.time()
        sim.run_headless_frames(num_frames_to_run)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        if elapsed_time > 0:
            avg_fps = num_frames_to_run / elapsed_time
        else:
            avg_fps = 0.0
        
        print(f"Average FPS over {num_frames_to_run} frames: {avg_fps:.2f}")
        
        return avg_fps, {"particle_count": sim.get_particle_count(), "measured_frames": num_frames_to_run}
    except Exception as e:
        print(f"Performance measurement failed: {e}", file=sys.stderr)
        return 0.0, {}
    finally:
        if sim:
            sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    try:
        # Initialize Pygame for font rendering in case of non-headless tests, then quit.
        # This is a workaround for potential issues with pygame.init() in sub-processes.
        pygame.init()
        pygame.quit()

        tests_passed, tests_total = run_tests()
        
        # Only run performance if tests pass
        score = None
        extra_metrics = {}
        if tests_passed == tests_total:
            score, extra_metrics = measure_performance()
        
        result = {
            "score": score,
            "metric_name": "FPS",
            "test_gate": tests_passed == tests_total,
            "metrics": {
                "tests_passed": tests_passed,
                "tests_total": tests_total,
                **extra_metrics
            },
            "message": f"Score: {score:.2f} FPS, Tests: {tests_passed}/{tests_total} passed." if score is not None else f"Tests: {tests_passed}/{tests_total} passed. Score not measured due to test failure."
        }
        
        if not quiet:
            print(json.dumps(result, indent=4))
        else:
            print(json.dumps(result))
        sys.exit(0 if result["test_gate"] and result["score"] is not None else 1)
        
    except Exception as e:
        result = {
            "score": None,
            "metric_name": "error",
            "test_gate": False,
            "message": str(e)
        }
        if not quiet:
            print(json.dumps(result, indent=4))
        else:
            print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
