"""
Evaluator for the Volumetric Particle Simulation Optimization Task

This evaluator:
1. Runs the simulation for a fixed number of frames
2. Measures average FPS as the primary score
3. Runs correctness tests to ensure the simulation still works
4. Returns a composite score

The evaluator is OUTSIDE the fake codebase, so it cannot be modified by the agent.
The agent must optimize the code in volumetric_particle_sim/particle_sim.py
"""

import sys
import os
import time
import math
import importlib.util
from typing import Tuple, Dict, List, Any
from dataclasses import dataclass

# Add the parent directory to the path so we can import the simulation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class TestResult:
    """Result of a single test"""
    name: str
    passed: bool
    message: str
    

@dataclass
class EvaluationResult:
    """Complete evaluation result"""
    fps: float
    score: float
    tests_passed: int
    tests_total: int
    test_results: List[TestResult]
    error: str = None


def load_simulation_module():
    """Dynamically load the particle simulation module from workspace"""
    # When run from CLI, WORKSPACE_ROOT is set to the workspace directory
    # Otherwise, look relative to this file
    workspace = os.environ.get("WORKSPACE_ROOT")
    
    if workspace:
        # CLI mode: workspace IS the particle sim directory
        module_path = os.path.join(workspace, "particle_sim.py")
    else:
        # Direct execution: look relative to this file
        module_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "volumetric_particle_sim",
            "particle_sim.py"
        )
    
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"particle_sim.py not found at: {module_path}")
    
    spec = importlib.util.spec_from_file_location("particle_sim", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SimulationTester:
    """Tests to verify the simulation still works correctly after optimization"""
    
    def __init__(self, module):
        self.module = module
        self.results: List[TestResult] = []
        
    def run_all_tests(self) -> List[TestResult]:
        """Run all correctness tests"""
        self.results = []
        
        # Test 1: Module imports successfully
        self._test_module_imports()
        
        # Test 2: Simulation initializes
        sim = self._test_simulation_init()
        if sim is None:
            return self.results
            
        # Test 3: Particles exist and have valid properties
        self._test_particles_valid(sim)
        
        # Test 4: Lights exist and have valid properties
        self._test_lights_valid(sim)
        
        # Test 5: Physics update works
        self._test_physics_update(sim)
        
        # Test 6: Particles stay in bounds after update
        self._test_particles_in_bounds(sim)
        
        # Test 7: Collision detection doesn't crash
        self._test_collision_detection(sim)
        
        # Test 8: Rendering doesn't crash
        self._test_rendering(sim)
        
        # Test 9: Camera rotation changes
        self._test_camera_rotation(sim)
        
        # Test 10: get_simulation_stats works
        self._test_stats_function(sim)
        
        # Cleanup
        try:
            sim.cleanup()
        except:
            pass
            
        return self.results
    
    def _test_module_imports(self):
        """Test that required classes/functions exist"""
        required = [
            'ParticleSimulation',
            'Particle',
            'Light',
            'Vector3',
            'VolumetricRenderer',
            'get_simulation_stats',
            'NUM_PARTICLES',
            'NUM_LIGHTS',
            'WORLD_BOUNDS',
        ]
        
        missing = []
        for name in required:
            if not hasattr(self.module, name):
                missing.append(name)
        
        if missing:
            self.results.append(TestResult(
                name="Module imports",
                passed=False,
                message=f"Missing required exports: {', '.join(missing)}"
            ))
        else:
            self.results.append(TestResult(
                name="Module imports",
                passed=True,
                message="All required exports present"
            ))
    
    def _test_simulation_init(self):
        """Test that simulation initializes correctly"""
        try:
            sim = self.module.ParticleSimulation()
            self.results.append(TestResult(
                name="Simulation initialization",
                passed=True,
                message="ParticleSimulation created successfully"
            ))
            return sim
        except Exception as e:
            self.results.append(TestResult(
                name="Simulation initialization",
                passed=False,
                message=f"Failed to create ParticleSimulation: {e}"
            ))
            return None
    
    def _test_particles_valid(self, sim):
        """Test that particles have valid properties"""
        try:
            particles = sim.particles
            
            if len(particles) == 0:
                self.results.append(TestResult(
                    name="Particles valid",
                    passed=False,
                    message="No particles found"
                ))
                return
            
            # Check a sample of particles
            for i, p in enumerate(particles[:10]):
                # Check position is a Vector3-like object
                if not all(hasattr(p.position, attr) for attr in ['x', 'y', 'z']):
                    self.results.append(TestResult(
                        name="Particles valid",
                        passed=False,
                        message=f"Particle {i} position missing x, y, or z"
                    ))
                    return
                
                # Check velocity is a Vector3-like object
                if not all(hasattr(p.velocity, attr) for attr in ['x', 'y', 'z']):
                    self.results.append(TestResult(
                        name="Particles valid",
                        passed=False,
                        message=f"Particle {i} velocity missing x, y, or z"
                    ))
                    return
                
                # Check color is valid
                if not (isinstance(p.color, (tuple, list)) and len(p.color) >= 3):
                    self.results.append(TestResult(
                        name="Particles valid",
                        passed=False,
                        message=f"Particle {i} has invalid color"
                    ))
                    return
                
                # Check radius is positive
                if not (hasattr(p, 'radius') and p.radius > 0):
                    self.results.append(TestResult(
                        name="Particles valid",
                        passed=False,
                        message=f"Particle {i} has invalid radius"
                    ))
                    return
            
            self.results.append(TestResult(
                name="Particles valid",
                passed=True,
                message=f"{len(particles)} particles with valid properties"
            ))
        except Exception as e:
            self.results.append(TestResult(
                name="Particles valid",
                passed=False,
                message=f"Error checking particles: {e}"
            ))
    
    def _test_lights_valid(self, sim):
        """Test that lights have valid properties"""
        try:
            lights = sim.lights
            
            if len(lights) == 0:
                self.results.append(TestResult(
                    name="Lights valid",
                    passed=False,
                    message="No lights found"
                ))
                return
            
            for i, light in enumerate(lights):
                if not all(hasattr(light.position, attr) for attr in ['x', 'y', 'z']):
                    self.results.append(TestResult(
                        name="Lights valid",
                        passed=False,
                        message=f"Light {i} position missing x, y, or z"
                    ))
                    return
                
                if not hasattr(light, 'intensity') or light.intensity <= 0:
                    self.results.append(TestResult(
                        name="Lights valid",
                        passed=False,
                        message=f"Light {i} has invalid intensity"
                    ))
                    return
            
            self.results.append(TestResult(
                name="Lights valid",
                passed=True,
                message=f"{len(lights)} lights with valid properties"
            ))
        except Exception as e:
            self.results.append(TestResult(
                name="Lights valid",
                passed=False,
                message=f"Error checking lights: {e}"
            ))
    
    def _test_physics_update(self, sim):
        """Test that physics update modifies particle positions"""
        try:
            # Store initial positions
            initial_positions = [
                (p.position.x, p.position.y, p.position.z)
                for p in sim.particles[:10]
            ]
            
            # Run several updates
            for _ in range(10):
                sim.update(1/60)
            
            # Check that positions changed
            changed = 0
            for i, p in enumerate(sim.particles[:10]):
                if (p.position.x, p.position.y, p.position.z) != initial_positions[i]:
                    changed += 1
            
            if changed == 0:
                self.results.append(TestResult(
                    name="Physics update",
                    passed=False,
                    message="No particle positions changed after update"
                ))
            else:
                self.results.append(TestResult(
                    name="Physics update",
                    passed=True,
                    message=f"{changed}/10 sample particles moved"
                ))
        except Exception as e:
            self.results.append(TestResult(
                name="Physics update",
                passed=False,
                message=f"Error during physics update: {e}"
            ))
    
    def _test_particles_in_bounds(self, sim):
        """Test that particles stay within world bounds"""
        try:
            bounds = self.module.WORLD_BOUNDS
            out_of_bounds = 0
            
            for p in sim.particles:
                if (abs(p.position.x) > bounds * 1.1 or
                    abs(p.position.y) > bounds * 1.1 or
                    abs(p.position.z) > bounds * 1.1):
                    out_of_bounds += 1
            
            if out_of_bounds > len(sim.particles) * 0.1:
                self.results.append(TestResult(
                    name="Particles in bounds",
                    passed=False,
                    message=f"{out_of_bounds}/{len(sim.particles)} particles out of bounds"
                ))
            else:
                self.results.append(TestResult(
                    name="Particles in bounds",
                    passed=True,
                    message=f"Particles staying within bounds (tolerance: 10%)"
                ))
        except Exception as e:
            self.results.append(TestResult(
                name="Particles in bounds",
                passed=False,
                message=f"Error checking bounds: {e}"
            ))
    
    def _test_collision_detection(self, sim):
        """Test that collision detection runs without error"""
        try:
            sim.check_particle_collisions()
            self.results.append(TestResult(
                name="Collision detection",
                passed=True,
                message="Collision detection completed without error"
            ))
        except Exception as e:
            self.results.append(TestResult(
                name="Collision detection",
                passed=False,
                message=f"Collision detection error: {e}"
            ))
    
    def _test_rendering(self, sim):
        """Test that rendering functions don't crash"""
        try:
            # Test multiple frames of rendering
            for _ in range(5):
                sim.render()
            
            self.results.append(TestResult(
                name="Rendering",
                passed=True,
                message="Rendering completed without error"
            ))
        except Exception as e:
            self.results.append(TestResult(
                name="Rendering",
                passed=False,
                message=f"Rendering error: {e}"
            ))
    
    def _test_camera_rotation(self, sim):
        """Test that camera rotates over time"""
        try:
            initial_rotation = sim.camera_rotation
            
            for _ in range(10):
                sim.update(1/60)
            
            if sim.camera_rotation == initial_rotation:
                self.results.append(TestResult(
                    name="Camera rotation",
                    passed=False,
                    message="Camera rotation not changing"
                ))
            else:
                self.results.append(TestResult(
                    name="Camera rotation",
                    passed=True,
                    message=f"Camera rotating: {initial_rotation:.2f} -> {sim.camera_rotation:.2f}"
                ))
        except Exception as e:
            self.results.append(TestResult(
                name="Camera rotation",
                passed=False,
                message=f"Error checking camera rotation: {e}"
            ))
    
    def _test_stats_function(self, sim):
        """Test that get_simulation_stats returns valid data"""
        try:
            stats = self.module.get_simulation_stats(sim)
            
            required_keys = ['num_particles', 'num_lights', 'camera_rotation', 'time']
            missing = [k for k in required_keys if k not in stats]
            
            if missing:
                self.results.append(TestResult(
                    name="Stats function",
                    passed=False,
                    message=f"Missing stats keys: {', '.join(missing)}"
                ))
            else:
                self.results.append(TestResult(
                    name="Stats function",
                    passed=True,
                    message=f"Stats: {stats['num_particles']} particles, {stats['num_lights']} lights"
                ))
        except Exception as e:
            self.results.append(TestResult(
                name="Stats function",
                passed=False,
                message=f"Error getting stats: {e}"
            ))


def measure_fps(module, num_frames: int = 100, warmup_frames: int = 20) -> Tuple[float, str]:
    """
    Measure the FPS of the simulation.
    
    Args:
        module: The particle_sim module
        num_frames: Number of frames to measure
        warmup_frames: Frames to run before measuring (for JIT warmup)
    
    Returns:
        Tuple of (average_fps, error_message_or_none)
    """
    try:
        sim = module.ParticleSimulation()
        
        # Warmup
        for _ in range(warmup_frames):
            sim.update(1/60)
            sim.render()
        
        # Measure
        start_time = time.time()
        for _ in range(num_frames):
            sim.update(1/60)
            sim.render()
        elapsed = time.time() - start_time
        
        fps = num_frames / elapsed if elapsed > 0 else 0
        
        sim.cleanup()
        return fps, None
        
    except Exception as e:
        try:
            sim.cleanup()
        except:
            pass
        return 0.0, str(e)


def calculate_score(fps: float, tests_passed: int, tests_total: int) -> float:
    """
    Calculate the final score based on FPS and test results.
    
    The score is primarily FPS-based, but penalized if tests fail.
    
    Scoring:
    - Base score = FPS (higher is better)
    - If all tests pass: score = FPS
    - If some tests fail: score = FPS * (tests_passed / tests_total) * 0.5
    - If critical tests fail (< 50% pass): score = 0
    
    Returns:
        Final score (higher is better)
    """
    if tests_total == 0:
        return 0.0
    
    pass_ratio = tests_passed / tests_total
    
    if pass_ratio < 0.5:
        # Critical failure - too many tests failed
        return 0.0
    elif pass_ratio < 1.0:
        # Some tests failed - heavy penalty
        return fps * pass_ratio * 0.5
    else:
        # All tests passed - full FPS score
        return fps


def evaluate(num_frames: int = 150, verbose: bool = True) -> EvaluationResult:
    """
    Main evaluation function.
    
    Args:
        num_frames: Number of frames to measure for FPS
        verbose: Whether to print progress
    
    Returns:
        EvaluationResult with fps, score, and test results
    """
    if verbose:
        print("=" * 60)
        print("Volumetric Particle Simulation Evaluator")
        print("=" * 60)
        print()
    
    # Load the module
    if verbose:
        print("Loading simulation module...")
    try:
        module = load_simulation_module()
    except Exception as e:
        return EvaluationResult(
            fps=0.0,
            score=0.0,
            tests_passed=0,
            tests_total=0,
            test_results=[],
            error=f"Failed to load module: {e}"
        )
    
    # Run correctness tests
    if verbose:
        print("Running correctness tests...")
        print()
    
    tester = SimulationTester(module)
    test_results = tester.run_all_tests()
    
    tests_passed = sum(1 for r in test_results if r.passed)
    tests_total = len(test_results)
    
    if verbose:
        for result in test_results:
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.name}: {result.message}")
        print()
        print(f"Tests: {tests_passed}/{tests_total} passed")
        print()
    
    # Measure FPS
    if verbose:
        print(f"Measuring FPS ({num_frames} frames)...")
    
    fps, error = measure_fps(module, num_frames)
    
    if error:
        if verbose:
            print(f"Error during FPS measurement: {error}")
        return EvaluationResult(
            fps=0.0,
            score=0.0,
            tests_passed=tests_passed,
            tests_total=tests_total,
            test_results=test_results,
            error=error
        )
    
    if verbose:
        print(f"Average FPS: {fps:.2f}")
        print()
    
    # Calculate final score
    score = calculate_score(fps, tests_passed, tests_total)
    
    if verbose:
        print("=" * 60)
        print(f"FINAL SCORE: {score:.2f}")
        print("=" * 60)
        if tests_passed < tests_total:
            print(f"Note: Score penalized due to {tests_total - tests_passed} failed test(s)")
        print()
    
    return EvaluationResult(
        fps=fps,
        score=score,
        tests_passed=tests_passed,
        tests_total=tests_total,
        test_results=test_results
    )


def main():
    """CLI entry point"""
    import argparse
    import json as json_module
    
    parser = argparse.ArgumentParser(
        description="Evaluate the volumetric particle simulation"
    )
    parser.add_argument(
        "--frames", "-f", type=int, default=100,
        help="Number of frames to measure (default: 100)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress output, only print final score as JSON"
    )
    
    args = parser.parse_args()
    
    result = evaluate(num_frames=args.frames, verbose=not args.quiet)
    
    if args.quiet:
        # Output JSON for CLI parsing
        output = {
            "score": result.score,
            "fps": result.fps,
            "tests_passed": result.tests_passed,
            "tests_total": result.tests_total,
        }
        if result.error:
            output["error"] = result.error
        print(json_module.dumps(output))
    
    # Return non-zero exit code if evaluation failed
    if result.error or result.tests_passed < result.tests_total * 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()
