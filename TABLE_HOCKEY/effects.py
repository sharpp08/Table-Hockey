"""Lightweight procedural particles, shockwaves, flashes and screen shake."""

from dataclasses import dataclass
import math
import random

import pygame

import config


@dataclass
class Particle:
    pos: pygame.Vector2
    velocity: pygame.Vector2
    color: tuple
    life: float
    max_life: float
    size: float
    gravity: float = 0.0
    shape: str = "circle"
    rotation: float = 0.0
    spin: float = 0.0


@dataclass
class Shockwave:
    pos: pygame.Vector2
    color: tuple
    life: float
    max_life: float
    max_radius: float


class EffectsManager:
    def __init__(self, quality, rng=None):
        self.quality = quality
        self.rng = rng or random.Random()
        self.particles = []
        self.waves = []
        self.flash = 0.0
        self.shake = 0.0
        self.celebrating = False
        self.celebration_color = config.COLOR_GOLD
        self.confetti_timer = 0.0
        self.bounds = (1280, 720)

    def configure(self, quality, bounds=None):
        self.quality = quality
        if bounds:
            self.bounds = bounds
        cap = max(0, self.quality.get("particles", 0) * 3)
        if cap and len(self.particles) > cap:
            del self.particles[:-cap]
        elif not cap:
            self.particles.clear()

    def clear(self):
        self.particles.clear()
        self.waves.clear()
        self.flash = 0.0
        self.shake = 0.0
        self.celebrating = False

    def impact(self, position, normal, color, strength=1.0):
        budget = self.quality.get("particles", 0)
        if budget:
            count = max(3, min(12, int(5 + strength * 4)))
            origin = pygame.Vector2(position)
            normal = pygame.Vector2(normal)
            base_angle = math.atan2(normal.y, normal.x)
            for _ in range(count):
                angle = base_angle + self.rng.uniform(-1.05, 1.05)
                speed = self.rng.uniform(80, 250) * (0.65 + strength * 0.35)
                velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
                life = self.rng.uniform(0.20, 0.48)
                self.particles.append(Particle(
                    origin.copy(), velocity, color, life, life,
                    self.rng.uniform(2.0, 5.5),
                ))
        self.waves.append(Shockwave(
            pygame.Vector2(position), color, 0.28, 0.28, 42 + 25 * strength
        ))
        self.shake = max(self.shake, min(8.0, 2.0 + strength * 3.0))

    def goal(self, position, color):
        self.flash = 1.0
        self.shake = 13.0
        origin = pygame.Vector2(position)
        count = self.quality.get("particles", 0)
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(100, 520)
            life = self.rng.uniform(0.45, 1.15)
            tint = color if self.rng.random() < 0.72 else config.COLOR_WHITE
            self.particles.append(Particle(
                origin.copy(),
                pygame.Vector2(math.cos(angle), math.sin(angle)) * speed,
                tint, life, life, self.rng.uniform(2.5, 7.5), gravity=110.0,
            ))
        for delay in (0.7, 1.0, 1.35):
            self.waves.append(Shockwave(origin.copy(), color, 0.8, 0.8, 170 * delay))

    def start_celebration(self, color):
        # Idempotent: GAMEOVER may request celebration every frame. Do not
        # reset the timer each frame or spawn an unbounded confetti stream.
        if not self.celebrating:
            self.celebration_color = color
            self.confetti_timer = 0.0
        self.celebrating = True

    def stop_celebration(self):
        self.celebrating = False

    def _confetti_burst(self):
        count = max(0, self.quality.get("particles", 0) // 3)
        width, height = self.bounds
        palette = [self.celebration_color, config.COLOR_GOLD,
                   config.COLOR_WHITE, config.COLOR_P1, config.COLOR_P2]
        for _ in range(count):
            life = self.rng.uniform(1.5, 3.0)
            self.particles.append(Particle(
                pygame.Vector2(self.rng.uniform(0, width), self.rng.uniform(-35, -5)),
                pygame.Vector2(self.rng.uniform(-55, 55), self.rng.uniform(80, 180)),
                self.rng.choice(palette), life, life, self.rng.uniform(3, 7),
                gravity=75.0, shape="rect", rotation=self.rng.uniform(0, 360),
                spin=self.rng.uniform(-300, 300),
            ))

    def update(self, dt):
        dt = min(max(dt, 0.0), 0.05)
        self.flash = max(0.0, self.flash - dt * 1.7)
        self.shake = max(0.0, self.shake - dt * 24.0)
        if self.celebrating:
            self.confetti_timer -= dt
            if self.confetti_timer <= 0:
                self.confetti_timer = 0.24
                self._confetti_burst()

        alive = []
        for particle in self.particles:
            particle.life -= dt
            if particle.life <= 0:
                continue
            particle.velocity.y += particle.gravity * dt
            particle.velocity *= math.exp(-0.42 * dt)
            particle.pos += particle.velocity * dt
            particle.rotation += particle.spin * dt
            alive.append(particle)
        cap = max(32, self.quality.get("particles", 0) * 4)
        self.particles = alive[-cap:]
        self.waves = [w for w in self.waves if w.life > 0]

    def shake_offset(self):
        if self.shake <= 0.2:
            return (0, 0)
        return (round(self.rng.uniform(-self.shake, self.shake)),
                round(self.rng.uniform(-self.shake, self.shake)))

    def draw(self, surface):
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for wave in self.waves:
            progress = 1.0 - wave.life / wave.max_life
            radius = max(1, int(wave.max_radius * progress))
            alpha = int(150 * (1.0 - progress) ** 1.4)
            pygame.draw.circle(layer, (*wave.color, alpha), wave.pos,
                               radius, max(1, int(4 * (1 - progress))))
        for particle in self.particles:
            ratio = particle.life / particle.max_life
            alpha = max(0, min(255, int(255 * ratio)))
            size = max(1, int(particle.size * (0.55 + 0.45 * ratio)))
            pos = (round(particle.pos.x), round(particle.pos.y))
            if particle.shape == "rect":
                rect = pygame.Rect(0, 0, size * 2, size)
                rect.center = pos
                pygame.draw.rect(layer, (*particle.color, alpha), rect, border_radius=1)
            else:
                pygame.draw.circle(layer, (*particle.color, alpha), pos, size)
        surface.blit(layer, (0, 0))
        if self.flash > 0:
            flash = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(110 * self.flash)))
            surface.blit(flash, (0, 0))
