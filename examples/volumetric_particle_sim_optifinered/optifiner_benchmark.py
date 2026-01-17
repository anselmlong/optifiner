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
    """Run the simulation and measure performance."""
    sim = ParticleSimulation()
    try:
        # Warm up
        sim.run(max_frames=5)
        
        # Measure
        start_time = time.time()
        avg_fps = sim.run(max_frames=num_frames)
        end_time = time.time()
        
        stats = get_simulation_stats(sim)
        
        return avg_fps, stats
    finally:
        sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    try:
        # Run benchmark
        avg_fps, stats = run_benchmark(num_frames=30)
        
        # Functional tests
        tests = {
            "correct_particle_count": stats['num_particles'] == 300,
            "correct_light_count": stats['num_lights'] == 4,
            "particles_moving": stats['avg_particle_velocity'] > 0,
            "particles_mostly_in_bounds": stats['particles_in_bounds'] > 250 # Some might be slightly out during collision resolution
        }
        
        test_gate = all(tests.values())
        
        result = {
            "score": avg_fps,
            "metric_name": "FPS",
            "test_gate": test_gate,
            "metrics": {
                "avg_fps": avg_fps,
                "num_particles": stats['num_particles'],
                "avg_velocity": stats['avg_particle_velocity'],
                "particles_in_bounds": stats['particles_in_bounds'],
                **tests
            },
            "message": f"Average FPS: {avg_fps:.2f}. All tests passed: {test_gate}"
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
