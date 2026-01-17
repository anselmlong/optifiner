#!/usr/bin/env python3
import json
import sys
import os
import time

# Add the current directory to sys.path so we can import particle_sim
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import pygame
    from particle_sim import ParticleSimulation, SCREEN_WIDTH, SCREEN_HEIGHT, NUM_PARTICLES
except ImportError as e:
    print(json.dumps({
        "score": None,
        "metric_name": "FPS",
        "test_gate": False,
        "message": f"Import error: {e}"
    }))
    sys.exit(1)

def run_benchmark():
    # Set dummy video driver for headless environment
    if os.environ.get('SDL_VIDEODRIVER') is None and not os.environ.get('DISPLAY'):
        os.environ['SDL_VIDEODRIVER'] = 'dummy'

    try:
        sim = ParticleSimulation()
        
        # Functional tests
        test_gate = True
        messages = []
        
        if len(sim.particles) != NUM_PARTICLES:
            test_gate = False
            messages.append(f"Expected {NUM_PARTICLES} particles, got {len(sim.particles)}")
        
        # Run for a few frames to measure performance
        # Given it's "deliberately unoptimized", we'll run for 5 frames
        num_frames = 5
        sim.run(max_frames=num_frames)
        
        fps = sim.fps
        
        # Check if particles moved
        if num_frames > 0:
            # We can't easily check movement without storing initial state, 
            # but we can check if sim.time increased
            if sim.time <= 0:
                test_gate = False
                messages.append("Simulation time did not increase")
        
        sim.cleanup()
        
        if test_gate:
            message = f"Benchmark completed: {fps:.2f} FPS"
        else:
            message = "Functional tests failed: " + "; ".join(messages)
            
        return {
            "score": fps,
            "metric_name": "FPS",
            "test_gate": test_gate,
            "metrics": {
                "frames": num_frames,
                "total_time": sim.time,
                "particle_count": len(sim.particles)
            },
            "message": message
        }
    except Exception as e:
        return {
            "score": None,
            "metric_name": "FPS",
            "test_gate": False,
            "message": f"Error during benchmark: {e}"
        }

if __name__ == "__main__":
    result = run_benchmark()
    print(json.dumps(result))
    if result["test_gate"] and result["score"] is not None:
        sys.exit(0)
    else:
        sys.exit(1)
