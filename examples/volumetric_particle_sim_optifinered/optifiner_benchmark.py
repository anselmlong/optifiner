#!/usr/bin/env python3
import json
import sys
import time
import os

# Add the workspace directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the simulation directly
try:
    from particle_sim import ParticleSimulation
except ImportError as e:
    print(f"Error importing particle_sim: {e}", file=sys.stderr)
    sys.exit(1)

def run_headless_benchmark_test(frames_to_run: int) -> float:
    """Runs the simulation in headless mode and returns average FPS."""
    sim = ParticleSimulation()
    try:
        avg_fps = sim.run_headless_benchmark(frames_to_run)
        return avg_fps
    except Exception as e:
        print(f"Error during headless benchmark run: {e}", file=sys.stderr)
        return 0.0

def run_functional_tests():
    """
    Runs a very short headless simulation to check if it starts and runs without immediate crashes.
    This is a basic smoke test.
    """
    try:
        # Run for a very small number of frames (e.g., 10 frames)
        avg_fps = run_headless_benchmark_test(frames_to_run=10)
        if avg_fps > 0:
            return True, "Headless simulation started and produced FPS output."
        else:
            return False, "Headless simulation ran but produced no FPS or crashed."
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
        # Run for a reasonable number of frames for performance measurement
        avg_fps = run_headless_benchmark_test(frames_to_run=300) # Run for 300 frames
        score = avg_fps

        if score > 0:
            message = f"Benchmark passed. Average FPS: {score:.2f}"
        else:
            test_gate = False # If no FPS, consider it a failure
            message = "Benchmark failed: No FPS captured during performance run."

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
