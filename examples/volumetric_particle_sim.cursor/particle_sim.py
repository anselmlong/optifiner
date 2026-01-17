"""
Volumetric 3D Particle Simulation - Optimized Version

Optimizations:
1. NumPy vectorization for all physics and math
2. Spatial grid for O(N) particle collisions
3. Vectorized volumetric raymarching
4. Pre-rendered particle sprites for fast drawing
5. Minimal object creation in the main loop
"""

import os
import math
import random
from typing import List, Tuple
import pygame
import numpy as np

# Configuration
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
NUM_PARTICLES = 500  # Increased since we are optimizing
NUM_LIGHTS = 4
FOG_DENSITY = 0.02
RAYMARCH_STEPS = 8
PARTICLE_RADIUS = 8.0
GRAVITY = 0.15
BOUNCE_DAMPING = 0.7
WORLD_BOUNDS = 200.0
PARTICLE_INFLUENCE_RADIUS = PARTICLE_RADIUS * 3

class ParticleSystem:
    def __init__(self, num_particles: int):
        self.num_particles = num_particles
        
        # State stored in NumPy arrays for vectorization
        self.pos = np.zeros((num_particles, 3), dtype=np.float32)
        self.vel = np.zeros((num_particles, 3), dtype=np.float32)
        self.colors = np.zeros((num_particles, 3), dtype=np.float32)
        self.radii = np.zeros(num_particles, dtype=np.float32)
        self.mass = np.zeros(num_particles, dtype=np.float32)
        self.emission = np.zeros(num_particles, dtype=np.float32)
        
        self._init_particles()
        
    def _init_particles(self):
        # Dreamy cosmic palette
        colors_palette = np.array([
            [255, 120, 200], [120, 200, 255], [255, 200, 120],
            [200, 120, 255], [120, 255, 200], [255, 150, 150],
            [150, 255, 255], [255, 220, 180]
        ], dtype=np.float32)

        for i in range(self.num_particles):
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(0, math.pi)
            r = random.uniform(20, WORLD_BOUNDS * 0.8)
            
            self.pos[i] = [
                r * math.sin(phi) * math.cos(theta),
                r * math.cos(phi),
                r * math.sin(phi) * math.sin(theta)
            ]
            
            self.vel[i] = [
                random.uniform(-2, 2),
                random.uniform(-1, 3),
                random.uniform(-2, 2)
            ]
            
            self.colors[i] = colors_palette[random.randint(0, len(colors_palette)-1)]
            self.radii[i] = random.uniform(PARTICLE_RADIUS * 0.5, PARTICLE_RADIUS * 1.5)
            self.mass[i] = self.radii[i] ** 2
            self.emission[i] = random.uniform(0.3, 1.0) if random.random() > 0.4 else random.uniform(0.0, 0.2)

    def update(self, dt: float):
        # Vectorized physics update
        # Gravity
        self.vel[:, 1] -= GRAVITY * dt * 60
        
        # Position
        self.pos += self.vel * (dt * 60)
        
        # Boundary checks (vectorized)
        mask_low = self.pos < -WORLD_BOUNDS
        mask_high = self.pos > WORLD_BOUNDS
        
        self.pos[mask_low] = -WORLD_BOUNDS
        self.pos[mask_high] = WORLD_BOUNDS
        
        # Bounce velocity
        self.vel[mask_low | mask_high] *= -BOUNCE_DAMPING

class SpatialGrid:
    """A uniform grid for O(N) collision detection"""
    def __init__(self, bounds: float, cell_size: float):
        self.bounds = bounds
        self.cell_size = cell_size
        self.dim = int((bounds * 2) / cell_size) + 1
        self.grid = {}

    def update(self, positions: np.ndarray):
        self.grid = {}
        # Map positions to grid cells
        indices = ((positions + self.bounds) / self.cell_size).astype(np.int32)
        for i, idx in enumerate(indices):
            cell_key = tuple(idx)
            if cell_key not in self.grid:
                self.grid[cell_key] = []
            self.grid[cell_key].append(i)

    def get_neighbors(self, cell_idx: tuple):
        neighbors = []
        cx, cy, cz = cell_idx
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    key = (cx + dx, cy + dy, cz + dz)
                    if key in self.grid:
                        neighbors.extend(self.grid[key])
        return neighbors

