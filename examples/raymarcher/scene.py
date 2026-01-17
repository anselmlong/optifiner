"""
Raymarching Demo - A heavily unoptimized 3D raymarching renderer in pygame.

This renders a scene with multiple objects, soft shadows, ambient occlusion,
and reflections using signed distance functions (SDFs). The code is intentionally
written in an unoptimized way to provide optimization opportunities.

The goal is to optimize this code to achieve higher FPS while maintaining
visual correctness.
"""

import pygame
import numpy as np
import math
import time
from typing import Tuple, List, Optional

# Configuration
WIDTH = 320
HEIGHT = 240
MAX_STEPS = 100
MAX_DIST = 100.0
SURF_DIST = 0.001
SHADOW_SOFTNESS = 8.0
AO_STEPS = 5
AO_STEP_SIZE = 0.1
REFLECTION_BOUNCES = 2


class Vec3:
    """A simple 3D vector class - intentionally not using numpy for per-vector ops."""
    
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
    
    def __add__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vec3':
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __rmul__(self, scalar: float) -> 'Vec3':
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar: float) -> 'Vec3':
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)
    
    def __neg__(self) -> 'Vec3':
        return Vec3(-self.x, -self.y, -self.z)
    
    def dot(self, other: 'Vec3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vec3') -> 'Vec3':
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    
    def normalize(self) -> 'Vec3':
        l = self.length()
        if l > 0:
            return self / l
        return Vec3(0, 0, 0)
    
    def abs(self) -> 'Vec3':
        return Vec3(abs(self.x), abs(self.y), abs(self.z))
    
    def max_component(self) -> float:
        return max(self.x, self.y, self.z)
    
    def min_component(self) -> float:
        return min(self.x, self.y, self.z)
    
    def clamp(self, min_val: float, max_val: float) -> 'Vec3':
        return Vec3(
            max(min_val, min(max_val, self.x)),
            max(min_val, min(max_val, self.y)),
            max(min_val, min(max_val, self.z))
        )
    
    def reflect(self, normal: 'Vec3') -> 'Vec3':
        return self - normal * 2.0 * self.dot(normal)
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    def copy(self) -> 'Vec3':
        return Vec3(self.x, self.y, self.z)


class Material:
    """Material properties for objects."""
    
    def __init__(self, color: Vec3, reflectivity: float = 0.0, 
                 shininess: float = 32.0, emission: float = 0.0):
        self.color = color
        self.reflectivity = reflectivity
        self.shininess = shininess
        self.emission = emission


# Scene objects with materials
MATERIALS = {
    'ground': Material(Vec3(0.4, 0.35, 0.3), reflectivity=0.1),
    'sphere1': Material(Vec3(0.8, 0.2, 0.2), reflectivity=0.5, shininess=64.0),
    'sphere2': Material(Vec3(0.2, 0.8, 0.3), reflectivity=0.3, shininess=32.0),
    'sphere3': Material(Vec3(0.2, 0.3, 0.9), reflectivity=0.4, shininess=48.0),
    'box': Material(Vec3(0.9, 0.7, 0.2), reflectivity=0.2, shininess=16.0),
    'torus': Material(Vec3(0.8, 0.4, 0.8), reflectivity=0.6, shininess=128.0),
}


def sdf_sphere(p: Vec3, center: Vec3, radius: float) -> float:
    """Signed distance function for a sphere."""
    return (p - center).length() - radius


def sdf_box(p: Vec3, center: Vec3, size: Vec3) -> float:
    """Signed distance function for a box."""
    q = (p - center).abs() - size
    return Vec3(max(q.x, 0), max(q.y, 0), max(q.z, 0)).length() + min(q.max_component(), 0)


def sdf_plane(p: Vec3, normal: Vec3, height: float) -> float:
    """Signed distance function for an infinite plane."""
    return p.dot(normal) - height


def sdf_torus(p: Vec3, center: Vec3, radius_major: float, radius_minor: float) -> float:
    """Signed distance function for a torus aligned with Y axis."""
    p_local = p - center
    q_x = math.sqrt(p_local.x * p_local.x + p_local.z * p_local.z) - radius_major
    q_y = p_local.y
    return math.sqrt(q_x * q_x + q_y * q_y) - radius_minor


def smooth_min(a: float, b: float, k: float) -> float:
    """Smooth minimum for blending SDFs."""
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


