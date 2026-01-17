#!/usr/bin/env python3
"""Benchmark script for Volumetric Particle Simulation."""

import json
import sys
import time
import os

# Add current directory to sys.path
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
    
    # Initial stats
    initial_stats = get_simulation_stats(sim)
    
    try:
        # Run simulation
        avg_fps = sim.run(max_frames=num_frames)
        
        # Final stats
        final_stats = get_simulation_stats(sim)
        
        # Functional tests
        tests = []
        
        # 1. Particle count should be correct
        tests.append(final_stats['num_particles'] == 300) # NUM_PARTICLES = 300
        
        # 2. Simulation time should have progressed
        tests.append(final_stats['time'] > 0)
        
        # 3. Particles should be within bounds (mostly)
        # Since they bounce, they should stay within WORLD_BOUNDS
        # We allow a margin because collisions can push them out slightly
        # and the stats are taken after collisions but before the next update's bound check.
        tests.append(final_stats['particles_in_bounds'] >= 250) # Lenient check
        
        # 4. Average velocity should be non-zero (things are moving)
        tests.append(final_stats['avg_particle_velocity'] > 0)
        
        test_gate = all(tests)
        
        result = {
            "score": avg_fps,
            "metric_name": "FPS",
            "test_gate": test_gate,
            "metrics": {
                "avg_fps": avg_fps,
                "num_particles": final_stats['num_particles'],
                "particles_in_bounds": final_stats['particles_in_bounds'],
                "sim_time": final_stats['time'],
                "avg_velocity": final_stats['avg_particle_velocity']
            },
            "message": f"Benchmark completed. FPS: {avg_fps:.2f}, Tests: {'PASSED' if test_gate else 'FAILED'}"
        }
        
        return result
    finally:
        sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    try:
        result = run_benchmark()
        if not quiet:
            print(json.dumps(result, indent=4))
        else:
            print(json.dumps(result))
        
        sys.exit(0 if result["test_gate"] else 1)
        
    except Exception as e:
        error_result = {
            "score": None,
            "metric_name": "FPS",
            "test_gate": False,
            "message": f"Error during benchmark: {str(e)}"
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
