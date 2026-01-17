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
    
    # Initial stats
    initial_stats = get_simulation_stats(sim)
    
    try:
        # Run simulation
        avg_fps = sim.run(max_frames=num_frames)
        
        # Final stats
        final_stats = get_simulation_stats(sim)
        
        # Functional tests
        tests = []
        
        # 1. Particle count should be constant
        tests.append(final_stats['num_particles'] == initial_stats['num_particles'])
        
        # 2. Simulation time should have progressed
        tests.append(final_stats['time'] > initial_stats['time'])
        
        # 3. Particles should be moving (avg velocity > 0)
        tests.append(final_stats['avg_particle_velocity'] > 0)
        
        # 4. Most particles should be within bounds (allowing for some bounce overlap)
        # The simulation has WORLD_BOUNDS = 200.0
        # Collision resolution can push particles slightly out of bounds.
        # We'll check with a 10% tolerance.
        particles_in_relaxed_bounds = sum(
            1 for p in sim.particles 
            if abs(p.position.x) <= 220.0 and
               abs(p.position.y) <= 220.0 and
               abs(p.position.z) <= 220.0
        )
        tests.append(particles_in_relaxed_bounds == initial_stats['num_particles'])
        
        test_gate = all(tests)
        
        result = {
            "score": avg_fps,
            "metric_name": "FPS",
            "test_gate": test_gate,
            "metrics": {
                "avg_fps": avg_fps,
                "num_particles": final_stats['num_particles'],
                "sim_time": final_stats['time'],
                "avg_velocity": final_stats['avg_particle_velocity'],
                "particles_in_bounds": final_stats['particles_in_bounds']
            },
            "message": f"Benchmark completed. FPS: {avg_fps:.2f}, Tests: {'PASSED' if test_gate else 'FAILED'}"
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
    
    result = run_benchmark()
    
    if quiet:
        print(json.dumps(result))
    else:
        # Print human readable output to stderr
        print(f"Metric: {result['metric_name']}", file=sys.stderr)
        print(f"Score: {result['score']}", file=sys.stderr)
        print(f"Test Gate: {'PASSED' if result['test_gate'] else 'FAILED'}", file=sys.stderr)
        if 'metrics' in result:
            print("Additional Metrics:", file=sys.stderr)
            for k, v in result['metrics'].items():
                print(f"  {k}: {v}", file=sys.stderr)
        print(f"Message: {result['message']}", file=sys.stderr)
        
        # Still print JSON to stdout as required
        print(json.dumps(result))

    sys.exit(0 if result["test_gate"] and result["score"] is not None else 1)

if __name__ == "__main__":
    main()
