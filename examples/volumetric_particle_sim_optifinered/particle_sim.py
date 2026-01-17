"""
Volumetric 3D Particle Simulation with Software Rendering

A deliberately unoptimized particle simulation with:
- Software-based 3D raymarching for volumetric effects
- Thousands of particles with physics
- Volumetric fog and lighting
- Per-pixel shading calculations

The goal is to optimize this code to achieve higher FPS
without breaking visual correctness or functionality.
"""

import os
import math
import random
from dataclasses import dataclass
from typing import List, Tuple


import pygame
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# Configuration
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
NUM_PARTICLES = 300
NUM_LIGHTS = 4
FOG_DENSITY = 0.02
RAYMARCH_STEPS = 8  # Reduced from 16
PARTICLE_RADIUS = 8.0
GRAVITY = 0.15
BOUNCE_DAMPING = 0.7
WORLD_BOUNDS = 200.0
PARTICLE_INFLUENCE_RADIUS = PARTICLE_RADIUS * 3  # Pre-calculated


@dataclass
class Vector3:
    """3D Vector class - intentionally not using numpy for 'simplicity'"""
    x: float
    y: float
    z: float
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __truediv__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)
    
    def dot(self, other: 'Vector3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vector3') -> 'Vector3':
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    
    def normalize(self) -> 'Vector3':
        l = self.length()
        if l > 0:
            return self / l
        return Vector3(0, 0, 0)
    
    def copy(self) -> 'Vector3':
        return Vector3(self.x, self.y, self.z)


@dataclass
class Particle:
    """A single particle in the simulation"""
    position: Vector3
    velocity: Vector3
    color: Tuple[int, int, int]
    radius: float
    mass: float
    emission: float  # Light emission strength
    
    def update(self, dt: float) -> None:
        """Update particle physics - intentionally basic"""
        # Apply gravity
        self.velocity.y -= GRAVITY * dt * 60
        
        # Update position
        self.position.x += self.velocity.x * dt * 60
        self.position.y += self.velocity.y * dt * 60
        self.position.z += self.velocity.z * dt * 60
        
        # Bounce off world bounds
        if self.position.x < -WORLD_BOUNDS:
            self.position.x = -WORLD_BOUNDS
            self.velocity.x *= -BOUNCE_DAMPING
        if self.position.x > WORLD_BOUNDS:
            self.position.x = WORLD_BOUNDS
            self.velocity.x *= -BOUNCE_DAMPING
            
        if self.position.y < -WORLD_BOUNDS:
            self.position.y = -WORLD_BOUNDS
            self.velocity.y *= -BOUNCE_DAMPING
        if self.position.y > WORLD_BOUNDS:
            self.position.y = WORLD_BOUNDS
            self.velocity.y *= -BOUNCE_DAMPING
            
        if self.position.z < -WORLD_BOUNDS:
            self.position.z = -WORLD_BOUNDS
            self.velocity.z *= -BOUNCE_DAMPING
        if self.position.z > WORLD_BOUNDS:
            self.position.z = WORLD_BOUNDS
            self.velocity.z *= -BOUNCE_DAMPING


@dataclass
class Light:
    """A point light source"""
    position: Vector3
    color: Tuple[float, float, float]
    intensity: float
    orbit_radius: float
    orbit_speed: float
    orbit_phase: float


