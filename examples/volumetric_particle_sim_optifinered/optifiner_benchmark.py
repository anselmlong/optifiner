#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os
import pygame # Import pygame at the top

# Ensure pygame doesn't try to open a window if we're running headless
os.environ["SDL_VIDEODRIVER"] = "dummy"

# Import the simulation class
from particle_sim import ParticleSimulation, SCREEN_WIDTH, SCREEN_HEIGHT

def run_functional_tests() -> bool:
    """Run functional tests to verify the application works."""
    sim = None
    try:
        # Test 1: Initialize and cleanup
        sim = ParticleSimulation()
        sim.cleanup()
        
        # Test 2: Run for a very short period without crashing
        sim = ParticleSimulation()
        sim.running = True
        sim.update(0.01) # Update once
        sim.render() # Render once
        sim.cleanup()
        
        return True
    except Exception as e:
        print(f"Functional test failed: {e}", file=sys.stderr)
        return False

def measure_performance(duration: int = 5) -> tuple[float, dict]:
    """Measure the primary performance metric (FPS)."""
    sim = None
    try:
        sim = ParticleSimulation()
        sim.running = True
        
        fps_values = []
        frame_times = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sim.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        sim.running = False
            
            if not sim.running:
                break

            dt = sim.clock.tick(0) / 1000.0 # Use 0 to not cap FPS
            dt = max(dt, 0.0001) # Prevent division by zero
            frame_times.append(dt)
            
            sim.update(dt)
            sim.render()
        
        if not frame_times:
            return 0.0, {"message": "No frames rendered."}

        avg_dt = sum(frame_times) / len(frame_times)
        avg_fps = 1.0 / avg_dt
        return avg_fps, {}
        
    except Exception as e:
        print(f"Performance measurement failed: {e}", file=sys.stderr)
        return 0.0, {"error": str(e)}
    finally:
        if sim:
            sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    # Initialize Pygame once for all tests and measurements
    pygame.init()

    result = {
        "score": None,
        "metric_name": "FPS",
        "test_gate": False,
        "metrics": {},
        "message": ""
    }

    try:
        # Run functional tests
        tests_passed = run_functional_tests()
        result["test_gate"] = tests_passed
        
        if not tests_passed:
            result["message"] = "Functional tests failed."
            print(json.dumps(result))
            sys.exit(1)

        # Measure performance
        score, extra_metrics = measure_performance(duration=5)
        result["score"] = score
        result["metrics"].update(extra_metrics)
        
        if score > 0:
            result["message"] = f"All tests passed. Average FPS: {score:.2f}"
        else:
            result["test_gate"] = False # If score is 0, something went wrong
            result["message"] = "Performance measurement failed or returned 0 FPS."
            print(json.dumps(result))
            sys.exit(1)
            
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        result["score"] = None
        result["metric_name"] = "error"
        result["test_gate"] = False
        result["message"] = str(e)
        print(json.dumps(result))
        sys.exit(1)
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
