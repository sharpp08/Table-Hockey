"""Air-hockey puck entity and its procedural arcade rendering."""

from collections import deque
import math
import random

import pygame

import config


class Puck:
    def __init__(self, position, radius):
        self.pos = pygame.Vector2(position)
        self.velocity = pygame.Vector2()
        self.radius = float(radius)
        self.active = False
        self.trail = deque(maxlen=22)
        self.contacts = set()
        self.spin = 0.0

    def reset(self, position, radius=None):
        self.pos.update(position)
        self.velocity.update(0, 0)
        if radius is not None:
            self.radius = float(radius)
        self.active = False
        self.trail.clear()
        self.contacts.clear()
        self.spin = 0.0

    def launch(self, direction, speed, rng=None):
        """Serve generally toward direction (-1 left, +1 right)."""
        rng = rng or random
        angle = math.radians(rng.uniform(-24.0, 24.0))
        self.velocity.update(math.cos(angle) * direction, math.sin(angle))
        self.velocity.scale_to_length(speed)
        self.active = True

    def record_trail(self):
        if not self.trail or self.pos.distance_squared_to(self.trail[-1]) > 9.0:
            self.trail.append(self.pos.copy())

    def draw(self, surface, quality, game_time=0.0):
        center = (round(self.pos.x), round(self.pos.y))
        radius = max(3, round(self.radius))

        if quality.get("trails", False) and len(self.trail) > 1:
            points = list(self.trail)
            layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            for index, point in enumerate(points[:-1]):
                strength = (index + 1) / len(points)
                # Smooth tail taper: older trail points dissolve instead of ending abruptly.
                strength = strength * strength * (3.0 - 2.0 * strength)
                rr = max(2, int(radius * strength * 0.72))
                tint = (95, 205, 255) if index % 2 else (185, 135, 255)
                pygame.draw.circle(
                    layer, (*tint, int(92 * strength)),
                    (round(point.x), round(point.y)), rr,
                )
            surface.blit(layer, (0, 0))

        # Anime-style motion cuts fade in with speed and dissolve toward their tails.
        speed = self.velocity.length()
        fade = max(0.0, min(1.0, (speed - 120.0) / 430.0))
        fade = fade * fade * (3.0 - 2.0 * fade)
        if fade > 0.015:
            direction = self.velocity.normalize()
            side = pygame.Vector2(-direction.y, direction.x)
            intensity = min(1.0, speed / 1050.0)
            length = radius * (2.5 + 8.0 * intensity)
            streak_layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            for index, spread in enumerate((-0.52, 0.0, 0.52)):
                offset = side * (spread * radius * 1.65)
                start = pygame.Vector2(center) - direction * (radius * 0.8) + offset
                for segment in range(5):
                    t0 = segment / 5.0
                    t1 = (segment + 1) / 5.0
                    a = 1.0 - t0
                    a = a * a * fade
                    p0 = start - direction * (length * t0)
                    p1 = start - direction * (length * t1)
                    color = (105, 220, 255) if index != 1 else (245, 225, 255)
                    alpha = int((45 + 145 * intensity) * a * (1.0 if index == 1 else 0.72))
                    pygame.draw.line(streak_layer, (*color, alpha),
                                     (round(p0.x), round(p0.y)),
                                     (round(p1.x), round(p1.y)),
                                     max(1, int(radius * (0.18 if index else 0.28))))
            surface.blit(streak_layer, (0, 0))

        if quality.get("glow", False):
            glow_r = radius * 3
            glow = pygame.Surface((glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA)
            gc = (glow_r + 1, glow_r + 1)
            for rr, alpha in ((radius * 3, 10), (radius * 2, 22), (radius + 6, 45)):
                pygame.draw.circle(glow, (*config.COLOR_PUCK, alpha), gc, rr)
            surface.blit(glow, (center[0] - gc[0], center[1] - gc[1]))

        pygame.draw.circle(surface, (3, 5, 10), (center[0] + 3, center[1] + 4), radius + 2)
        pygame.draw.circle(surface, (155, 170, 195), center, radius + 2)
        pygame.draw.circle(surface, config.COLOR_PUCK, center, radius)
        pygame.draw.circle(surface, (205, 215, 235), center, max(2, int(radius * 0.55)))
        pygame.draw.circle(
            surface, config.COLOR_WHITE,
            (center[0] - radius // 4, center[1] - radius // 4),
            max(2, radius // 5),
        )
