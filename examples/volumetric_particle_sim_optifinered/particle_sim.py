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
import time

_frame_count = 0
_fps_start_time = time.time()
_current_fps = 0.0
_total_frames_rendered = 0
_total_time_elapsed = 0.0

def get_fps():
    return _current_fps

def get_total_frames_rendered():
    return _total_frames_rendered

def get_total_time_elapsed():
    return _total_time_elapsed

import math
import random
from dataclasses import dataclass
from typing import List, Tuple
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
        """Calculate beautiful shading for a single particle"""
        base_color = list(particle.color)
        # Soft ambient with slight blue tint for depth
        final_color = [c * 0.15 + 10 for c in base_color]
        final_color[2] += 15  # Blue ambient boost
        
        for light in lights:
            # Calculate light direction and distance
            light_dir = (light.position - particle.position).normalize()
            light_dist = (light.position - particle.position).length()
            
            # Softer diffuse lighting with smoother falloff
            attenuation = light.intensity / (1.0 + light_dist * light_dist * 0.00008)
            attenuation = min(1.2, attenuation)  # Cap for softer look
            
            # Enhanced fresnel-like rim lighting for that glowy look
            fresnel = 1.0 - abs(view_dir.dot(light_dir))
            fresnel = fresnel ** 2  # Softer falloff
            
            # Color mixing with light
            final_color[0] += base_color[0] * light.color[0] * attenuation * (0.6 + fresnel * 0.4)
            final_color[1] += base_color[1] * light.color[1] * attenuation * (0.6 + fresnel * 0.4)
            final_color[2] += base_color[2] * light.color[2] * attenuation * (0.6 + fresnel * 0.4)
        
        # Add emission with bloom-like effect
        emission_boost = 1.0 + particle.emission * 0.8
        final_color[0] = final_color[0] * emission_boost + base_color[0] * particle.emission * 0.3
        final_color[1] = final_color[1] * emission_boost + base_color[1] * particle.emission * 0.3
        final_color[2] = final_color[2] * emission_boost + base_color[2] * particle.emission * 0.3
        
        # Soft HDR-like tone mapping for nicer color distribution
        final_color = [c / (1 + c / 300) for c in final_color]
        
        return (
            min(255, max(0, int(final_color[0]))),
            min(255, max(0, int(final_color[1]))),
            min(255, max(0, int(final_color[2])))
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
        
        self._init_particles()
        self._init_lights()
    
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
        INTENTIONALLY O(n²) - a major optimization opportunity!
        """
        for i in range(len(self.particles)):
            for j in range(i + 1, len(self.particles)):
                p1 = self.particles[i]
                p2 = self.particles[j]
                
                # Calculate distance between particles
                dx = p2.position.x - p1.position.x
                dy = p2.position.y - p1.position.y
                dz = p2.position.z - p1.position.z
                
                dist_sq = dx * dx + dy * dy + dz * dz
                min_dist = p1.radius + p2.radius
                
                if dist_sq < min_dist * min_dist and dist_sq > 0:
                    dist = math.sqrt(dist_sq)
                    
                    # Normalize collision vector
                    nx = dx / dist
                    ny = dy / dist
                    nz = dz / dist
                    
                    # Relative velocity
                    dvx = p2.velocity.x - p1.velocity.x
                    dvy = p2.velocity.y - p1.velocity.y
                    dvz = p2.velocity.z - p1.velocity.z
                    
                    # Relative velocity along collision normal
                    dvn = dvx * nx + dvy * ny + dvz * nz
                    
                    if dvn < 0:  # Particles moving toward each other
                        # Mass-weighted impulse
                        total_mass = p1.mass + p2.mass
                        impulse = -2.0 * dvn / total_mass
                        
                        p1.velocity.x -= impulse * p2.mass * nx * BOUNCE_DAMPING
                        p1.velocity.y -= impulse * p2.mass * ny * BOUNCE_DAMPING
                        p1.velocity.z -= impulse * p2.mass * nz * BOUNCE_DAMPING
                        
                        p2.velocity.x += impulse * p1.mass * nx * BOUNCE_DAMPING
                        p2.velocity.y += impulse * p1.mass * ny * BOUNCE_DAMPING
                        p2.velocity.z += impulse * p1.mass * nz * BOUNCE_DAMPING
                        
                        # Separate particles
                        overlap = min_dist - dist
                        p1.position.x -= nx * overlap * 0.5
                        p1.position.y -= ny * overlap * 0.5
                        p1.position.z -= nz * overlap * 0.5
                        p2.position.x += nx * overlap * 0.5
                        p2.position.y += ny * overlap * 0.5
                        p2.position.z += nz * overlap * 0.5
    
    def render_volumetric_background(self, surface: pygame.Surface) -> None:
        """
        Render beautiful gradient background with nebula-like effects.
        INTENTIONALLY SLOW - per-pixel calculations!
        """
        # Create a background surface with smooth gradients
        sample_rate = 8  # Finer sampling for smoother look
        
        for y in range(0, self.renderer.height, sample_rate):
            for x in range(0, self.renderer.width, sample_rate):
                # Normalized coordinates
                nx = x / self.renderer.width
                ny = y / self.renderer.height
                
                # Animated swirling effect based on time and position
                swirl = math.sin(nx * 3 + self.time * 0.5) * math.cos(ny * 2 + self.time * 0.3)
                swirl2 = math.cos(nx * 2 - self.time * 0.4) * math.sin(ny * 4 + self.time * 0.6)
                
                # Deep space gradient - dark blue to purple to deep magenta
                base_r = int(15 + 25 * ny + 15 * swirl)
                base_g = int(5 + 15 * (1 - ny) + 10 * swirl2)
                base_b = int(35 + 40 * ny + 20 * abs(swirl))
                
                # Add subtle nebula clouds
                cloud = math.sin(nx * 6 + ny * 4 + self.time * 0.2) * 0.5 + 0.5
                cloud *= math.cos(nx * 3 - ny * 5 + self.time * 0.15) * 0.5 + 0.5
                
                base_r = int(min(60, base_r + cloud * 30))
                base_g = int(min(40, base_g + cloud * 15))
                base_b = int(min(80, base_b + cloud * 25))
                
                # Calculate ray direction for this pixel
                ndc_x = (x / self.renderer.width) * 2 - 1
                ndc_y = 1 - (y / self.renderer.height) * 2
                
                fov_scale = math.tan(math.radians(self.renderer.fov / 2))
                ray_dir = Vector3(
                    ndc_x * fov_scale * self.renderer.aspect_ratio,
                    ndc_y * fov_scale,
                    1.0
                ).normalize()
                
                # Rotate ray by camera rotation
                cos_r = math.cos(self.camera_rotation)
                sin_r = math.sin(self.camera_rotation)
                rot_ray = Vector3(
                    ray_dir.x * cos_r + ray_dir.z * sin_r,
                    ray_dir.y,
                    -ray_dir.x * sin_r + ray_dir.z * cos_r
                )
                
                # Raymarch for volumetric fog
                fog_color = self.renderer.calculate_volumetric_fog(
                    self.camera_position, rot_ray,
                    self.particles, self.lights,
                    WORLD_BOUNDS * 3
                )
                
                # Blend fog with beautiful background
                fog_strength = (fog_color[0] + fog_color[1] + fog_color[2]) / 3
                blend = min(1.0, fog_strength * 2)
                
                final_r = int(base_r * (1 - blend) + fog_color[0] * 255 * blend)
                final_g = int(base_g * (1 - blend) + fog_color[1] * 255 * blend)
                final_b = int(base_b * (1 - blend) + fog_color[2] * 255 * blend)
                
                color = (
                    min(255, max(0, final_r)),
                    min(255, max(0, final_g)),
                    min(255, max(0, final_b))
                )
                
                # Fill the sampled area
                pygame.draw.rect(surface, color, (x, y, sample_rate, sample_rate))
    
    def render_particles(self, surface: pygame.Surface) -> None:
        """Render particles with depth sorting and beautiful soft shading"""
        # Calculate view direction
        view_dir = Vector3(
            math.sin(self.camera_rotation),
            0,
            math.cos(self.camera_rotation)
        )
        
        # Sort particles by depth - INTENTIONALLY using slow sort key
        # that recalculates projection for each comparison
        sorted_particles = sorted(
            self.particles,
            key=lambda p: -(
                (p.position.x - self.camera_position.x) * math.sin(self.camera_rotation) +
                (p.position.z - self.camera_position.z) * math.cos(self.camera_rotation)
            )
        )
        
        for particle in sorted_particles:
            # Project particle position
            screen_x, screen_y, depth = self.renderer.project_point(
                particle.position, self.camera_position, self.camera_rotation
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
            atmosphere_color = (
                int(color[0] * (1 - depth_fade * 0.5) + 80 * depth_fade * 0.5),
                int(color[1] * (1 - depth_fade * 0.4) + 60 * depth_fade * 0.4),
                int(color[2] * (1 - depth_fade * 0.2) + 120 * depth_fade * 0.2)
            )
            color = atmosphere_color
            
            # Create soft glow surface with alpha blending - INTENTIONALLY per-particle
            glow_surface = pygame.Surface((screen_radius * 6, screen_radius * 6), pygame.SRCALPHA)
            center = screen_radius * 3
            
            # Outer soft glow (large, very transparent)
            for glow_i in range(8, 0, -1):
                glow_radius = int(screen_radius * (1 + glow_i * 0.5))
                alpha = int(25 * (1 - glow_i / 9) * (0.5 + particle.emission * 0.5))
                glow_color = (color[0], color[1], color[2], alpha)
                if glow_radius > 0:
                    pygame.draw.circle(glow_surface, glow_color, (center, center), glow_radius)
            
            # Inner brighter glow
            for glow_i in range(4, 0, -1):
                glow_radius = int(screen_radius * (1 + glow_i * 0.2))
                alpha = int(60 * (1 - glow_i / 5))
                glow_color = (
                    min(255, color[0] + 30),
                    min(255, color[1] + 30),
                    min(255, color[2] + 30),
                    alpha
                )
                if glow_radius > 0:
                    pygame.draw.circle(glow_surface, glow_color, (center, center), glow_radius)
            
            # Core particle - solid with soft edge
            if screen_radius > 2:
                # Soft edge ring
                edge_color = (color[0], color[1], color[2], 180)
                pygame.draw.circle(glow_surface, edge_color, (center, center), screen_radius)
                
                # Bright core
                core_radius = max(1, int(screen_radius * 0.7))
                core_color = (
                    min(255, color[0] + 50),
                    min(255, color[1] + 50),
                    min(255, color[2] + 50),
                    220
                )
                pygame.draw.circle(glow_surface, core_color, (center, center), core_radius)
                
                # Hot center highlight
                if screen_radius > 4:
                    hot_radius = max(1, int(screen_radius * 0.3))
                    hot_color = (
                        min(255, color[0] + 100),
                        min(255, color[1] + 100),
                        min(255, color[2] + 80),
                        255
                    )
                    pygame.draw.circle(glow_surface, hot_color, (center - screen_radius//4, center - screen_radius//4), hot_radius)
            else:
                # Small particles - just a bright dot
                pygame.draw.circle(glow_surface, (*color, 255), (center, center), max(1, screen_radius))
            
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
        
        # Draw subtle vignette effect - INTENTIONALLY slow per-pixel
        vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(0, SCREEN_HEIGHT, 16):
            for x in range(0, SCREEN_WIDTH, 16):
                # Distance from center normalized
                dx = (x - SCREEN_WIDTH / 2) / (SCREEN_WIDTH / 2)
                dy = (y - SCREEN_HEIGHT / 2) / (SCREEN_HEIGHT / 2)
                dist = math.sqrt(dx * dx + dy * dy)
                alpha = int(min(80, dist * dist * 60))
                pygame.draw.rect(vignette, (0, 0, 0, alpha), (x, y, 16, 16))
        self.screen.blit(vignette, (0, 0))
        
        pygame.display.flip()
    
    def run(self) -> None:
        """Run the simulation."""
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

            _frame_count += 1
            _total_frames_rendered += 1
            _total_time_elapsed += dt
            elapsed = time.time() - _fps_start_time
            if elapsed >= 1.0:
                _current_fps = _frame_count / elapsed
                _frame_count = 0
                _fps_start_time = time.time()
    
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
    import sys
    run_duration = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    sim = ParticleSimulation()
    start_time = time.time()
    sim.running = True
    try:
        while sim.running and (time.time() - start_time < run_duration):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sim.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        sim.running = False
            
            dt = sim.clock.tick(60) / 1000.0
            dt = min(dt, 0.1)  # Cap delta time
            
            sim.update(dt)
            sim.render()

            _frame_count += 1
            _total_frames_rendered += 1
            _total_time_elapsed += dt
            elapsed = time.time() - _fps_start_time
            if elapsed >= 1.0:
                _current_fps = _frame_count / elapsed
                _frame_count = 0
                _fps_start_time = time.time()
    finally:
        sim.cleanup()
        print(f"FINAL_FPS:{get_fps()}")
        print(f"TOTAL_FRAMES:{get_total_frames_rendered()}")
        print(f"TOTAL_TIME:{get_total_time_elapsed()}")
