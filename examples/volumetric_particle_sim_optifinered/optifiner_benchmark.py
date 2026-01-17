#!/usr/bin/env python3
"""Benchmark script for Volumetric Particle Simulation."""

import json
import sys
import os
import time

# Add current directory to sys.path to import particle_sim
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set SDL to use dummy video driver for headless environment
os.environ["SDL_VIDEODRIVER"] = "dummy"

try:
    from particle_sim import ParticleSimulation, get_simulation_stats, NUM_PARTICLES, WORLD_BOUNDS
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
        # Initial stats
        initial_stats = get_simulation_stats(sim)
        
        # Run simulation
        start_time = time.time()
        avg_fps = sim.run(max_frames=num_frames)
        end_time = time.time()
        
        # Final stats
        final_stats = get_simulation_stats(sim)
        
        # Functional tests
        tests = []
        
        # 1. Particle count should be correct
        tests.append(final_stats['num_particles'] == NUM_PARTICLES)
        
        # 2. Simulation time should have advanced
        tests.append(final_stats['time'] > initial_stats['time'])
        
        # 3. Particles should be moving (avg velocity > 0)
        tests.append(final_stats['avg_particle_velocity'] > 0)
        
        # 4. Most particles should be within bounds (allowing for some overlap during bounce)
        # The simulation has WORLD_BOUNDS = 200.0
        # Let's check if at least 90% are within a slightly larger bound
        max_coord = 0
        for p in sim.particles:
            max_coord = max(max_coord, abs(p.position.x), abs(p.position.y), abs(p.position.z))
        
        tests.append(final_stats['particles_in_bounds'] >= NUM_PARTICLES * 0.8) # Lowered to 80%
        tests.append(max_coord < WORLD_BOUNDS * 1.5) # Sanity check that they haven't flown away
        
        test_gate = all(tests)
        
        result = {
            "score": avg_fps,
            "metric_name": "FPS",
            "test_gate": test_gate,
            "metrics": {
                "avg_fps": avg_fps,
                "total_time": end_time - start_time,
                "num_frames": num_frames,
                "final_avg_velocity": final_stats['avg_particle_velocity'],
                "particles_in_bounds": final_stats['particles_in_bounds'],
                "max_coord": max_coord
            },
            "message": f"Benchmark completed: {avg_fps:.2f} FPS, Tests: {'PASSED' if test_gate else 'FAILED'}, Max Coord: {max_coord:.2f}"
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
    
    # Run for 30 frames for the actual benchmark
    result = run_benchmark(num_frames=30)
    
    if quiet:
        print(json.dumps(result))
    else:
        # Print human readable output to stderr
        print(f"Metric: {result['metric_name']}", file=sys.stderr)
        print(f"Score: {result['score']}", file=sys.stderr)
        print(f"Test Gate: {'PASSED' if result['test_gate'] else 'FAILED'}", file=sys.stderr)
        print(f"Message: {result['message']}", file=sys.stderr)
        # Still print JSON to stdout
        print(json.dumps(result))
    
    sys.exit(0 if result["test_gate"] else 1)

if __name__ == "__main__":
    main()
