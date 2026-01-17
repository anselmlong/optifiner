"""
Raymarching Demo Evaluator

This file is OUTSIDE the editable codebase - the agent cannot modify it.
It evaluates the raymarcher's performance (FPS) while ensuring correctness.

The score is the average FPS achieved over a test run.
Higher FPS = better optimization.

Validation tests ensure the optimization doesn't break the renderer.
"""

import pygame
import numpy as np
import sys
import time
import os
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass

# Add the current directory to path to import scene
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class ValidationResult:
    """Result of a validation test."""
    passed: bool
    message: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class EvaluationResult:
    """Complete evaluation result."""
    score: float  # FPS
    passed: bool
    validation_results: List[ValidationResult]
    frame_times: List[float]
    error: str = None


class RaymarcherEvaluator:
    """
    Evaluates the raymarching demo for performance and correctness.
    """
    
    # Expected color ranges for validation (RGB)
    # These are approximate ranges that should be present in a correctly rendered scene
    EXPECTED_COLORS = {
        'sky_blue': {'min': (50, 100, 150), 'max': (150, 200, 255)},
        'ground_brown': {'min': (80, 60, 40), 'max': (180, 160, 140)},
        'red_sphere': {'min': (150, 30, 30), 'max': (255, 120, 120)},
        'green_sphere': {'min': (30, 120, 40), 'max': (120, 255, 150)},
        'blue_sphere': {'min': (30, 50, 150), 'max': (120, 150, 255)},
    }
    
    # Minimum pixel count for each expected color region
    MIN_PIXELS_PER_COLOR = 50
    
    # Test parameters
    NUM_FRAMES = 10  # Number of frames to render for evaluation
    WARMUP_FRAMES = 2  # Frames to skip for warmup
    
    def __init__(self, width: int = 320, height: int = 240):
        self.width = width
        self.height = height
        self.screenshots: List[np.ndarray] = []
        self.frame_times: List[float] = []
    
    def capture_frame(self, surface: pygame.Surface) -> np.ndarray:
        """Capture a frame as numpy array."""
        return pygame.surfarray.array3d(surface).copy()
    
    def validate_no_crash(self) -> ValidationResult:
        """Test that the demo doesn't crash during rendering."""
        try:
            # Import fresh to test module loading
            import importlib
            import scene
            importlib.reload(scene)
            
            pygame.init()
            test_surface = pygame.display.set_mode((self.width, self.height))
            
            # Try rendering a single frame
            scene.render_frame(test_surface, 0.0)
            
            pygame.quit()
            return ValidationResult(True, "No crash during basic render")
        except Exception as e:
            return ValidationResult(False, f"Crash during render: {str(e)}")
    
    def validate_not_black(self, frame: np.ndarray) -> ValidationResult:
        """Validate that the frame is not entirely black."""
        mean_brightness = np.mean(frame)
        if mean_brightness < 5:
            return ValidationResult(
                False, 
                f"Frame is too dark (mean brightness: {mean_brightness:.2f})",
                {'mean_brightness': mean_brightness}
            )
        return ValidationResult(
            True, 
            f"Frame has content (mean brightness: {mean_brightness:.2f})",
            {'mean_brightness': mean_brightness}
        )
    
    def validate_not_white(self, frame: np.ndarray) -> ValidationResult:
        """Validate that the frame is not entirely white/overexposed."""
        mean_brightness = np.mean(frame)
        if mean_brightness > 250:
            return ValidationResult(
                False,
                f"Frame is overexposed (mean brightness: {mean_brightness:.2f})",
                {'mean_brightness': mean_brightness}
            )
        return ValidationResult(
            True,
            f"Frame not overexposed (mean brightness: {mean_brightness:.2f})",
            {'mean_brightness': mean_brightness}
        )
    
    def validate_color_diversity(self, frame: np.ndarray) -> ValidationResult:
        """Validate that the frame has sufficient color diversity."""
        # Calculate color variance
        r_var = np.var(frame[:, :, 0])
        g_var = np.var(frame[:, :, 1])
        b_var = np.var(frame[:, :, 2])
        total_var = r_var + g_var + b_var
        
        if total_var < 100:
            return ValidationResult(
                False,
                f"Frame lacks color diversity (variance: {total_var:.2f})",
                {'color_variance': total_var}
            )
        return ValidationResult(
            True,
            f"Frame has color diversity (variance: {total_var:.2f})",
            {'color_variance': total_var}
        )
    
    def validate_expected_colors(self, frame: np.ndarray) -> ValidationResult:
        """Validate that expected colors are present in the scene."""
        found_colors = {}
        missing_colors = []
        
        for color_name, ranges in self.EXPECTED_COLORS.items():
            min_rgb = np.array(ranges['min'])
            max_rgb = np.array(ranges['max'])
            
            # Count pixels in this color range
            mask = np.all((frame >= min_rgb) & (frame <= max_rgb), axis=2)
            pixel_count = np.sum(mask)
            found_colors[color_name] = pixel_count
            
            if pixel_count < self.MIN_PIXELS_PER_COLOR:
                missing_colors.append(color_name)
        
        if missing_colors:
            return ValidationResult(
                False,
                f"Missing expected colors: {missing_colors}",
                {'found_colors': found_colors, 'missing': missing_colors}
            )
        
        return ValidationResult(
            True,
            "All expected colors found",
            {'found_colors': found_colors}
        )
    
    def validate_temporal_consistency(self, frames: List[np.ndarray]) -> ValidationResult:
        """Validate that animation is smooth (frames are different but not too different)."""
        if len(frames) < 2:
            return ValidationResult(True, "Not enough frames for temporal check")
        
        differences = []
        for i in range(1, len(frames)):
            diff = np.mean(np.abs(frames[i].astype(float) - frames[i-1].astype(float)))
            differences.append(diff)
        
        avg_diff = np.mean(differences)
        max_diff = np.max(differences)
        
        # Check that frames are changing (animation is working)
        if avg_diff < 0.5:
            return ValidationResult(
                False,
                f"Animation appears frozen (avg frame diff: {avg_diff:.2f})",
                {'avg_diff': avg_diff, 'max_diff': max_diff}
            )
        
        # Check that changes aren't too drastic (no visual corruption)
        if max_diff > 100:
            return ValidationResult(
                False,
                f"Animation has sudden jumps (max frame diff: {max_diff:.2f})",
                {'avg_diff': avg_diff, 'max_diff': max_diff}
            )
        
        return ValidationResult(
            True,
            f"Animation is smooth (avg diff: {avg_diff:.2f})",
            {'avg_diff': avg_diff, 'max_diff': max_diff}
        )
    
    def validate_shadows_present(self, frame: np.ndarray) -> ValidationResult:
        """Validate that shadows are being rendered (luminance variation on ground)."""
        # Look at the lower portion of the frame (ground area)
        ground_region = frame[:, int(self.height * 0.6):, :]
        
        # Calculate luminance
        luminance = 0.299 * ground_region[:, :, 0] + \
                    0.587 * ground_region[:, :, 1] + \
                    0.114 * ground_region[:, :, 2]
        
        lum_variance = np.var(luminance)
        
        if lum_variance < 50:
            return ValidationResult(
                False,
                f"Ground lacks shadow variation (variance: {lum_variance:.2f})",
                {'luminance_variance': lum_variance}
            )
        
        return ValidationResult(
            True,
            f"Shadows appear present (variance: {lum_variance:.2f})",
            {'luminance_variance': lum_variance}
        )
    
    def validate_reflections_present(self, frames: List[np.ndarray]) -> ValidationResult:
        """Validate that reflections are working by checking for specular highlights."""
        if not frames:
            return ValidationResult(False, "No frames to check")
        
        # Look for very bright spots (specular highlights)
        bright_pixel_counts = []
        for frame in frames:
            luminance = 0.299 * frame[:, :, 0] + \
                        0.587 * frame[:, :, 1] + \
                        0.114 * frame[:, :, 2]
            bright_count = np.sum(luminance > 230)
            bright_pixel_counts.append(bright_count)
        
        avg_bright = np.mean(bright_pixel_counts)
        
        if avg_bright < 10:
            return ValidationResult(
                False,
                f"No specular highlights found (avg bright pixels: {avg_bright:.0f})",
                {'avg_bright_pixels': avg_bright}
            )
        
        return ValidationResult(
            True,
            f"Specular highlights present (avg bright pixels: {avg_bright:.0f})",
            {'avg_bright_pixels': avg_bright}
        )
    
    def run_performance_test(self) -> Tuple[float, List[np.ndarray], List[float]]:
        """
        Run the performance test and return (avg_fps, screenshots, frame_times).
        """
        import scene
        import importlib
        importlib.reload(scene)
        
        pygame.init()
        surface = pygame.display.set_mode((self.width, self.height))
        
        screenshots = []
        frame_times = []
        sim_time = 0.0
        time_step = 1/30.0
        
        total_frames = self.WARMUP_FRAMES + self.NUM_FRAMES
        
        for i in range(total_frames):
            # Handle pygame events to prevent hanging
            for event in pygame.event.get():
                pass
            
            frame_start = time.time()
            scene.render_frame(surface, sim_time)
            pygame.display.flip()
            frame_time = time.time() - frame_start
            
            # Only record after warmup
            if i >= self.WARMUP_FRAMES:
                frame_times.append(frame_time)
                # Capture some frames for validation
                if i % 2 == 0:
                    screenshots.append(self.capture_frame(surface))
            
            sim_time += time_step
        
        pygame.quit()
        
        # Calculate average FPS
        if frame_times:
            avg_frame_time = sum(frame_times) / len(frame_times)
            avg_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
        else:
            avg_fps = 0.0
        
        return avg_fps, screenshots, frame_times
    
    def evaluate(self) -> EvaluationResult:
        """
        Run full evaluation: performance test + validation.
        Returns EvaluationResult with score (FPS) and validation results.
        """
        validation_results = []
        
        # First, basic crash test
        crash_result = self.validate_no_crash()
        validation_results.append(crash_result)
        
        if not crash_result.passed:
            return EvaluationResult(
                score=0.0,
                passed=False,
                validation_results=validation_results,
                frame_times=[],
                error=crash_result.message
            )
        
        # Run performance test
        try:
            avg_fps, screenshots, frame_times = self.run_performance_test()
        except Exception as e:
            return EvaluationResult(
                score=0.0,
                passed=False,
                validation_results=validation_results,
                frame_times=[],
                error=f"Performance test failed: {str(e)}"
            )
        
        # Run validation tests on captured frames
        if screenshots:
            # Test first frame
            frame = screenshots[0]
            validation_results.append(self.validate_not_black(frame))
            validation_results.append(self.validate_not_white(frame))
            validation_results.append(self.validate_color_diversity(frame))
            validation_results.append(self.validate_expected_colors(frame))
            validation_results.append(self.validate_shadows_present(frame))
            
            # Test all frames
            validation_results.append(self.validate_temporal_consistency(screenshots))
            validation_results.append(self.validate_reflections_present(screenshots))
        
        # Check if all validations passed
        all_passed = all(r.passed for r in validation_results)
        
        return EvaluationResult(
            score=avg_fps if all_passed else 0.0,
            passed=all_passed,
            validation_results=validation_results,
            frame_times=frame_times
        )


