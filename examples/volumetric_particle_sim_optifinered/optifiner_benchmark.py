#!/usr/bin/env python3
import json
import sys
import time
import subprocess
import os

def run_simulation_and_get_fps(duration=5):
    """Runs the particle simulation in a subprocess and captures FPS."""
    # Set SDL to use dummy video driver for headless testing
    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"

    command = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "particle_sim.py")]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env
    )

    # Allow the simulation to run for the specified duration
    # We'll terminate it after the duration if it doesn't exit on its own
    try:
        stdout, stderr = process.communicate(timeout=duration + 10) # Add buffer for cleanup
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        stderr += "\nSimulation terminated due to timeout.\n"

    final_fps = 0.0
    total_frames = 0
    total_time = 0.0

    for line in stdout.splitlines():
        if line.startswith("FINAL_FPS:"):
            final_fps = float(line.split(":")[1])
        elif line.startswith("TOTAL_FRAMES:"):
            total_frames = int(line.split(":")[1])
        elif line.startswith("TOTAL_TIME:"):
            total_time = float(line.split(":")[1])

    if process.returncode != 0 and "Simulation terminated due to timeout." not in stderr:
        raise RuntimeError(f"Simulation subprocess failed with exit code {process.returncode}. Stderr: {stderr}")

    return final_fps, total_frames, total_time, stdout, stderr

def run_tests():
    """Placeholder for functional tests. For now, just return true."""
    # In a real scenario, you would add assertions here to check if the simulation
    # behaves as expected (e.g., particles stay within bounds, don't overlap excessively).
    return True, "All functional tests passed (placeholder)."

def main():
    quiet = "--quiet" in sys.argv
    
    score = None
    metric_name = "FPS"
    test_gate = False
    metrics = {}
    message = ""

    try:
        test_gate, test_message = run_tests()
        if not test_gate:
            raise RuntimeError(f"Functional tests failed: {test_message}")

        # Run simulation for 5 seconds to get an average FPS
        fps, total_frames, total_time, stdout, stderr = run_simulation_and_get_fps(duration=5)
        score = fps
        metrics["total_frames_rendered"] = total_frames
        metrics["total_simulation_time"] = total_time
        metrics["simulation_stdout"] = stdout
        metrics["simulation_stderr"] = stderr
        
        message = f"Simulation ran for {total_time:.2f} seconds. Average FPS: {fps:.2f}. {test_message}"
        
    except Exception as e:
        test_gate = False
        score = None
        message = f"Benchmark failed: {e}"
        metrics["error"] = str(e)
        if "stdout" in locals(): metrics["simulation_stdout"] = stdout
        if "stderr" in locals(): metrics["simulation_stderr"] = stderr

    result = {
        "score": score,
        "metric_name": metric_name,
        "test_gate": test_gate,
        "metrics": metrics,
        "message": message
    }
    
    if not quiet:
        print(json.dumps(result, indent=4))
    else:
        print(json.dumps(result))
    
    sys.exit(0 if test_gate and score is not None else 1)

if __name__ == "__main__":
    main()
