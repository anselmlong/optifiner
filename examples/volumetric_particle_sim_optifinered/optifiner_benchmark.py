#!/usr/bin/env python3
"""Benchmark script for Volumetric 3D Particle Simulation."""

import json
import sys
import time
import os

# Add the parent directory to the path to import particle_sim
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import particle_sim
except ImportError:
    # Fallback for when the script is run directly from the workspace root
    sys.path.insert(0, os.getcwd())
    import particle_sim


def run_tests():
    """Run functional tests to verify the application works."""
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Basic initialization
    tests_total += 1
    try:
        sim = particle_sim.ParticleSimulation()
        if sim is not None:
            tests_passed += 1
        sim.cleanup()
    except Exception as e:
        print(f"Test 1 (Initialization) failed: {e}", file=sys.stderr)
    
    # Test 2: Particle count
    tests_total += 1
    try:
        sim = particle_sim.ParticleSimulation()
        if len(sim.particles) == particle_sim.NUM_PARTICLES:
            tests_passed += 1
        else:
            print(f"Test 2 (Particle Count) failed: Expected {particle_sim.NUM_PARTICLES}, got {len(sim.particles)}", file=sys.stderr)
        sim.cleanup()
    except Exception as e:
        print(f"Test 2 (Particle Count) failed: {e}", file=sys.stderr)

    return tests_passed, tests_total

def measure_performance():
    """Measure the primary performance metric (FPS)."""
    benchmark_frames = 60  # Run for 60 frames for benchmarking
    
    sim = None
    try:
        sim = particle_sim.ParticleSimulation()
        sim.run(benchmark_frames=benchmark_frames)
        
        # The FPS is updated in particle_sim.py, so we can just retrieve it
        score = particle_sim.get_fps()
        
        return score, {}
    except Exception as e:
        print(f"Performance measurement failed: {e}", file=sys.stderr)
        return None, {}
    finally:
        if sim:
            sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    try:
        tests_passed, tests_total = run_tests()
        score, extra_metrics = measure_performance()
        
        result = {
            "score": score,
            "metric_name": "FPS",
            "test_gate": tests_passed == tests_total,
            "metrics": {
                "tests_passed": tests_passed,
                "tests_total": tests_total,
                **extra_metrics
            },
            "message": f"Score: {score:.2f} FPS, Tests: {tests_passed}/{tests_total} passed"
        }
        
        print(json.dumps(result))
        sys.exit(0 if result["test_gate"] and result["score"] is not None else 1)
        
    except Exception as e:
        result = {
            "score": None,
            "metric_name": "error",
            "test_gate": False,
            "message": str(e)
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
