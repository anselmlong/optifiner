#!/usr/bin/env python3
"""Benchmark script for Volumetric Particle Simulation."""

import json
import sys
import os
import time

# Add current directory to path so we can import particle_sim
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set SDL to use dummy video driver for headless environment
os.environ["SDL_VIDEODRIVER"] = "dummy"

try:
    from particle_sim import ParticleSimulation, get_simulation_stats
except ImportError as e:
    print(json.dumps({
        "score": None,
        "metric_name": "FPS",
        "test_gate": False,
        "message": f"Failed to import particle_sim: {e}"
    }))
    sys.exit(1)

def run_benchmark(num_frames=30):
    """Run the simulation and measure performance and correctness."""
    sim = ParticleSimulation()
    try:
        # Run for a few frames to warm up
        sim.run(max_frames=5)
        
        # Measure performance
        start_time = time.time()
        avg_fps = sim.run(max_frames=num_frames)
        elapsed = time.time() - start_time
        
        # Get stats for functional testing
        stats = get_simulation_stats(sim)
        
        # Functional tests
        tests = {
            "correct_particle_count": stats['num_particles'] == 300,
            "correct_light_count": stats['num_lights'] == 4,
            "particles_moving": stats['avg_particle_velocity'] > 0,
            "simulation_time_progressed": stats['time'] > 0,
            "particles_mostly_in_bounds": stats['particles_in_bounds'] > 200 # Most should be in bounds
        }
        
        test_gate = all(tests.values())
        
        result = {
            "score": avg_fps,
            "metric_name": "FPS",
            "test_gate": test_gate,
            "metrics": {
                "avg_fps": avg_fps,
                "elapsed_time": elapsed,
                "num_particles": stats['num_particles'],
                "avg_velocity": stats['avg_particle_velocity'],
                "particles_in_bounds": stats['particles_in_bounds'],
                **tests
            },
            "message": f"Average FPS: {avg_fps:.2f}. All tests passed: {test_gate}"
        }
        
        return result
    except Exception as e:
        return {
            "score": None,
            "metric_name": "FPS",
            "test_gate": False,
            "message": f"Error during benchmark: {e}"
        }
    finally:
        sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    result = run_benchmark(num_frames=30)
    
    if quiet:
        print(json.dumps(result))
    else:
        # Print human readable output to stderr
        print(f"Benchmark Result: {result['message']}", file=sys.stderr)
        print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["test_gate"] else 1)

if __name__ == "__main__":
    main()