def scene_sdf(p: Vec3, time_val: float) -> Tuple[float, str]:
    """
    Compute the signed distance to the scene and return material ID.
    This is intentionally computing each object separately without optimization.
    """
    # Animated positions
    bounce1 = math.sin(time_val * 2.0) * 0.3
    bounce2 = math.sin(time_val * 2.5 + 1.0) * 0.25
    bounce3 = math.sin(time_val * 1.8 + 2.0) * 0.35
    rotate_angle = time_val * 0.5
    
    # Ground plane
    d_ground = sdf_plane(p, Vec3(0, 1, 0), 0)
    
    # Spheres with animation
    d_sphere1 = sdf_sphere(p, Vec3(-2, 1 + bounce1, 0), 1.0)
    d_sphere2 = sdf_sphere(p, Vec3(0, 0.7 + bounce2, 2), 0.7)
    d_sphere3 = sdf_sphere(p, Vec3(2.5, 0.5 + bounce3, -1), 0.5)
    
    # Rotating box
    box_center = Vec3(1.5, 0.8, 1.5)
    cos_r = math.cos(rotate_angle)
    sin_r = math.sin(rotate_angle)
    p_rotated = Vec3(
        (p.x - box_center.x) * cos_r - (p.z - box_center.z) * sin_r + box_center.x,
        p.y,
        (p.x - box_center.x) * sin_r + (p.z - box_center.z) * cos_r + box_center.z
    )
    d_box = sdf_box(p_rotated, box_center, Vec3(0.6, 0.6, 0.6))
    
    # Torus
    d_torus = sdf_torus(p, Vec3(-1, 0.5, -2), 0.6, 0.2)
    
    # Find minimum distance and corresponding material
    # Intentionally not using a more efficient approach
    distances = [
        (d_ground, 'ground'),
        (d_sphere1, 'sphere1'),
        (d_sphere2, 'sphere2'),
        (d_sphere3, 'sphere3'),
        (d_box, 'box'),
        (d_torus, 'torus'),
    ]
    
    min_dist = float('inf')
    material_id = 'ground'
    for d, mat in distances:
        if d < min_dist:
            min_dist = d
            material_id = mat
    
    return min_dist, material_id


def scene_sdf_only(p: Vec3, time_val: float) -> float:
    """Get just the distance, without material info."""
    dist, _ = scene_sdf(p, time_val)
    return dist


def get_normal(p: Vec3, time_val: float) -> Vec3:
    """
    Calculate surface normal using central differences.
    Intentionally using small epsilon and multiple SDF evaluations.
    """
    eps = 0.0001
    
    # Intentionally computing each component separately
    dx = scene_sdf_only(Vec3(p.x + eps, p.y, p.z), time_val) - \
         scene_sdf_only(Vec3(p.x - eps, p.y, p.z), time_val)
    dy = scene_sdf_only(Vec3(p.x, p.y + eps, p.z), time_val) - \
         scene_sdf_only(Vec3(p.x, p.y - eps, p.z), time_val)
    dz = scene_sdf_only(Vec3(p.x, p.y, p.z + eps), time_val) - \
         scene_sdf_only(Vec3(p.x, p.y, p.z - eps), time_val)
    
    return Vec3(dx, dy, dz).normalize()


def ray_march(origin: Vec3, direction: Vec3, time_val: float) -> Tuple[float, str]:
    """
    March a ray through the scene.
    Returns (distance, material_id) or (MAX_DIST, None) if no hit.
    """
    total_dist = 0.0
    
    for _ in range(MAX_STEPS):
        p = origin + direction * total_dist
        dist, material_id = scene_sdf(p, time_val)
        
        if dist < SURF_DIST:
            return total_dist, material_id
        
        total_dist += dist
        
        if total_dist > MAX_DIST:
            break
    
    return MAX_DIST, None


def calculate_soft_shadow(origin: Vec3, light_dir: Vec3, time_val: float) -> float:
    """
    Calculate soft shadow using ray marching.
    Intentionally using many steps for quality.
    """
    result = 1.0
    t = 0.02  # Start slightly away from surface
    
    for _ in range(64):  # Intentionally high step count
        p = origin + light_dir * t
        d = scene_sdf_only(p, time_val)
        
        if d < SURF_DIST:
            return 0.0
        
        result = min(result, SHADOW_SOFTNESS * d / t)
        t += d
        
        if t > 20.0:
            break
    
    return max(0.0, result)