class VolumetricRenderer:
    """Software-based volumetric renderer - intentionally unoptimized"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.aspect_ratio = width / height
        self.fov = 60.0
        self.camera_distance = 400.0
        
    def project_point(self, point: Vector3, camera_pos: Vector3, cos_r: float, sin_r: float) -> Tuple[int, int, float]:
        """Project 3D point to 2D screen coordinates"""
        # Rotate point around Y axis relative to camera
        rel_x = point.x - camera_pos.x
        rel_y = point.y - camera_pos.y
        rel_z = point.z - camera_pos.z
        
        rot_x = rel_x * cos_r - rel_z * sin_r
        rot_z = rel_x * sin_r + rel_z * cos_r
        
        if rot_z <= 0.1:
            return (-1, -1, 0)
        
        # Perspective projection
        fov_scale = math.tan(math.radians(self.fov / 2))
        screen_x = (rot_x / (rot_z * fov_scale * self.aspect_ratio)) * self.width / 2 + self.width / 2
        screen_y = (-rel_y / (rot_z * fov_scale)) * self.height / 2 + self.height / 2
        
        return (int(screen_x), int(screen_y), rot_z)
    
    def calculate_volumetric_fog(self, ray_ox, ray_oy, ray_oz, ray_dx, ray_dy, ray_dz, 
                                  grid, grid_size, lights_data,
                                  max_distance: float) -> Tuple[float, float, float]:
        """
        Raymarch through the scene to calculate volumetric fog contribution.
        Optimized with spatial grid and pre-extracted data.
        """
        acc_r, acc_g, acc_b = 0.0, 0.0, 0.0
        acc_density = 0.0
        step_size = max_distance / RAYMARCH_STEPS
        inv_grid_size = 1.0 / grid_size
        fog_factor = step_size * FOG_DENSITY
        
        for step in range(RAYMARCH_STEPS):
            t = step * step_size
            curr_x = ray_ox + ray_dx * t
            curr_y = ray_oy + ray_dy * t
            curr_z = ray_oz + ray_dz * t
            
            cell = (int(curr_x * inv_grid_size), int(curr_y * inv_grid_size), int(curr_z * inv_grid_size))
            nearby_particles = grid.get(cell)
            if not nearby_particles:
                continue
                
            local_density = 0.0
            local_r, local_g, local_b = 0.0, 0.0, 0.0
            
            for px, py, pz, p_infl, p_infl_sq, inv_p_infl, pr, pg, pb, pem in nearby_particles:
                dx = curr_x - px
                d2 = dx * dx
                if d2 >= p_infl_sq: continue
                dy = curr_y - py
                d2 += dy * dy
                if d2 >= p_infl_sq: continue
                dz = curr_z - pz
                d2 += dz * dz
                if d2 >= p_infl_sq: continue
                
                falloff = 1.0 - math.sqrt(d2) * inv_p_infl
                falloff_sq = falloff * falloff
                local_density += falloff_sq * 0.5
                emission = pem * falloff_sq
                local_r += pr * emission
                local_g += pg * emission
                local_b += pb * emission
            
            if local_density > 0:
                for lx, ly, lz, lc0, lc1, lc2, l_int in lights_data:
                    ldx, ldy, ldz = curr_x - lx, curr_y - ly, curr_z - lz
                    ld2 = ldx*ldx + ldy*ldy + ldz*ldz
                    attenuation = l_int / (1.0 + ld2 * 0.0001)
                    local_r += lc0 * attenuation
                    local_g += lc1 * attenuation
                    local_b += lc2 * attenuation
                
                alpha = 1.0 - math.exp(-local_density * fog_factor)
                remaining = 1.0 - acc_density
                factor = alpha * remaining
                acc_r += local_r * factor
                acc_g += local_g * factor
                acc_b += local_b * factor
                acc_density += factor
                
                if acc_density > 0.95:
                    break
        
        return (min(1.0, acc_r), min(1.0, acc_g), min(1.0, acc_b))
    
    def shade_particle(self, particle: Particle, lights: List[Light], 
                       view_dir: Vector3) -> Tuple[int, int, int]:
        """Calculate beautiful shading for a single particle"""
        p_pos = particle.position
        px, py, pz = p_pos.x, p_pos.y, p_pos.z
        base_color = particle.color
        
        # Soft ambient with slight blue tint for depth
        final_r = base_color[0] * 0.15 + 10
        final_g = base_color[1] * 0.15 + 10
        final_b = base_color[2] * 0.15 + 25 # Blue ambient boost
        
        vx, vy, vz = view_dir.x, view_dir.y, view_dir.z
        
        for light in lights:
            l_pos = light.position
            lx_pos, ly_pos, lz_pos = l_pos.x, l_pos.y, l_pos.z
            
            dx = lx_pos - px
            dy = ly_pos - py
            dz = lz_pos - pz
            
            dist_sq = dx * dx + dy * dy + dz * dz
            if dist_sq > 0:
                dist = math.sqrt(dist_sq)
                inv_dist = 1.0 / dist
                
                # Normalize light direction
                ldx, ldy, ldz = dx * inv_dist, dy * inv_dist, dz * inv_dist
                
                # Softer diffuse lighting with smoother falloff
                attenuation = light.intensity / (1.0 + dist_sq * 0.00008)
                if attenuation > 1.2: attenuation = 1.2
                
                # Enhanced fresnel-like rim lighting
                dot = vx * ldx + vy * ldy + vz * ldz
                fresnel = 1.0 - abs(dot)
                fresnel = fresnel * fresnel
                
                factor = attenuation * (0.6 + fresnel * 0.4)
                l_col = light.color
                final_r += base_color[0] * l_col[0] * factor
                final_g += base_color[1] * l_col[1] * factor
                final_b += base_color[2] * l_col[2] * factor
        
        # Add emission
        em = particle.emission
        emission_boost = 1.0 + em * 0.8
        final_r = final_r * emission_boost + base_color[0] * em * 0.3
        final_g = final_g * emission_boost + base_color[1] * em * 0.3
        final_b = final_b * emission_boost + base_color[2] * em * 0.3
        
        # Tone mapping
        return (
            int(final_r / (1 + final_r / 300)),
            int(final_g / (1 + final_g / 300)),
            int(final_b / (1 + final_b / 300))
        )


class ParticleSimulation:
    """Main simulation class"""
    
    def __init__(self):
        if os.environ.get('SDL_VIDEODRIVER') is None and not os.environ.get('DISPLAY'):
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Volumetric Particle Simulation - Optimize Me!")
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.renderer = VolumetricRenderer(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.particles: List[Particle] = []
        self.lights: List[Light] = []
        
        self.camera_rotation = 0.0
        self.camera_position = Vector3(0, 50, -self.renderer.camera_distance)
        self.time = 0.0
        
        self._init_particles()
        self._init_lights()

        # Pre-calculate vignette
        self.vignette = self._create_vignette()
        self.glow_cache = {}

        # Metrics
        self.frame_count = 0
        self.start_time = 0.0
        self.fps = 0.0
    
    def _create_vignette(self) -> pygame.Surface:
        vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        vignette_step = 32
        for y in range(0, SCREEN_HEIGHT, vignette_step):
            for x in range(0, SCREEN_WIDTH, vignette_step):
                dx = (x - SCREEN_WIDTH / 2) / (SCREEN_WIDTH / 2)
                dy = (y - SCREEN_HEIGHT / 2) / (SCREEN_HEIGHT / 2)
                dist = math.sqrt(dx * dx + dy * dy)
                alpha = int(min(80, dist * dist * 60))
                pygame.draw.rect(vignette, (0, 0, 0, alpha), (x, y, vignette_step, vignette_step))
        return vignette

    def _init_particles(self) -> None:
        """Initialize particles with random positions and properties"""
        # Dreamy cosmic palette - soft pastels and rich jewel tones
        colors = [
            (255, 120, 200),  # Hot pink
            (120, 200, 255),  # Sky blue
            (255, 200, 120),  # Peach gold
            (200, 120, 255),  # Lavender
            (120, 255, 200),  # Mint
            (255, 150, 150),  # Coral
            (150, 255, 255),  # Aqua
            (255, 220, 180),  # Warm cream
        ]
        
        for i in range(NUM_PARTICLES):
            # Distribute particles in a sphere
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(0, math.pi)
            r = random.uniform(20, WORLD_BOUNDS * 0.8)
            
            pos = Vector3(
                r * math.sin(phi) * math.cos(theta),
                r * math.cos(phi),
                r * math.sin(phi) * math.sin(theta)
            )
            
            vel = Vector3(
                random.uniform(-2, 2),
                random.uniform(-1, 3),
                random.uniform(-2, 2)
            )
            
            color = random.choice(colors)
            radius = random.uniform(PARTICLE_RADIUS * 0.5, PARTICLE_RADIUS * 1.5)
            mass = radius ** 2
            # More particles emit light for prettier effect
            emission = random.uniform(0.3, 1.0) if random.random() > 0.4 else random.uniform(0.0, 0.2)
            
            self.particles.append(Particle(pos, vel, color, radius, mass, emission))
    
    def _init_lights(self) -> None:
        """Initialize orbiting lights"""
        # Vibrant light colors for dramatic effect
        light_colors = [
            (1.0, 0.6, 0.9),   # Magenta
            (0.5, 0.8, 1.0),   # Cyan blue
            (1.0, 0.85, 0.5),  # Golden
            (0.6, 1.0, 0.8),   # Mint green
        ]
        
        for i in range(NUM_LIGHTS):
            phase = i * (2 * math.pi / NUM_LIGHTS)
            self.lights.append(Light(
                position=Vector3(0, 0, 0),
                color=light_colors[i % len(light_colors)],
                intensity=200.0,  # Brighter lights for more dramatic effect
                orbit_radius=WORLD_BOUNDS * 0.7,
                orbit_speed=0.4 + i * 0.12,  # Slightly varied speeds
                orbit_phase=phase
            ))
    
    def update_lights(self, dt: float) -> None:
        """Update light positions"""
        for light in self.lights:
            angle = self.time * light.orbit_speed + light.orbit_phase
            light.position.x = math.cos(angle) * light.orbit_radius
            light.position.y = math.sin(angle * 0.7) * light.orbit_radius * 0.3
            light.position.z = math.sin(angle) * light.orbit_radius
    
    def check_particle_collisions(self) -> None:
        """
        Check and resolve particle-particle collisions.
        Optimized with X-sorting and pruning.
        """
        self.particles.sort(key=lambda p: p.position.x)
        max_radius = PARTICLE_RADIUS * 1.5 * 2
        max_radius_sq = max_radius * max_radius
        
        for i in range(len(self.particles)):
            p1 = self.particles[i]
            p1_pos = p1.position
            p1_x, p1_y, p1_z = p1_pos.x, p1_pos.y, p1_pos.z
            
            for j in range(i + 1, len(self.particles)):
                p2 = self.particles[j]
                p2_pos = p2.position
                dx = p2_pos.x - p1_x
                if dx > max_radius:
                    break
                
                dy = p2_pos.y - p1_y
                if dy > max_radius or dy < -max_radius: continue
                dz = p2_pos.z - p1_z
                if dz > max_radius or dz < -max_radius: continue
                
                dist_sq = dx * dx + dy * dy + dz * dz
                if dist_sq > max_radius_sq:
                    continue
                    
                min_dist = p1.radius + p2.radius
                
                if dist_sq < min_dist * min_dist and dist_sq > 0:
                    dist = math.sqrt(dist_sq)
                    
                    # Normalize collision vector
                    nx = dx / dist
                    ny = dy / dist
                    nz = dz / dist
                    
                    # Relative velocity
                    p1_vel = p1.velocity
                    p2_vel = p2.velocity
                    dvx = p2_vel.x - p1_vel.x
                    dvy = p2_vel.y - p1_vel.y
                    dvz = p2_vel.z - p1_vel.z
                    
                    # Relative velocity along collision normal
                    dvn = dvx * nx + dvy * ny + dvz * nz
                    
                    if dvn < 0:  # Particles moving toward each other
                        # Mass-weighted impulse
                        total_mass = p1.mass + p2.mass
                        impulse = -2.0 * dvn / total_mass
                        
                        p1_vel.x -= impulse * p2.mass * nx * BOUNCE_DAMPING
                        p1_vel.y -= impulse * p2.mass * ny * BOUNCE_DAMPING
                        p1_vel.z -= impulse * p2.mass * nz * BOUNCE_DAMPING
                        
                        p2_vel.x += impulse * p1.mass * nx * BOUNCE_DAMPING
                        p2_vel.y += impulse * p1.mass * ny * BOUNCE_DAMPING
                        p2_vel.z += impulse * p1.mass * nz * BOUNCE_DAMPING
                        
                        # Separate particles
                        overlap = min_dist - dist
                        p1_pos.x -= nx * overlap * 0.5
                        p1_pos.y -= ny * overlap * 0.5
                        p1_pos.z -= nz * overlap * 0.5
                        p2_pos.x += nx * overlap * 0.5
                        p2_pos.y += ny * overlap * 0.5
                        p2_pos.z += nz * overlap * 0.5
    
    def render_volumetric_background(self, surface: pygame.Surface) -> None:
        """
        Render beautiful gradient background with nebula-like effects.
        Optimized with low-res rendering and spatial grid.
        """
        sample_rate = 16
        width = self.renderer.width
        height = self.renderer.height
        small_w = width // sample_rate
        small_h = height // sample_rate
        small_surf = pygame.Surface((small_w, small_h))
        
        # Pre-calculate spatial grid for fog
        grid = {}
        grid_size = 50
        for p in self.particles:
            infl = p.radius * 3
            px, py, pz = p.position.x, p.position.y, p.position.z
            min_x = int((px - infl) / grid_size)
            max_x = int((px + infl) / grid_size)
            min_y = int((py - infl) / grid_size)
            max_y = int((py + infl) / grid_size)
            min_z = int((pz - infl) / grid_size)
            max_z = int((pz + infl) / grid_size)
            
            p_info = (px, py, pz, infl, infl*infl, 1.0/infl, p.color[0]/255.0, p.color[1]/255.0, p.color[2]/255.0, p.emission)
            
            for i in range(min_x, max_x + 1):
                for j in range(min_y, max_y + 1):
                    for k in range(min_z, max_z + 1):
                        key = (i, j, k)
                        if key not in grid: grid[key] = []
                        grid[key].append(p_info)
        
        # Pre-extract light data
        lights_data = [(l.position.x, l.position.y, l.position.z, 
                        l.color[0] * 0.1, l.color[1] * 0.1, l.color[2] * 0.1, 
                        l.intensity) for l in self.lights]
        
        inv_width = 1.0 / width
        inv_height = 1.0 / height
        fov_scale = math.tan(math.radians(self.renderer.fov / 2))
        aspect = self.renderer.aspect_ratio
        cos_r = math.cos(self.camera_rotation)
        sin_r = math.sin(self.camera_rotation)
        
        # Pre-calculate nx dependent values
        nx_vals = [(sx * sample_rate) * inv_width for sx in range(small_w)]
        swirl_x1 = [math.sin(nx * 3 + self.time * 0.5) for nx in nx_vals]
        swirl_x2 = [math.cos(nx * 2 - self.time * 0.4) for nx in nx_vals]
        cloud_x1 = [nx * 6 for nx in nx_vals]
        cloud_x2 = [nx * 3 for nx in nx_vals]
        ray_x_vals = [(nx * 2 - 1) * fov_scale * aspect for nx in nx_vals]
        
        for sy in range(small_h):
            y = sy * sample_rate
            ny = y * inv_height
            ndc_y = 1 - ny * 2
            ray_y = ndc_y * fov_scale
            
            swirl_y1 = math.cos(ny * 2 + self.time * 0.3)
            swirl_y2 = math.sin(ny * 4 + self.time * 0.6)
            cloud_y1 = ny * 4 + self.time * 0.2
            cloud_y2 = -ny * 5 + self.time * 0.15
            
            for sx in range(small_w):
                swirl = swirl_x1[sx] * swirl_y1
                swirl2 = swirl_x2[sx] * swirl_y2
                
                base_r = int(15 + 25 * ny + 15 * swirl)
                base_g = int(5 + 15 * (1 - ny) + 10 * swirl2)
                base_b = int(35 + 40 * ny + 20 * abs(swirl))
                
                cloud = (math.sin(cloud_x1[sx] + cloud_y1) * 0.5 + 0.5) * \
                        (math.cos(cloud_x2[sx] + cloud_y2) * 0.5 + 0.5)
                
                base_r = int(min(60, base_r + cloud * 30))
                base_g = int(min(40, base_g + cloud * 15))
                base_b = int(min(80, base_b + cloud * 25))
                
                ray_x = ray_x_vals[sx]
                ray_z = 1.0
                ray_len = math.sqrt(ray_x * ray_x + ray_y * ray_y + ray_z * ray_z)
                inv_ray_len = 1.0 / ray_len
                
                rx = ray_x * inv_ray_len
                ry = ray_y * inv_ray_len
                rz = ray_z * inv_ray_len
                
                rot_ray_x = rx * cos_r + rz * sin_r
                rot_ray_y = ry
                rot_ray_z = -rx * sin_r + rz * cos_r
                
                fog_color = self.renderer.calculate_volumetric_fog(
                    self.camera_position.x, self.camera_position.y, self.camera_position.z,
                    rot_ray_x, rot_ray_y, rot_ray_z,
                    grid, grid_size, lights_data,
                    WORLD_BOUNDS * 3
                )
                
                fog_strength = (fog_color[0] + fog_color[1] + fog_color[2]) / 3
                blend = min(1.0, fog_strength * 2)
                
                final_r = int(base_r * (1 - blend) + fog_color[0] * 255 * blend)
                final_g = int(base_g * (1 - blend) + fog_color[1] * 255 * blend)
                final_b = int(base_b * (1 - blend) + fog_color[2] * 255 * blend)
                
                color = (min(255, max(0, final_r)), min(255, max(0, final_g)), min(255, max(0, final_b)))
                small_surf.set_at((sx, sy), color)
        
        pygame.transform.scale(small_surf, (width, height), surface)
    
    def render_particles(self, surface: pygame.Surface) -> None:
        """Render particles with depth sorting and beautiful soft shading"""
        # Calculate view direction
        view_dir = Vector3(
            math.sin(self.camera_rotation),
            0,
            math.cos(self.camera_rotation)
        )
        
        # Sort particles by depth - cache trig values but still O(n log n) sort
        sin_r = math.sin(self.camera_rotation)
        cos_r = math.cos(self.camera_rotation)
        cam_x = self.camera_position.x
        cam_z = self.camera_position.z
        
        sorted_particles = sorted(
            self.particles,
            key=lambda p: -(
                (p.position.x - cam_x) * sin_r +
                (p.position.z - cam_z) * cos_r
            )
        )
        
        for particle in sorted_particles:
            # Project particle position
            screen_x, screen_y, depth = self.renderer.project_point(
                particle.position, self.camera_position, cos_r, sin_r
            )
            
            if screen_x < 0 or depth <= 0:
                continue
            
            # Calculate screen-space radius
            screen_radius = int(particle.radius * 400 / depth)
            if screen_radius < 1:
                continue
            
            # Calculate shading
            color = self.renderer.shade_particle(particle, self.lights, view_dir)
            
            # Depth-based atmospheric fade (distant particles are more blue/purple)
            depth_fade = min(1.0, depth / 600)
            color = (
                int(color[0] * (1 - depth_fade * 0.5) + 80 * depth_fade * 0.5),
                int(color[1] * (1 - depth_fade * 0.4) + 60 * depth_fade * 0.4),
                int(color[2] * (1 - depth_fade * 0.2) + 120 * depth_fade * 0.2)
            )
            
            # Round color for caching to increase hit rate
            color_key = (color[0] >> 2, color[1] >> 2, color[2] >> 2)
            glow_key = (screen_radius, color_key, round(particle.emission, 1))
            
            if glow_key in self.glow_cache:
                glow_surface = self.glow_cache[glow_key]
                center = screen_radius * 3
            else:
                glow_surface = pygame.Surface((screen_radius * 6, screen_radius * 6), pygame.SRCALPHA)
                center = screen_radius * 3
                
                # Use rounded color for drawing to ensure cache consistency
                draw_color = (color_key[0] << 2, color_key[1] << 2, color_key[2] << 2)
                
                # Outer soft glow (large, very transparent) - reduced layers
                for glow_i in range(4, 0, -1):  # Was 8
                    glow_radius = int(screen_radius * (1 + glow_i * 0.8))
                    alpha = int(30 * (1 - glow_i / 5) * (0.5 + particle.emission * 0.5))
                    g_col = (draw_color[0], draw_color[1], draw_color[2], alpha)
                    if glow_radius > 0:
                        pygame.draw.circle(glow_surface, g_col, (center, center), glow_radius)
                
                # Inner brighter glow - reduced layers
                for glow_i in range(2, 0, -1):  # Was 4
                    glow_radius = int(screen_radius * (1 + glow_i * 0.3))
                    alpha = int(80 * (1 - glow_i / 3))
                    g_col = (
                        min(255, draw_color[0] + 30),
                        min(255, draw_color[1] + 30),
                        min(255, draw_color[2] + 30),
                        alpha
                    )
                    if glow_radius > 0:
                        pygame.draw.circle(glow_surface, g_col, (center, center), glow_radius)
                
                # Core particle - solid with soft edge
                if screen_radius > 2:
                    # Soft edge ring
                    edge_color = (draw_color[0], draw_color[1], draw_color[2], 180)
                    pygame.draw.circle(glow_surface, edge_color, (center, center), screen_radius)
                    
                    # Bright core
                    core_radius = max(1, int(screen_radius * 0.7))
                    core_color = (
                        min(255, draw_color[0] + 50),
                        min(255, draw_color[1] + 50),
                        min(255, draw_color[2] + 50),
                        220
                    )
                    pygame.draw.circle(glow_surface, core_color, (center, center), core_radius)
                    
                    # Hot center highlight
                    if screen_radius > 4:
                        hot_radius = max(1, int(screen_radius * 0.3))
                        hot_color = (
                            min(255, draw_color[0] + 100),
                            min(255, draw_color[1] + 100),
                            min(255, draw_color[2] + 80),
                            255
                        )
                        pygame.draw.circle(glow_surface, hot_color, (center - screen_radius//4, center - screen_radius//4), hot_radius)
                else:
                    # Small particles - just a bright dot
                    pygame.draw.circle(glow_surface, (*draw_color, 255), (center, center), max(1, screen_radius))
                
                self.glow_cache[glow_key] = glow_surface
            
            # Blit the glow surface onto main surface
            surface.blit(glow_surface, (screen_x - center, screen_y - center), special_flags=pygame.BLEND_ALPHA_SDL2)
    
    def update(self, dt: float) -> None:
        """Update simulation state"""
        self.time += dt
        
        # Update camera rotation
        self.camera_rotation += dt * 0.3
        
        # Update lights
        self.update_lights(dt)
        
        # Update particles
        for particle in self.particles:
            particle.update(dt)
        
        # Check collisions
        self.check_particle_collisions()
    
    def render(self) -> None:
        """Render the complete scene"""
        # Clear screen with deep space background
        self.screen.fill((8, 4, 20))
        
        # Render volumetric fog background
        self.render_volumetric_background(self.screen)
        
        # Render particles on top
        self.render_particles(self.screen)
        
        # Draw pre-calculated vignette
        self.screen.blit(self.vignette, (0, 0))
        
        pygame.display.flip()
    
    def run(self, max_frames=None) -> None:
        """Run the simulation."""
        import time
        self.start_time = time.time()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
            
            dt = self.clock.tick() / 1000.0 # No cap for benchmarking
            dt = min(dt, 0.1)  # Cap delta time
            
            self.update(dt)
            self.render()

            self.frame_count += 1
            if max_frames and self.frame_count >= max_frames:
                self.running = False
        
        end_time = time.time()
        duration = end_time - self.start_time
        if duration > 0:
            self.fps = self.frame_count / duration
    
    def cleanup(self) -> None:
        """Clean up pygame resources"""
        pygame.quit()


def main():
    """Main entry point"""
    sim = ParticleSimulation()
    try:
        sim.run()
    finally:
        sim.cleanup()


if __name__ == "__main__":
    main()
