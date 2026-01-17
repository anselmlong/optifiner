#!/usr/bin/env python3
import json
import sys
import time
import os

# Add the workspace directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the particle_sim module
import particle_sim

def run_simulation_and_get_fps(duration=5):
    """Runs the particle simulation directly and captures FPS."""
    sim = particle_sim.ParticleSimulation(benchmark_mode=True)
    avg_fps = sim.run_benchmark(duration)
    sim.cleanup()

    if avg_fps > 0:
        return avg_fps, ""
    else:
        return 0.0, "No FPS values captured."

def run_functional_tests():
    """
    Runs a very short simulation to check if it starts and runs without immediate crashes.
    This is a basic smoke test.
    """
    try:
        # We'll run the simulation for a very short time (e.g., 1 second)
        # and check if it produces any FPS output.
        avg_fps, message = run_simulation_and_get_fps(duration=1)
        if avg_fps > 0:
            return True, "Simulation started and produced FPS output."
        else:
            return False, f"Simulation ran but produced no FPS or crashed: {message}"
    except Exception as e:
        return False, f"Functional test failed: {str(e)}"

def main():
    quiet = "--quiet" in sys.argv
    
    score = None
    metric_name = "FPS"
    test_gate = False
    metrics = {}
    message = "Benchmark failed."

    try:
        # Functional Test
        test_gate, test_message = run_functional_tests()
        metrics["functional_test_message"] = test_message
        
        if not test_gate:
            message = f"Functional test failed: {test_message}"
            print(json.dumps({
                "score": score,
                "metric_name": metric_name,
                "test_gate": test_gate,
                "metrics": metrics,
                "message": message
            }))
            sys.exit(1)

        # Performance Measurement
        avg_fps, perf_message = run_simulation_and_get_fps(duration=10) # Run for 10 seconds for performance
        score = avg_fps
        metrics["performance_measurement_message"] = perf_message

        if score > 0:
            message = f"Benchmark passed. Average FPS: {score:.2f}"
        else:
            test_gate = False # If no FPS, consider it a failure
            message = f"Benchmark failed: No FPS captured during performance run. {perf_message}"

        result = {
            "score": score,
            "metric_name": metric_name,
            "test_gate": test_gate,
            "metrics": metrics,
            "message": message
        }
        
        print(json.dumps(result))
        sys.exit(0 if test_gate and score is not None else 1)
        
    except Exception as e:
        result = {
            "score": None,
            "metric_name": metric_name,
            "test_gate": False,
            "message": f"An unexpected error occurred: {str(e)}"
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
