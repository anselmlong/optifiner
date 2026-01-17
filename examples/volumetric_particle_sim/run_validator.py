#!/usr/bin/env python3
"""Benchmark and test script for Volumetric Particle Simulation."""

import json
import sys
import time
import os

# Add current directory to path so we can import particle_sim
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import pygame
    from particle_sim import ParticleSimulation, get_simulation_stats
except ImportError as e:
    print(json.dumps({
        "score": 0,
        "passed": False,
        "error": f"Failed to import dependencies: {e}"
    }))
    sys.exit(1)

def run_functional_tests():
    """Run functional tests to verify the application works."""
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Initialization
    tests_total += 1
    try:
        sim = ParticleSimulation()
        stats = get_simulation_stats(sim)
        if stats['num_particles'] > 0:
            tests_passed += 1
        else:
            print("Test 1 failed: No particles initialized", file=sys.stderr)
        sim.cleanup()
    except Exception as e:
        print(f"Test 1 failed: {e}", file=sys.stderr)
    
    # Test 2: Physics update and bounds
    tests_total += 1
    try:
        sim = ParticleSimulation()
        initial_stats = get_simulation_stats(sim)
        
        # Run for a few frames
        sim.run(max_frames=20, target_fps=0)
        
        final_stats = get_simulation_stats(sim)
        
        # Check if time has advanced and particles have moved
        time_advanced = final_stats['time'] > 0
        particles_moved = final_stats['avg_particle_velocity'] > 0
        particles_in_bounds = final_stats['particles_in_bounds'] == final_stats['num_particles']
        particle_count_consistent = final_stats['num_particles'] == initial_stats['num_particles']
        
        if time_advanced and particles_moved and particles_in_bounds and particle_count_consistent:
            tests_passed += 1
        else:
            print(f"Test 2 failed: Simulation state invalid. Time+: {time_advanced}, Moved: {particles_moved}, InBounds: {particles_in_bounds}, Count: {particle_count_consistent}", file=sys.stderr)
        sim.cleanup()
    except Exception as e:
        print(f"Test 2 failed: {e}", file=sys.stderr)

    # Test 3: Rendering (smoke test)
    tests_total += 1
    try:
        sim = ParticleSimulation()
        # Just see if it can render one frame without crashing
        sim.run(max_frames=1, target_fps=0)
        tests_passed += 1
        sim.cleanup()
    except Exception as e:
        print(f"Test 3 failed: {e}", file=sys.stderr)
    
    return tests_passed, tests_total

def measure_performance():
    """Measure the primary performance metric (FPS)."""
    # Run for more frames to get a stable measurement
    # Given the "intentionally slow" nature, 50 frames might be enough
    NUM_BENCHMARK_FRAMES = 50
    
    sim = ParticleSimulation()
    try:
        # Run with target_fps=0 for maximum performance
        avg_fps = sim.run(max_frames=NUM_BENCHMARK_FRAMES, target_fps=0)
        
        # Also measure memory usage if possible
        import psutil
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / (1024 * 1024)
        
        metrics = {
            "fps": avg_fps,
            "memory_mb": memory_mb,
            "num_particles": len(sim.particles),
            "frames_measured": NUM_BENCHMARK_FRAMES
        }
        return avg_fps, metrics
    finally:
        sim.cleanup()

def main():
    quiet = "--quiet" in sys.argv
    
    # Set SDL to use dummy video driver for headless environment
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    
    try:
        tests_passed, tests_total = run_functional_tests()
        score, metrics = measure_performance()
        
        passed = (tests_passed == tests_total)
        
        result = {
            "score": score,
            "passed": passed,
            "tests_passed": tests_passed,
            "tests_total": tests_total,
            "metrics": metrics,
            "message": f"FPS: {score:.2f}, Tests: {tests_passed}/{tests_total}"
        }
        
        if not quiet:
            print(json.dumps(result, indent=4))
        else:
            print(json.dumps(result))
            
        sys.exit(0 if passed else 1)
        
    except Exception as e:
        result = {
            "score": 0,
            "passed": False,
            "error": str(e)
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
