#!/usr/bin/env python3
"""Benchmark script for Volumetric Particle Simulation."""

import json
import sys
import os
import time

# Add current directory to sys.path to import particle_sim
sys.path.append(os.getcwd())

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
    """Run the simulation and return performance and functional metrics."""
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
        
        return avg_fps, stats, elapsed
    finally:
        sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    try:
        num_frames = 30
        avg_fps, stats, elapsed = run_benchmark(num_frames)
        
        # Functional tests
        tests = []
        
        # Test 1: Particle count
        expected_particles = 300 # From particle_sim.py NUM_PARTICLES
        tests.append(stats['num_particles'] == expected_particles)
        
        # Test 2: Particles in bounds
        # Most particles should be in bounds, but some might have just bounced or be slightly out
        tests.append(stats['particles_in_bounds'] > expected_particles * 0.8)
        
        # Test 3: Simulation is moving
        tests.append(stats['avg_particle_velocity'] > 0)
        
        # Test 4: Time progressed
        tests.append(stats['time'] > 0)

        test_gate = all(tests)
        
        result = {
            "score": avg_fps,
            "metric_name": "FPS",
            "test_gate": test_gate,
            "metrics": {
                "avg_fps": avg_fps,
                "elapsed_time": elapsed,
                "num_particles": stats['num_particles'],
                "particles_in_bounds": stats['particles_in_bounds'],
                "avg_particle_velocity": stats['avg_particle_velocity'],
                "sim_time": stats['time'],
                "tests_passed": sum(tests),
                "total_tests": len(tests)
            },
            "message": f"Average FPS: {avg_fps:.2f}. Functional tests: {'Passed' if test_gate else 'Failed'}"
        }
        
        if not quiet:
            print(json.dumps(result, indent=4))
        else:
            print(json.dumps(result))
            
        sys.exit(0 if test_gate else 1)
        
    except Exception as e:
        result = {
            "score": None,
            "metric_name": "FPS",
            "test_gate": False,
            "message": f"Error during benchmark: {str(e)}"
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