class VolumetricRenderer:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.aspect_ratio = width / height
        self.fov = 60.0
        self.fov_scale = math.tan(math.radians(self.fov / 2))
        
        # Pre-generate sprites for particles
        self.particle_sprites = {} # Cached surfaces by (radius, color_tuple)

    def get_particle_sprite(self, radius: int, color: tuple, emission: float):
        key = (radius, color, int(emission * 10))
        if key in self.particle_sprites:
            return self.particle_sprites[key]
        
        # Create sprite surface
        size = radius * 6
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        
        # Draw soft glow layers
        for i in range(4, 0, -1):
            r = int(radius * (1 + i * 0.8))
            alpha = int(30 * (1 - i / 5) * (0.5 + emission * 0.5))
            if r > 0:
                pygame.draw.circle(sprite, (*color, alpha), (center, center), r)
        
        # Core
        pygame.draw.circle(sprite, (*color, 255), (center, center), radius)
        # Highlight
        h_color = (min(255, color[0]+100), min(255, color[1]+100), min(255, color[2]+100), 255)
        pygame.draw.circle(sprite, h_color, (center - radius//3, center - radius//3), max(1, radius//3))
        
        self.particle_sprites[key] = sprite
        return sprite

    def project_points(self, positions: np.ndarray, cam_pos: np.ndarray, cam_rot: float):
        # Vectorized projection
        rel_pos = positions - cam_pos
        
        cos_r = math.cos(cam_rot)
        sin_r = math.sin(cam_rot)
        
        # Rotation around Y
        rx = rel_pos[:, 0] * cos_r - rel_pos[:, 2] * sin_r
        ry = rel_pos[:, 1]
        rz = rel_pos[:, 0] * sin_r + rel_pos[:, 2] * cos_r
        
        # Screen projection
        mask = rz > 0.1
        screen_x = np.full(len(positions), -1, dtype=np.float32)
        screen_y = np.full(len(positions), -1, dtype=np.float32)
        
        f = self.fov_scale
        screen_x[mask] = (rx[mask] / (rz[mask] * f * self.aspect_ratio)) * (self.width / 2) + (self.width / 2)
        screen_y[mask] = (-ry[mask] / (rz[mask] * f)) * (self.height / 2) + (self.height / 2)
        
        return screen_x.astype(np.int32), screen_y.astype(np.int32), rz

class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.ps = ParticleSystem(NUM_PARTICLES)
        self.renderer = VolumetricRenderer(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.grid = SpatialGrid(WORLD_BOUNDS, PARTICLE_RADIUS * 3)
        
        self.camera_pos = np.array([0, 50, -400.0], dtype=np.float32)
        self.camera_rot = 0.0
        self.time = 0.0
        
        # Lights
        self.light_pos = np.zeros((NUM_LIGHTS, 3), dtype=np.float32)
        self.light_colors = np.array([
            [1.0, 0.6, 0.9], [0.5, 0.8, 1.0], [1.0, 0.85, 0.5], [0.6, 1.0, 0.8]
        ], dtype=np.float32)
        self.light_intensity = 200.0

    def update(self, dt: float):
        self.time += dt
        self.camera_rot += dt * 0.3
        
        # Update lights
        for i in range(NUM_LIGHTS):
            angle = self.time * (0.4 + i * 0.12) + i * (2 * math.pi / NUM_LIGHTS)
            self.light_pos[i] = [
                math.cos(angle) * WORLD_BOUNDS * 0.7,
                math.sin(angle * 0.7) * WORLD_BOUNDS * 0.2,
                math.sin(angle) * WORLD_BOUNDS * 0.7
            ]
            
        self.ps.update(dt)
        self._check_collisions()

    def _check_collisions(self):
        self.grid.update(self.ps.pos)
        
        # Only check particles in neighboring grid cells
        for cell_key, indices in self.grid.grid.items():
            neighbors = self.grid.get_neighbors(cell_key)
            for i in indices:
                p1_pos = self.ps.pos[i]
                p1_rad = self.ps.radii[i]
                for j in neighbors:
                    if i >= j: continue
                    
                    diff = self.ps.pos[j] - p1_pos
                    dist_sq = np.sum(diff**2)
                    min_dist = p1_rad + self.ps.radii[j]
                    
                    if dist_sq < min_dist**2 and dist_sq > 0:
                        dist = math.sqrt(dist_sq)
                        normal = diff / dist
                        
                        # Impulse-based collision
                        rel_vel = self.ps.vel[j] - self.ps.vel[i]
                        v_dot_n = np.dot(rel_vel, normal)
                        
                        if v_dot_n < 0:
                            total_mass = self.ps.mass[i] + self.ps.mass[j]
                            impulse = -2.0 * v_dot_n / total_mass
                            
                            self.ps.vel[i] -= impulse * self.ps.mass[j] * normal * BOUNCE_DAMPING
                            self.ps.vel[j] += impulse * self.ps.mass[i] * normal * BOUNCE_DAMPING
                            
                            # Separation
                        overlap = min_dist - dist
                        self.ps.pos[i] -= normal * overlap * 0.5
                        self.ps.pos[j] += normal * overlap * 0.5

    def render_background(self):
        # Vectorized background and fog
        sample_rate = 16  # Better quality
        w, h = SCREEN_WIDTH // sample_rate, SCREEN_HEIGHT // sample_rate
        
        # Generate coordinates
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        nx = x_coords / w
        ny = y_coords / h
        
        ndc_x = nx * 2 - 1
        ndc_y = 1 - ny * 2
        
        f = self.renderer.fov_scale
        ray_x = ndc_x * f * self.renderer.aspect_ratio
        ray_y = ndc_y * f
        ray_z = np.ones_like(ray_x)
        
        # Normalize rays
        ray_len = np.sqrt(ray_x**2 + ray_y**2 + ray_z**2)
        ray_x /= ray_len
        ray_y /= ray_len
        ray_z /= ray_len
                
        # Rotate rays
        cos_r, sin_r = math.cos(self.camera_rot), math.sin(self.camera_rot)
        rot_ray_x = ray_x * cos_r + ray_z * sin_r
        rot_ray_y = ray_y
        rot_ray_z = -ray_x * sin_r + ray_z * cos_r
        
        # Background nebula effect
        swirl = np.sin(nx * 3 + self.time * 0.5) * np.cos(ny * 2 + self.time * 0.3)
        base_r = 15 + 25 * ny + 15 * swirl
        base_g = 5 + 15 * (1 - ny)
        base_b = 35 + 40 * ny + 20 * np.abs(swirl)
        
        # Raymarching (vectorized)
        accum_color = np.zeros((h, w, 3), dtype=np.float32)
        accum_density = np.zeros((h, w), dtype=np.float32)
        
        max_dist = WORLD_BOUNDS * 2.5
        step_size = max_dist / RAYMARCH_STEPS
        
        # Optimization: Only use a subset of particles for the volumetric effect
        num_fog_particles = min(30, NUM_PARTICLES)
        fog_indices = np.random.choice(NUM_PARTICLES, num_fog_particles, replace=False)
        fog_pos = self.ps.pos[fog_indices]
        fog_colors = self.ps.colors[fog_indices] / 255.0
        fog_emission = self.ps.emission[fog_indices]
        fog_radii = self.ps.radii[fog_indices] * 3.0
        
        for step in range(RAYMARCH_STEPS):
            t = (step + 0.5) * step_size
            curr_x = self.camera_pos[0] + rot_ray_x * t
            curr_y = self.camera_pos[1] + rot_ray_y * t
            curr_z = self.camera_pos[2] + rot_ray_z * t
            
            local_density = np.zeros((h, w), dtype=np.float32)
            local_color = np.zeros((h, w, 3), dtype=np.float32)
            
            for i in range(num_fog_particles):
                dx = curr_x - fog_pos[i, 0]
                dy = curr_y - fog_pos[i, 1]
                dz = curr_z - fog_pos[i, 2]
                dist_sq = dx*dx + dy*dy + dz*dz
                
                inf = fog_radii[i]
                inf_sq = inf * inf
                
                # Fast mask
                mask = dist_sq < inf_sq
                if np.any(mask):
                    dist = np.sqrt(dist_sq[mask])
                    falloff = (1.0 - dist / inf) ** 2
                    local_density[mask] += falloff * 0.5
                    local_color[mask] += fog_colors[i] * fog_emission[i] * falloff[:, None]
            
            alpha = 1.0 - np.exp(-local_density * step_size * FOG_DENSITY)
            remaining = 1.0 - accum_density
            accum_color += local_color * (alpha * remaining)[:, :, None]
            accum_density += alpha * remaining
            
        # Final colors
        final_r = (base_r * (1 - accum_density) + accum_color[:,:,0] * 255 * accum_density).clip(0, 255)
        final_g = (base_g * (1 - accum_density) + accum_color[:,:,1] * 255 * accum_density).clip(0, 255)
        final_b = (base_b * (1 - accum_density) + accum_color[:,:,2] * 255 * accum_density).clip(0, 255)
        
        # Use pygame.surfarray for fast blitting
        rgb_array = np.stack([final_r, final_g, final_b], axis=2).astype(np.uint8)
        # Transpose to (W, H, 3) for pygame
        rgb_array = np.transpose(rgb_array, (1, 0, 2))
        
        bg_surf = pygame.surfarray.make_surface(rgb_array)
        # Scale up to screen size
        pygame.transform.scale(bg_surf, (SCREEN_WIDTH, SCREEN_HEIGHT), self.screen)

    def render_particles(self):
        sx, sy, depth = self.renderer.project_points(self.ps.pos, self.camera_pos, self.camera_rot)
        
        # Depth sorting
        indices = np.argsort(-depth)
        
        for i in indices:
            if sx[i] < -50 or sx[i] > SCREEN_WIDTH + 50 or depth[i] <= 0.1:
                continue
                
            radius = int(self.ps.radii[i] * 400 / depth[i])
            if radius < 1: continue
            
            color = tuple(self.ps.colors[i].astype(int))
            sprite = self.renderer.get_particle_sprite(radius, color, self.ps.emission[i])
            
            # Blit sprite
            rect = sprite.get_rect(center=(sx[i], sy[i]))
            self.screen.blit(sprite, rect, special_flags=pygame.BLEND_ALPHA_SDL2)

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        self.running = False
            
            dt = self.clock.tick(60) / 1000.0
            dt = min(dt, 0.1)
            
            self.update(dt)
            self.screen.fill((8, 4, 20))
            self.render_background()
            self.render_particles()
            
            # Draw FPS
            fps = self.clock.get_fps()
            if self.time % 1.0 < 0.1:
                pygame.display.set_caption(f"Optimized Particle Sim - FPS: {fps:.1f}")
                
            pygame.display.flip()

def main():
    sim = Simulation()
    sim.run()
    pygame.quit()

if __name__ == "__main__":
    main()
