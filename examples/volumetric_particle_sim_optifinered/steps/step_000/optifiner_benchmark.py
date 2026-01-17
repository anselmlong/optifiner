#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os

# Add the current directory to the Python path to import particle_sim
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from particle_sim import ParticleSimulation
    import pygame
except ImportError as e:
    print(json.dumps({
        "score": None,
        "metric_name": "error",
        "test_gate": False,
        "message": f"Failed to import necessary modules: {e}. Ensure pygame is installed."
    }))
    sys.exit(1)

def run_functional_tests() -> bool:
    """
    Run basic functional tests.
    For this simulation, we'll just check if Pygame initializes and a window can be created.
    """
    try:
        pygame.init()
        screen = pygame.display.set_mode((64, 48), pygame.HIDDEN) # Small window for quick test, hidden
        pygame.display.set_caption("Benchmark Test")
        pygame.quit()
        return True
    except Exception as e:
        print(f"Functional test failed: {e}", file=sys.stderr)
        return False

def measure_performance(duration_seconds: int = 5) -> tuple[float, dict]:
    """
    Measure the average FPS over a given duration.
    """
    sim = None
    try:
        print("Starting performance measurement...", file=sys.stderr)
        sim = ParticleSimulation()
        print("ParticleSimulation initialized.", file=sys.stderr)
        sim.running = True # Ensure the simulation loop starts

        frame_times = [] # To store time taken for each frame
        start_benchmark_time = time.time()
        frame_count = 0

        while time.time() - start_benchmark_time < duration_seconds:
            frame_start_time = time.time()

            # Process events to keep pygame happy and allow quitting
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sim.running = False
                    break
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        sim.running = False
                        break
            
            if not sim.running:
                print("Simulation stopped by event.", file=sys.stderr)
                break

            dt = sim.clock.tick(60) / 1000.0 # Limit to 60 FPS, get actual dt
            dt = min(dt, 0.1) # Cap delta time

            sim.update(dt)
            sim.render()
            
            frame_end_time = time.time()
            frame_duration = frame_end_time - frame_start_time
            if frame_duration > 0: # Avoid division by zero
                frame_times.append(1.0 / frame_duration)
            
            frame_count += 1
            if frame_count % 30 == 0: # Print progress every 30 frames
                print(f"Benchmark running, frames: {frame_count}, last frame FPS: {1.0 / frame_duration:.2f}", file=sys.stderr)

        print("Performance measurement loop finished.", file=sys.stderr)
        if not frame_times:
            print("No FPS data collected during benchmark.", file=sys.stderr)
            return 0.0, {"message": "No FPS data collected."}

        avg_fps = sum(frame_times) / len(frame_times)
        print(f"Average FPS calculated: {avg_fps:.2f}", file=sys.stderr)
        return avg_fps, {}

    except Exception as e:
        print(f"Performance measurement failed: {e}", file=sys.stderr)
        return 0.0, {"error": str(e)}
    finally:
        if sim:
            print("Cleaning up simulation...", file=sys.stderr)
            sim.cleanup()
        pygame.quit() # Ensure pygame is quit even if sim.cleanup fails
        print("Pygame quit.", file=sys.stderr)


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
        fps_score, extra_metrics = measure_performance(duration_seconds=5)
        result["score"] = fps_score
        result["metrics"].update(extra_metrics)
        
        if fps_score > 0:
            result["message"] = f"Benchmark passed. Average FPS: {fps_score:.2f}"
        else:
            result["test_gate"] = False # If FPS is 0, consider it a failure
            result["message"] = "Benchmark failed: Could not measure FPS or FPS was 0."
            sys.exit(1)

        print(json.dumps(result))
        sys.exit(0 if result["test_gate"] and result["score"] is not None else 1)
        
    except Exception as e:
        result["score"] = None
        result["metric_name"] = "error"
        result["test_gate"] = False
        result["message"] = f"An unexpected error occurred: {str(e)}"
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
