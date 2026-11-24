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
        self.flash_color = config.COLOR_WHITE
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
        self.flash_color = config.COLOR_WHITE
        self.shake = 0.0
        self.celebrating = False

    def impact(self, position, normal, color, strength=1.0):
        self.flash = max(self.flash, min(0.22, 0.065 + strength * 0.075))
        self.flash_color = color
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
            # Sharp comic-book impact cuts mixed into the particle burst.
            for _ in range(max(2, count // 3)):
                angle = base_angle + self.rng.uniform(-1.35, 1.35)
                velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * self.rng.uniform(150, 340)
                life = self.rng.uniform(0.12, 0.24)
                self.particles.append(Particle(
                    origin.copy(), velocity, config.COLOR_WHITE, life, life,
                    self.rng.uniform(8.0, 16.0), shape="slash",
                    rotation=math.degrees(angle), spin=self.rng.uniform(-90, 90),
                ))
        self.waves.append(Shockwave(
            pygame.Vector2(position), color, 0.28, 0.28, 42 + 25 * strength
        ))
        self.shake = max(self.shake, min(8.0, 2.0 + strength * 3.0))

    def goal(self, position, color):
        self.flash = 0.72
        self.flash_color = color
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
        # Exponential decay avoids abrupt cut-offs and gives flashes a soft tail.
        self.flash *= math.exp(-dt * 8.5)
        if self.flash < 0.006:
            self.flash = 0.0
        self.shake *= math.exp(-dt * 9.0)
        if self.shake < 0.12:
            self.shake = 0.0
        if self.celebrating:
            self.confetti_timer -= dt
            if self.confetti_timer <= 0:
                self.confetti_timer = 0.24
                self._confetti_burst()

        for wave in self.waves:
            wave.life -= dt
        self.waves = [wave for wave in self.waves if wave.life > 0]

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

    def shake_offset(self):
        if self.shake <= 0.2:
            return (0, 0)
        return (round(self.rng.uniform(-self.shake, self.shake)),
                round(self.rng.uniform(-self.shake, self.shake)))

    def draw(self, surface):
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for wave in self.waves:
            progress = 1.0 - wave.life / wave.max_life
            # Ease outward, then dissolve smoothly instead of popping away.
            eased = 1.0 - (1.0 - progress) ** 2.4
            fade = (1.0 - progress) ** 1.35
            fade *= min(1.0, progress * 8.0)
            radius = max(1, int(wave.max_radius * eased))
            alpha = max(0, min(255, int(175 * fade)))
            pygame.draw.circle(layer, (*wave.color, alpha), wave.pos,
                               radius, max(1, int(4 * (1.0 - eased * 0.72))))
        for particle in self.particles:
            ratio = max(0.0, min(1.0, particle.life / particle.max_life))
            # Soft envelope: fade in quickly, linger, and fade out at the tail.
            fade_in = min(1.0, (1.0 - ratio) * 7.0)
            fade_out = min(1.0, ratio * 2.4)
            envelope = fade_in * fade_out
            envelope = envelope * envelope * (3.0 - 2.0 * envelope)
            alpha = max(0, min(255, int(255 * envelope)))
            size = max(1, int(particle.size * (0.72 + 0.28 * ratio)))
            pos = (round(particle.pos.x), round(particle.pos.y))
            if particle.shape == "rect":
                rect = pygame.Rect(0, 0, size * 2, size)
                rect.center = pos
                pygame.draw.rect(layer, (*particle.color, alpha), rect, border_radius=1)
            elif particle.shape == "slash":
                angle = math.radians(particle.rotation)
                direction = pygame.Vector2(math.cos(angle), math.sin(angle))
                half = direction * size
                start = pygame.Vector2(pos) - half
                end = pygame.Vector2(pos) + half
                pygame.draw.line(
                    layer, (*particle.color, alpha),
                    (round(start.x), round(start.y)),
                    (round(end.x), round(end.y)),
                    max(1, int(size * 0.32)),
                )
            else:
                pygame.draw.circle(layer, (*particle.color, alpha), pos, size)
        surface.blit(layer, (0, 0))
        if self.flash > 0:
            flash = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            eased_flash = self.flash * self.flash * (3.0 - 2.0 * self.flash)
            flash.fill((*self.flash_color, int(105 * eased_flash)))
            surface.blit(flash, (0, 0))
