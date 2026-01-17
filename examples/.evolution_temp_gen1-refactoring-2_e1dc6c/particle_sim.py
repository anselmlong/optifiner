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
import time

# Set SDL to use dummy video driver if no display available (for headless testing)
if os.environ.get("SDL_VIDEODRIVER") is None and os.environ.get("DISPLAY") is None:
    # Check if we're in a headless environment
    try:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    except:
        pass

import pygame


# Configuration
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
NUM_PARTICLES = 300
NUM_LIGHTS = 4
FOG_DENSITY = 0.02
RAYMARCH_STEPS = 16
PARTICLE_RADIUS = 8.0
GRAVITY = 0.15
BOUNCE_DAMPING = 0.7
WORLD_BOUNDS = 200.0


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
        
    def project_point(self, point: Vector3, camera_pos: Vector3, camera_rot: float) -> Tuple[int, int, float]:
        """Project 3D point to 2D screen coordinates"""
        # Rotate point around Y axis relative to camera
        cos_r = math.cos(camera_rot)
        sin_r = math.sin(camera_rot)
        
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
    
    def calculate_volumetric_fog(self, ray_origin: Vector3, ray_dir: Vector3, 
                                  particles: List[Particle], lights: List[Light],
                                  max_distance: float) -> Tuple[float, float, float]:
        """
        Raymarch through the scene to calculate volumetric fog contribution.
        This is INTENTIONALLY slow - per-pixel, no vectorization.
        """
        accumulated_color = [0.0, 0.0, 0.0]
        accumulated_density = 0.0
        step_size = max_distance / RAYMARCH_STEPS
        
        for step in range(RAYMARCH_STEPS):
            # Calculate current position along ray
            t = step * step_size
            current_pos = Vector3(
                ray_origin.x + ray_dir.x * t,
                ray_origin.y + ray_dir.y * t,
                ray_origin.z + ray_dir.z * t
            )
            
            # Calculate density at this point (influenced by nearby particles)
            local_density = 0.0
            local_color = [0.0, 0.0, 0.0]
            
            # Check contribution from each particle - O(n) per raymarch step!
            for particle in particles:
                dist = (current_pos - particle.position).length()
                if dist < particle.radius * 3:
                    # Falloff based on distance
                    falloff = 1.0 - (dist / (particle.radius * 3))
                    falloff = max(0, falloff ** 2)
                    
                    local_density += falloff * 0.5
                    local_color[0] += particle.color[0] / 255.0 * falloff * particle.emission
                    local_color[1] += particle.color[1] / 255.0 * falloff * particle.emission
                    local_color[2] += particle.color[2] / 255.0 * falloff * particle.emission
            
            # Add light contribution at this point
            for light in lights:
                light_dist = (current_pos - light.position).length()
                if light_dist > 0:
                    # Calculate light falloff
                    attenuation = light.intensity / (1.0 + light_dist * light_dist * 0.0001)
                    local_color[0] += light.color[0] * attenuation * 0.1
                    local_color[1] += light.color[1] * attenuation * 0.1
                    local_color[2] += light.color[2] * attenuation * 0.1
            
            # Accumulate fog using front-to-back compositing
            if local_density > 0:
                alpha = 1.0 - math.exp(-local_density * step_size * FOG_DENSITY)
                alpha = min(1.0, alpha)
                
                remaining = 1.0 - accumulated_density
                accumulated_color[0] += local_color[0] * alpha * remaining
                accumulated_color[1] += local_color[1] * alpha * remaining
                accumulated_color[2] += local_color[2] * alpha * remaining
                accumulated_density += alpha * remaining
                
                if accumulated_density > 0.99:
                    break
        
        return (
            min(1.0, accumulated_color[0]),
            min(1.0, accumulated_color[1]),
            min(1.0, accumulated_color[2])
        )
    
    def shade_particle(self, particle: Particle, lights: List[Light], 
                       view_dir: Vector3) -> Tuple[int, int, int]:
        """Calculate shading for a single particle"""
        base_color = list(particle.color)
        final_color = [c * 0.1 for c in base_color]  # Ambient
        
        for light in lights:
            # Calculate light direction and distance
            light_dir = (light.position - particle.position).normalize()
            light_dist = (light.position - particle.position).length()
            
            # Diffuse lighting with quadratic falloff
            attenuation = light.intensity / (1.0 + light_dist * light_dist * 0.0001)
            
            # Fresnel-like rim lighting
            fresnel = 1.0 - abs(view_dir.dot(light_dir))
            fresnel = fresnel ** 3
            
            final_color[0] += base_color[0] * light.color[0] * attenuation * (0.7 + fresnel * 0.3)
            final_color[1] += base_color[1] * light.color[1] * attenuation * (0.7 + fresnel * 0.3)
            final_color[2] += base_color[2] * light.color[2] * attenuation * (0.7 + fresnel * 0.3)
        
        # Add emission
        final_color[0] += base_color[0] * particle.emission * 0.5
        final_color[1] += base_color[1] * particle.emission * 0.5
        final_color[2] += base_color[2] * particle.emission * 0.5
        
        return (
            min(255, int(final_color[0])),
            min(255, int(final_color[1])),
            min(255, int(final_color[2]))
        )