def calculate_ao(p: Vec3, normal: Vec3, time_val: float) -> float:
    """
    Calculate ambient occlusion.
    Intentionally using simple sampling without optimization.
    """
    occlusion = 0.0
    
    for i in range(AO_STEPS):
        dist = AO_STEP_SIZE * (i + 1)
        sample_point = p + normal * dist
        d = scene_sdf_only(sample_point, time_val)
        occlusion += (dist - d) / (2.0 ** i)
    
    return max(0.0, 1.0 - occlusion * 0.5)


def get_checkerboard(p: Vec3) -> float:
    """Get checkerboard pattern for ground."""
    checker = int(math.floor(p.x) + math.floor(p.z)) % 2
    return 0.8 if checker else 1.0


def shade_pixel(hit_point: Vec3, normal: Vec3, view_dir: Vec3, 
                material: Material, time_val: float, is_ground: bool) -> Vec3:
    """
    Calculate shading for a hit point.
    Uses Blinn-Phong model with shadows and AO.
    """
    # Light setup - intentionally computing light direction every time
    light_pos = Vec3(5.0 * math.sin(time_val * 0.3), 8.0, 5.0 * math.cos(time_val * 0.3))
    light_dir = (light_pos - hit_point).normalize()
    light_color = Vec3(1.0, 0.95, 0.9)
    
    # Ambient
    ambient_color = Vec3(0.15, 0.18, 0.25)
    ambient = Vec3(
        material.color.x * ambient_color.x,
        material.color.y * ambient_color.y,
        material.color.z * ambient_color.z
    )
    
    # Diffuse
    diff = max(0.0, normal.dot(light_dir))
    diffuse = Vec3(
        material.color.x * diff * light_color.x,
        material.color.y * diff * light_color.y,
        material.color.z * diff * light_color.z
    )
    
    # Specular (Blinn-Phong)
    half_vec = (light_dir - view_dir).normalize()
    spec = pow(max(0.0, normal.dot(half_vec)), material.shininess)
    specular = light_color * spec * material.reflectivity
    
    # Apply checkerboard to ground
    if is_ground:
        checker = get_checkerboard(hit_point)
        diffuse = diffuse * checker
        ambient = ambient * checker
    
    # Soft shadows
    shadow = calculate_soft_shadow(hit_point + normal * 0.01, light_dir, time_val)
    
    # Ambient occlusion
    ao = calculate_ao(hit_point, normal, time_val)
    
    # Combine
    color = ambient * ao + (diffuse + specular) * shadow
    
    return color


def trace_ray(origin: Vec3, direction: Vec3, time_val: float, depth: int = 0) -> Vec3:
    """
    Trace a ray and return the color.
    Handles reflections recursively.
    """
    if depth > REFLECTION_BOUNCES:
        return Vec3(0.1, 0.15, 0.2)  # Sky color for max depth
    
    dist, material_id = ray_march(origin, direction, time_val)
    
    if material_id is None:
        # Sky gradient
        t = 0.5 * (direction.y + 1.0)
        sky_bottom = Vec3(0.5, 0.7, 1.0)
        sky_top = Vec3(0.1, 0.2, 0.4)
        return Vec3(
            sky_bottom.x * (1 - t) + sky_top.x * t,
            sky_bottom.y * (1 - t) + sky_top.y * t,
            sky_bottom.z * (1 - t) + sky_top.z * t
        )
    
    hit_point = origin + direction * dist
    normal = get_normal(hit_point, time_val)
    material = MATERIALS[material_id]
    
    # Base shading
    color = shade_pixel(hit_point, normal, direction, material, time_val, 
                       material_id == 'ground')
    
    # Reflections
    if material.reflectivity > 0.01 and depth < REFLECTION_BOUNCES:
        reflect_dir = direction.reflect(normal)
        reflect_origin = hit_point + normal * 0.01
        reflect_color = trace_ray(reflect_origin, reflect_dir, time_val, depth + 1)
        
        color = Vec3(
            color.x * (1 - material.reflectivity) + reflect_color.x * material.reflectivity,
            color.y * (1 - material.reflectivity) + reflect_color.y * material.reflectivity,
            color.z * (1 - material.reflectivity) + reflect_color.z * material.reflectivity
        )
    
    return color


