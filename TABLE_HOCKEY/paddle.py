"""Circular hockey paddle entity with smooth, frame-rate independent motion."""

import math

import pygame

import config
from skins import get_skin


class Paddle:
    def __init__(self, side, position, radius, color):
        self.side = -1 if side < 0 else 1
        self.pos = pygame.Vector2(position)
        self.previous_pos = self.pos.copy()
        self.velocity = pygame.Vector2()
        self.radius = float(radius)
        self.color = color
        self.hit_flash = 0.0
        self.skin_id = 0

    def reset(self, position, radius=None):
        self.pos.update(position)
        self.previous_pos = self.pos.copy()
        self.velocity.update(0, 0)
        if radius is not None:
            self.radius = float(radius)
        self.hit_flash = 0.0

    def update(self, direction, dt, layout, speed_scale=1.0, max_speed=None):
        """Accelerate toward input and constrain the paddle to its own half."""
        self.previous_pos = self.pos.copy()
        direction = pygame.Vector2(direction)
        if direction.length_squared() > 1.0:
            direction.normalize_ip()

        base_speed = config.PADDLE_SPEED * layout.scale * speed_scale
        speed = base_speed if max_speed is None else max_speed
        target_velocity = direction * speed
        # Exponential response feels smooth while remaining independent of FPS.
        response = 1.0 - math.exp(-30.0 * max(0.0, dt))
        self.velocity += (target_velocity - self.velocity) * response
        if direction.length_squared() == 0 and self.velocity.length_squared() < 4.0:
            self.velocity.update(0, 0)

        self.pos += self.velocity * dt
        min_x = layout.p1_min_x if self.side < 0 else layout.p2_min_x
        max_x = layout.p1_max_x if self.side < 0 else layout.p2_max_x
        old_x, old_y = self.pos.x, self.pos.y
        self.pos.x = config.clamp(self.pos.x, min_x, max_x)
        self.pos.y = config.clamp(self.pos.y, layout.min_y, layout.max_y)
        if self.pos.x != old_x:
            self.velocity.x = 0.0
        if self.pos.y != old_y:
            self.velocity.y = 0.0
        self.hit_flash = max(0.0, self.hit_flash - dt * 4.5)

    def draw(self, surface, quality, game_time=0.0):
        center = (round(self.pos.x), round(self.pos.y))
        radius = max(4, round(self.radius))
        if quality.get("glow", False):
            glow_r = radius + max(8, radius // 2)
            glow = pygame.Surface((glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA)
            gc = (glow_r + 1, glow_r + 1)
            for extra, alpha in ((radius // 2, 12), (radius // 3, 22), (6, 38)):
                pygame.draw.circle(glow, (*self.color, alpha), gc, radius + extra)
            surface.blit(glow, (center[0] - gc[0], center[1] - gc[1]))

        # Drop shadow, metallic rim, and campaign skin materials.
        skin = get_skin(self.skin_id) if self.side < 0 and self.skin_id > 0 else None
        body = skin["color"] if skin else self.color
        accent = skin["accent"] if skin else config.COLOR_WHITE
        pygame.draw.circle(surface, (5, 7, 12), (center[0] + 4, center[1] + 6), radius + 3)
        pygame.draw.circle(surface, accent, center, radius + 3)
        pygame.draw.circle(surface, body, center, radius)
        inner = tuple(max(0, int(c * 0.62)) for c in body)
        pygame.draw.circle(surface, inner, center, max(4, int(radius * 0.58)))
        pygame.draw.circle(surface, body, center, max(3, int(radius * 0.46)))
        if skin:
            pattern = skin["pattern"]
            if pattern in ("orbit", "legend"):
                pygame.draw.circle(surface, accent, center, max(4, int(radius * .76)), max(2, radius // 12))
                pygame.draw.circle(surface, accent, (center[0], center[1] - radius // 2), max(2, radius // 9))
            elif pattern == "flare":
                pygame.draw.line(surface, accent, (center[0] - radius // 2, center[1] + radius // 2),
                                 (center[0] + radius // 2, center[1] - radius // 2), max(2, radius // 8))
            elif pattern == "core":
                pygame.draw.circle(surface, accent, center, max(3, int(radius * .22)))
        shine = tuple(min(255, int(c * 1.45)) for c in body)
        pygame.draw.circle(
            surface, shine,
            (center[0] - int(radius * 0.22), center[1] - int(radius * 0.25)),
            max(2, int(radius * 0.13)),
        )
        if self.hit_flash > 0:
            pygame.draw.circle(surface, config.COLOR_WHITE, center, radius + 7, 3)