class ParticleSimulation:
    """Main simulation class"""
    
    def __init__(self):
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
        
        self.fps_history: List[float] = []
        self.frame_count = 0
        
        self._init_particles()
        self._init_lights()
    
    def _init_particles(self) -> None:
        """Initialize particles with random positions and properties"""
        colors = [
            (255, 100, 50),   # Orange
            (50, 150, 255),   # Blue
            (255, 50, 150),   # Pink
            (50, 255, 150),   # Cyan
            (255, 255, 100),  # Yellow
            (150, 100, 255),  # Purple
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
            emission = random.uniform(0.2, 1.0) if random.random() > 0.7 else 0.0
            
            self.particles.append(Particle(pos, vel, color, radius, mass, emission))
    
    def _init_lights(self) -> None:
        """Initialize orbiting lights"""
        light_colors = [
            (1.0, 0.8, 0.6),
            (0.6, 0.8, 1.0),
            (1.0, 0.6, 0.8),
            (0.8, 1.0, 0.6),
        ]
        
        for i in range(NUM_LIGHTS):
            phase = i * (2 * math.pi / NUM_LIGHTS)
            self.lights.append(Light(
                position=Vector3(0, 0, 0),
                color=light_colors[i % len(light_colors)],
                intensity=150.0,
                orbit_radius=WORLD_BOUNDS * 0.6,
                orbit_speed=0.5 + i * 0.1,
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
        Check and resolve particle-particle collisions using a spatial grid.
        """
        particles = self.particles
        num_particles = len(particles)
        if num_particles == 0:
            return

        # Grid size based on max particle radius (PARTICLE_RADIUS * 1.5)
        # Max min_dist is 2 * 1.5 * PARTICLE_RADIUS = 3 * PARTICLE_RADIUS = 24.0
        grid_size = 24.0
        grid = {}
        
        for i in range(num_particles):
            p = particles[i]
            pos = p.position
            gx = int(pos.x / grid_size)
            gy = int(pos.y / grid_size)
            gz = int(pos.z / grid_size)
            key = (gx, gy, gz)
            if key not in grid:
                grid[key] = []
            grid[key].append(i)
            
        for i in range(num_particles):
            p1 = particles[i]
            pos1 = p1.position
            p1x, p1y, p1z = pos1.x, pos1.y, pos1.z
            r1 = p1.radius
            
            gx = int(p1x / grid_size)
            gy = int(p1y / grid_size)
            gz = int(p1z / grid_size)
            
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    for dz in range(-1, 2):
                        neighbor_key = (gx + dx, gy + dy, gz + dz)
                        if neighbor_key in grid:
                            for j in grid[neighbor_key]:
                                if j <= i:
                                    continue
                                
                                p2 = particles[j]
                                pos2 = p2.position
                                dx_val = pos2.x - p1x
                                dy_val = pos2.y - p1y
                                dz_val = pos2.z - p1z
                                
                                dist_sq = dx_val * dx_val + dy_val * dy_val + dz_val * dz_val
                                min_dist = r1 + p2.radius
                                
                                if dist_sq < min_dist * min_dist and dist_sq > 0:
                                    dist = math.sqrt(dist_sq)
                                    
                                    # Normalize collision vector
                                    nx = dx_val / dist
                                    ny = dy_val / dist
                                    nz = dz_val / dist
                                    
                                    # Relative velocity
                                    v1 = p1.velocity
                                    v2 = p2.velocity
                                    dvx = v2.x - v1.x
                                    dvy = v2.y - v1.y
                                    dvz = v2.z - v1.z
                                    
                                    # Relative velocity along collision normal
                                    dvn = dvx * nx + dvy * ny + dvz * nz
                                    
                                    if dvn < 0:  # Particles moving toward each other
                                        # Mass-weighted impulse
                                        total_mass = p1.mass + p2.mass
                                        impulse = -2.0 * dvn / total_mass
                                        
                                        factor1 = impulse * p2.mass * BOUNCE_DAMPING
                                        v1.x -= factor1 * nx
                                        v1.y -= factor1 * ny
                                        v1.z -= factor1 * nz
                                        
                                        factor2 = impulse * p1.mass * BOUNCE_DAMPING
                                        v2.x += factor2 * nx
                                        v2.y += factor2 * ny
                                        v2.z += factor2 * nz
                                        
                                        # Separate particles
                                        overlap = min_dist - dist
                                        sep_x = nx * overlap * 0.5
                                        sep_y = ny * overlap * 0.5
                                        sep_z = nz * overlap * 0.5
                                        pos1.x -= sep_x
                                        pos1.y -= sep_y
                                        pos1.z -= sep_z
                                        pos2.x += sep_x
                                        pos2.y += sep_y
                                        pos2.z += sep_z
    
    def render_volumetric_background(self, surface: pygame.Surface) -> None:
        """
        Render volumetric fog background - Optimized version with ray-particle pre-filtering.
        """
        sample_rate = 32
        width = self.renderer.width
        height = self.renderer.height
        fov = self.renderer.fov
        aspect_ratio = self.renderer.aspect_ratio
        camera_pos = self.camera_position
        camera_rot = self.camera_rotation
        
        # Pre-calculate camera-related values
        fov_scale = math.tan(math.radians(fov / 2))
        cos_r = math.cos(camera_rot)
        sin_r = math.sin(camera_rot)
        
        # Pre-extract particle and light data
        particles = self.particles
        lights = self.lights
        max_distance = WORLD_BOUNDS * 3
        step_size = max_distance / RAYMARCH_STEPS
        fog_density_step = step_size * FOG_DENSITY
        
        ox, oy, oz = camera_pos.x, camera_pos.y, camera_pos.z
        
        p_data = []
        for p in particles:
            pos = p.position
            pdx, pdy, pdz = pos.x - ox, pos.y - oy, pos.z - oz
            v_sq = pdx*pdx + pdy*pdy + pdz*pdz
            r3 = p.radius * 3.0
            r3_sq = r3 * r3
            inv_r3 = 1.0 / r3 if r3 > 0 else 0.0
            c = p.color
            e = p.emission / 255.0
            p_data.append((pos.x, pos.y, pos.z, pdx, pdy, pdz, v_sq, r3, r3_sq, inv_r3, c[0] * e, c[1] * e, c[2] * e))
            
        l_data = []
        for l in lights:
            pos = l.position
            c = l.color
            l_data.append((pos.x, pos.y, pos.z, l.intensity, c[0] * 0.1, c[1] * 0.1, c[2] * 0.1))

        for y in range(0, height, sample_rate):
            ndc_y = 1 - (y / height) * 2
            ray_y = ndc_y * fov_scale
            
            for x in range(0, width, sample_rate):
                ndc_x = (x / width) * 2 - 1
                ray_x = ndc_x * fov_scale * aspect_ratio
                
                # Combined rotation and normalization
                mag = math.sqrt(ray_x*ray_x + ray_y*ray_y + 1.0)
                rx, ry, rz = ray_x/mag, ray_y/mag, 1.0/mag
                
                # Rotate ray
                drx = rx * cos_r + rz * sin_r
                dry = ry
                drz = -rx * sin_r + rz * cos_r
                
                # Pre-filter particles for this ray
                ray_particles = []
                for p_x, p_y, p_z, pdx, pdy, pdz, v_sq, r3, r3_sq, inv_r3, er, eg, eb in p_data:
                    v_dot_d = pdx * drx + pdy * dry + pdz * drz
                    if -r3 < v_dot_d < max_distance + r3:
                        dist_to_ray_sq = v_sq - v_dot_d*v_dot_d
                        if dist_to_ray_sq < r3_sq:
                            half_width = math.sqrt(r3_sq - dist_to_ray_sq)
                            ray_particles.append((inv_r3, er, eg, eb, v_dot_d - half_width, v_dot_d + half_width, dist_to_ray_sq, v_dot_d))
                
                # Raymarch
                accum_r, accum_g, accum_b = 0.0, 0.0, 0.0
                accumulated_density = 0.0
                
                if ray_particles or l_data:
                    for step in range(RAYMARCH_STEPS):
                        t = step * step_size
                        px, py, pz = ox + drx * t, oy + dry * t, oz + drz * t
                        
                        local_density = 0.0
                        lr, lg, lb = 0.0, 0.0, 0.0
                        
                        for inv_r3, er, eg, eb, t_min, t_max, d2r_sq, vdd in ray_particles:
                            if t_min <= t <= t_max:
                                dist = math.sqrt(d2r_sq + (t - vdd)**2)
                                falloff = 1.0 - (dist * inv_r3)
                                falloff *= falloff
                                
                                local_density += falloff * 0.5
                                lr += er * falloff
                                lg += eg * falloff
                                lb += eb * falloff
                        
                        for lx, ly, lz, l_int, l_r1, l_g1, l_b1 in l_data:
                            ldx, ldy, ldz = px - lx, py - ly, pz - lz
                            ldist_sq = ldx*ldx + ldy*ldy + ldz*ldz
                            if ldist_sq > 0:
                                attenuation = l_int / (1.0 + ldist_sq * 0.0001)
                                lr += l_r1 * attenuation
                                lg += l_g1 * attenuation
                                lb += l_b1 * attenuation
                        
                        if local_density > 0:
                            alpha = 1.0 - math.exp(-local_density * fog_density_step)
                            remaining = 1.0 - accumulated_density
                            weight = alpha * remaining
                            accum_r += lr * weight
                            accum_g += lg * weight
                            accum_b += lb * weight
                            accumulated_density += weight
                            
                            if accumulated_density > 0.99:
                                break
                
                color = (
                    int(min(1.0, accum_r) * 255),
                    int(min(1.0, accum_g) * 255),
                    int(min(1.0, accum_b) * 255)
                )
                pygame.draw.rect(surface, color, (x, y, sample_rate, sample_rate))
    
    def render_particles(self, surface: pygame.Surface) -> None:
        """Render particles with depth sorting and shading - Optimized"""
        camera_rot = self.camera_rotation
        camera_pos = self.camera_position
        cos_r = math.cos(camera_rot)
        sin_r = math.sin(camera_rot)
        
        cx, cy, cz = camera_pos.x, camera_pos.y, camera_pos.z
        
        # Pre-calculate view direction
        view_dir_x = sin_r
        view_dir_z = cos_r
        
        # Sort particles by depth
        # Depth = (p.x - cx) * sin_r + (p.z - cz) * cos_r
        sorted_particles = sorted(
            self.particles,
            key=lambda p: -((p.position.x - cx) * sin_r + (p.position.z - cz) * cos_r)
        )
        
        width = self.renderer.width
        height = self.renderer.height
        aspect_ratio = self.renderer.aspect_ratio
        fov_scale = math.tan(math.radians(self.renderer.fov / 2))
        
        lights = self.lights
        l_data = []
        for l in lights:
            l_pos = l.position
            l_color = l.color
            l_data.append((l_pos.x, l_pos.y, l_pos.z, l.intensity, l_color[0], l_color[1], l_color[2]))

        for particle in sorted_particles:
            pos = particle.position
            px, py, pz = pos.x, pos.y, pos.z
            
            rel_x = px - cx
            rel_y = py - cy
            rel_z = pz - cz
            
            rot_x = rel_x * cos_r - rel_z * sin_r
            rot_z = rel_x * sin_r + rel_z * cos_r
            
            if rot_z <= 0.1:
                continue
            
            # Perspective projection
            screen_x = int((rot_x / (rot_z * fov_scale * aspect_ratio)) * width / 2 + width / 2)
            screen_y = int((-rel_y / (rot_z * fov_scale)) * height / 2 + height / 2)
            
            # Calculate screen-space radius
            screen_radius = int(particle.radius * 400 / rot_z)
            if screen_radius < 1:
                continue
            
            # Calculate shading (inlined shade_particle)
            base_color = particle.color
            final_r = base_color[0] * 0.1
            final_g = base_color[1] * 0.1
            final_b = base_color[2] * 0.1
            
            for lx, ly, lz, l_int, l_cr, l_cg, l_cb in l_data:
                ldx, ldy, ldz = lx - px, ly - py, lz - pz
                l_dist_sq = ldx*ldx + ldy*ldy + ldz*ldz
                
                if l_dist_sq > 0:
                    l_dist = math.sqrt(l_dist_sq)
                    inv_l_dist = 1.0 / l_dist
                    lnx, lny, lnz = ldx * inv_l_dist, ldy * inv_l_dist, ldz * inv_l_dist
                    
                    attenuation = l_int / (1.0 + l_dist_sq * 0.0001)
                    
                    # view_dir is (sin_r, 0, cos_r)
                    # dot product: view_dir.dot(light_dir)
                    dot = view_dir_x * lnx + view_dir_z * lnz
                    fresnel = (1.0 - abs(dot)) ** 3
                    
                    factor = attenuation * (0.7 + fresnel * 0.3)
                    final_r += base_color[0] * l_cr * factor
                    final_g += base_color[1] * l_cg * factor
                    final_b += base_color[2] * l_cb * factor
            
            # Add emission
            em = particle.emission * 0.5
            final_r += base_color[0] * em
            final_g += base_color[1] * em
            final_b += base_color[2] * em
            
            color = (
                min(255, int(final_r)),
                min(255, int(final_g)),
                min(255, int(final_b))
            )
            
            # Draw particle with glow effect
            if particle.emission > 0:
                for glow_i in range(3, 0, -1):
                    glow_radius = screen_radius + glow_i * 3
                    glow_alpha = particle.emission * (1 - glow_i / 4)
                    glow_color = (
                        int(color[0] * glow_alpha),
                        int(color[1] * glow_alpha),
                        int(color[2] * glow_alpha)
                    )
                    if glow_radius > 0:
                        pygame.draw.circle(surface, glow_color, (screen_x, screen_y), glow_radius)
            
            # Draw main particle
            pygame.draw.circle(surface, color, (screen_x, screen_y), screen_radius)
            
            # Highlight
            r_offset = particle.radius * 0.3
            h_rel_x = rel_x - sin_r * r_offset
            h_rel_y = rel_y + r_offset
            h_rel_z = rel_z - cos_r * r_offset
            
            h_rot_x = h_rel_x * cos_r - h_rel_z * sin_r
            h_rot_z = h_rel_x * sin_r + h_rel_z * cos_r
            
            if h_rot_z > 0.1:
                hx = int((h_rot_x / (h_rot_z * fov_scale * aspect_ratio)) * width / 2 + width / 2)
                hy = int((-h_rel_y / (h_rot_z * fov_scale)) * height / 2 + height / 2)
                
                highlight_radius = max(1, screen_radius // 4)
                highlight_color = (
                    min(255, color[0] + 100),
                    min(255, color[1] + 100),
                    min(255, color[2] + 100)
                )
                pygame.draw.circle(surface, highlight_color, (hx, hy), highlight_radius)
    
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
        # Clear screen with dark background
        self.screen.fill((5, 5, 15))
        
        # Render volumetric fog background
        self.render_volumetric_background(self.screen)
        
        # Render particles on top
        self.render_particles(self.screen)
        
        # Draw FPS counter
        fps = self.clock.get_fps()
        self.fps_history.append(fps)
        if len(self.fps_history) > 60:
            self.fps_history.pop(0)
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        
        font = pygame.font.Font(None, 36)
        fps_text = font.render(f"FPS: {avg_fps:.1f}", True, (255, 255, 255))
        self.screen.blit(fps_text, (10, 10))
        
        particles_text = font.render(f"Particles: {len(self.particles)}", True, (255, 255, 255))
        self.screen.blit(particles_text, (10, 40))
        
        pygame.display.flip()
    
    def run(self, max_frames: int = None) -> float:
        """
        Run the simulation.
        
        Args:
            max_frames: If set, stop after this many frames and return average FPS
            
        Returns:
            Average FPS if max_frames is set, otherwise 0
        """
        self.frame_count = 0
        start_time = time.time()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
            
            dt = self.clock.tick(60) / 1000.0
            dt = min(dt, 0.1)  # Cap delta time
            
            self.update(dt)
            self.render()
            
            self.frame_count += 1
            
            if max_frames and self.frame_count >= max_frames:
                break
        
        elapsed = time.time() - start_time
        avg_fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        return avg_fps
    
    def cleanup(self) -> None:
        """Clean up pygame resources"""
        pygame.quit()


def get_simulation_stats(sim: ParticleSimulation) -> dict:
    """Get current simulation statistics for validation"""
    return {
        'num_particles': len(sim.particles),
        'num_lights': len(sim.lights),
        'camera_rotation': sim.camera_rotation,
        'time': sim.time,
        'particles_in_bounds': sum(
            1 for p in sim.particles 
            if abs(p.position.x) <= WORLD_BOUNDS and
               abs(p.position.y) <= WORLD_BOUNDS and
               abs(p.position.z) <= WORLD_BOUNDS
        ),
        'avg_particle_velocity': sum(
            p.velocity.length() for p in sim.particles
        ) / len(sim.particles) if sim.particles else 0,
    }


def main():
    """Main entry point"""
    sim = ParticleSimulation()
    try:
        sim.run()
    finally:
        sim.cleanup()


if __name__ == "__main__":
    main()