def get_camera_ray(x: int, y: int, width: int, height: int, time_val: float) -> Tuple[Vec3, Vec3]:
    """
    Calculate camera ray for a pixel.
    Intentionally recalculating camera matrix for each pixel.
    """
    # Camera setup
    cam_dist = 6.0
    cam_height = 3.0
    cam_angle = time_val * 0.2
    
    cam_pos = Vec3(
        cam_dist * math.sin(cam_angle),
        cam_height,
        cam_dist * math.cos(cam_angle)
    )
    
    target = Vec3(0, 0.5, 0)
    
    # Calculate camera basis vectors (intentionally for each pixel)
    forward = (target - cam_pos).normalize()
    right = Vec3(0, 1, 0).cross(forward).normalize()
    up = forward.cross(right)
    
    # Screen coordinates
    aspect = width / height
    fov = 1.0  # ~60 degrees
    
    u = (2.0 * x / width - 1.0) * aspect * fov
    v = (1.0 - 2.0 * y / height) * fov
    
    direction = (forward + right * u + up * v).normalize()
    
    return cam_pos, direction


def render_frame(surface: pygame.Surface, time_val: float) -> None:
    """
    Render a complete frame.
    This is the main rendering loop - intentionally unoptimized.
    """
    width = surface.get_width()
    height = surface.get_height()
    
    # Lock surface for pixel access
    pixel_array = pygame.surfarray.pixels3d(surface)
    
    # Render each pixel individually (very slow!)
    for y in range(height):
        for x in range(width):
            # Get camera ray
            origin, direction = get_camera_ray(x, y, width, height, time_val)
            
            # Trace the ray
            color = trace_ray(origin, direction, time_val)
            
            # Gamma correction
            color = Vec3(
                math.pow(max(0, min(1, color.x)), 0.4545),
                math.pow(max(0, min(1, color.y)), 0.4545),
                math.pow(max(0, min(1, color.z)), 0.4545)
            )
            
            # Convert to 8-bit color
            r = int(color.x * 255)
            g = int(color.y * 255)
            b = int(color.z * 255)
            
            pixel_array[x, y] = (r, g, b)
    
    del pixel_array


class RaymarchingDemo:
    """Main demo class."""
    
    def __init__(self, width: int = WIDTH, height: int = HEIGHT):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Raymarching Demo - Optimize Me!")
        self.clock = pygame.time.Clock()
        self.running = True
        self.time = 0.0
        self.frame_count = 0
        self.fps_history: List[float] = []
    
    def handle_events(self) -> None:
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def update(self, dt: float) -> None:
        """Update simulation state."""
        self.time += dt
        self.frame_count += 1
    
    def render(self) -> None:
        """Render the current frame."""
        render_frame(self.screen, self.time)
        pygame.display.flip()
    
    def get_average_fps(self) -> float:
        """Return average FPS over recent history."""
        if not self.fps_history:
            return 0.0
        return sum(self.fps_history) / len(self.fps_history)
    
    def run(self, max_frames: Optional[int] = None) -> float:
        """
        Main loop. Returns average FPS.
        If max_frames is set, stops after that many frames.
        """
        frame_times = []
        
        while self.running:
            frame_start = time.time()
            
            self.handle_events()
            
            # Fixed timestep for animation
            self.update(1/30.0)
            
            self.render()
            
            frame_time = time.time() - frame_start
            frame_times.append(frame_time)
            
            if frame_time > 0:
                fps = 1.0 / frame_time
                self.fps_history.append(fps)
                if len(self.fps_history) > 30:
                    self.fps_history.pop(0)
            
            # Update window title with FPS
            avg_fps = self.get_average_fps()
            pygame.display.set_caption(f"Raymarching Demo - FPS: {avg_fps:.1f}")
            
            if max_frames and self.frame_count >= max_frames:
                break
        
        pygame.quit()
        
        # Return average FPS
        if frame_times:
            avg_frame_time = sum(frame_times) / len(frame_times)
            return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
        return 0.0


def main():
    """Entry point."""
    demo = RaymarchingDemo()
    avg_fps = demo.run()
    print(f"Average FPS: {avg_fps:.2f}")


if __name__ == "__main__":
    main()
