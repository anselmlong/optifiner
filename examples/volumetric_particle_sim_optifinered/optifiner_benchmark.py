#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os
import pygame # Import pygame at the top level

# Add the current directory to the path to import particle_sim
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from particle_sim import ParticleSimulation, SCREEN_WIDTH, SCREEN_HEIGHT

def run_functional_test() -> bool:
    """
    Runs a short simulation to check if the application starts and runs without crashing.
    """
    # print("Running functional test...", file=sys.stderr)
    sim = None
    try:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        
        sim = ParticleSimulation()
        # Run for a very short duration to ensure it initializes and renders at least one frame
        start_time = time.time()
        while time.time() - start_time < 0.5: # Run for 0.5 seconds
            sim.run_frame()
            if not sim.running:
                break
        # print("Functional test passed: Simulation ran without immediate crash.", file=sys.stderr)
        return True
    except Exception as e:
        # print(f"Functional test failed: {e}", file=sys.stderr)
        return False
    finally:
        if sim:
            sim.cleanup()
        # Pygame quit is handled by sim.cleanup(), but ensure it's fully quit if not already
        if pygame.get_init():
            pygame.quit()


def measure_performance(duration: int = 5) -> tuple[float, dict]:
    """
    Measures the average FPS over a given duration.
    """
    # print(f"Measuring performance for {duration} seconds...", file=sys.stderr)
    sim = None
    fps_values = []
    try:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

        sim = ParticleSimulation()
        sim.running = True # Ensure the simulation loop runs

        start_time = time.time()
        frame_count = 0
        
        # Run the simulation for the specified duration
        while time.time() - start_time < duration:
            sim.run_frame()
            if not sim.running:
                break
            
            current_fps = sim.get_fps()
            if current_fps > 0: # Only record valid FPS values
                fps_values.append(current_fps)
            frame_count += 1

        if not fps_values:
            # print("Warning: No FPS values recorded during performance measurement.", file=sys.stderr)
            return 0.0, {}

        avg_fps = sum(fps_values) / len(fps_values)
        # print(f"Average FPS: {avg_fps:.2f}", file=sys.stderr)
        return avg_fps, {"frames_rendered": frame_count}

    except Exception as e:
        # print(f"Performance measurement failed: {e}", file=sys.stderr)
        return 0.0, {}
    finally:
        if sim:
            sim.cleanup()
        # Pygame quit is handled by sim.cleanup(), but ensure it's fully quit if not already
        if pygame.get_init():
            pygame.quit()

def main():
    quiet = "--quiet" in sys.argv
    
    try:
        test_gate_passed = run_functional_test()
        
        score, extra_metrics = 0.0, {}
        if test_gate_passed:
            score, extra_metrics = measure_performance(duration=5) # Measure over 5 seconds

        result = {
            "score": score if test_gate_passed else None,
            "metric_name": "FPS",
            "test_gate": test_gate_passed,
            "metrics": {
                **extra_metrics
            },
            "message": f"Functional test: {'PASSED' if test_gate_passed else 'FAILED'}. Average FPS: {score:.2f}"
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
