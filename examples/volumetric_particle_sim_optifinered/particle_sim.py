#!/usr/bin/env python3
"""Minimal headless particle simulation for benchmark."""

import random
import math
from dataclasses import dataclass

WORLD_BOUNDS = 200.0
PARTICLE_RADIUS = 8.0
GRAVITY = 0.0
BOUNCE_DAMPING = 0.9

@dataclass
class Vector3:
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
    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

@dataclass
class Particle:
    position: Vector3
    velocity: Vector3
    radius: float
    mass: float
    emission: float
    def update(self, dt: float) -> None:
        self.velocity.y -= GRAVITY * dt
        self.position.x += self.velocity.x * dt
        self.position.y += self.velocity.y * dt
        self.position.z += self.velocity.z * dt
        # simple bounds bounce
        for axis in ['x','y','z']:
            v = getattr(self.position, axis)
            if v < -WORLD_BOUNDS:
                setattr(self.position, axis, -WORLD_BOUNDS)
                setattr(self.velocity, axis, getattr(self.velocity, axis) * -BOUNCE_DAMPING)
            if v > WORLD_BOUNDS:
                setattr(self.position, axis, WORLD_BOUNDS)
                setattr(self.velocity, axis, getattr(self.velocity, axis) * -BOUNCE_DAMPING)

def simulate_frames(frames: int, dt: float = 1.0/60.0) -> None:
    particles = []
    for i in range(12):
        pos = Vector3(
            random.uniform(-WORLD_BOUNDS*0.8, WORLD_BOUNDS*0.8),
            random.uniform(-WORLD_BOUNDS*0.8, WORLD_BOUNDS*0.8),
            random.uniform(-WORLD_BOUNDS*0.8, WORLD_BOUNDS*0.8),
        )
        vel = Vector3(
            random.uniform(-2.0, 2.0),
            random.uniform(-1.0, 3.0),
            random.uniform(-2.0, 2.0),
        )
        radius = random.uniform(PARTICLE_RADIUS*0.5, PARTICLE_RADIUS*1.5)
        mass = radius ** 2
        emission = random.uniform(0.0, 1.0)
        particles.append(Particle(pos, vel, radius, mass, emission))
    for _ in range(frames):
        for p in particles:
            p.update(dt)