def format_results(result: EvaluationResult) -> str:
    """Format evaluation results for display."""
    lines = []
    lines.append("=" * 60)
    lines.append("RAYMARCHER EVALUATION RESULTS")
    lines.append("=" * 60)
    
    if result.error:
        lines.append(f"\n❌ ERROR: {result.error}\n")
    
    lines.append("\nVALIDATION TESTS:")
    lines.append("-" * 40)
    
    for vr in result.validation_results:
        status = "✅" if vr.passed else "❌"
        lines.append(f"{status} {vr.message}")
    
    lines.append("\n" + "-" * 40)
    lines.append(f"All tests passed: {'Yes' if result.passed else 'No'}")
    
    if result.frame_times:
        lines.append(f"\nPERFORMANCE METRICS:")
        lines.append("-" * 40)
        lines.append(f"Frames rendered: {len(result.frame_times)}")
        lines.append(f"Min frame time: {min(result.frame_times)*1000:.1f}ms")
        lines.append(f"Max frame time: {max(result.frame_times)*1000:.1f}ms")
        lines.append(f"Avg frame time: {sum(result.frame_times)/len(result.frame_times)*1000:.1f}ms")
    
    lines.append("\n" + "=" * 60)
    lines.append(f"FINAL SCORE (FPS): {result.score:.2f}")
    lines.append("=" * 60)
    
    if not result.passed:
        lines.append("\n⚠️  Score is 0 because validation tests failed.")
        lines.append("   Fix the rendering issues to get a valid score.")
    
    return "\n".join(lines)


def main():
    """Run evaluation and print results."""
    print("Starting raymarcher evaluation...")
    print("This will render several frames and validate the output.\n")
    
    evaluator = RaymarcherEvaluator()
    result = evaluator.evaluate()
    
    print(format_results(result))
    
    return result.score


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score > 0 else 1)
