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

        # Rotating anime-tech glyphs around each paddle; drawn as a small alpha layer.
        ring_r = radius + max(5, radius // 3)
        ring_size = ring_r * 2 + 4
        ring_layer = pygame.Surface((ring_size, ring_size), pygame.SRCALPHA)
        ring_rect = pygame.Rect(2, 2, ring_size - 4, ring_size - 4)
        rotation = game_time * (2.2 if self.side < 0 else -1.8)
        pulse = 0.5 + 0.5 * math.sin(game_time * 3.1 + self.side * 0.7)
        ring_alpha = int(58 + 102 * pulse)
        ring_width = max(1, int(radius / 10 * (0.82 + pulse * 0.28)))
        for segment in range(3):
            start = rotation + segment * math.tau / 3.0
            pygame.draw.arc(ring_layer, (*accent, ring_alpha),
                            ring_rect, start, start + 0.62 + pulse * 0.16, ring_width)
        surface.blit(ring_layer, (center[0] - ring_size // 2, center[1] - ring_size // 2))

        # Movement cuts ease in with speed and taper toward their trailing ends.
        speed = self.velocity.length()
        motion_fade = max(0.0, min(1.0, (speed - 55.0) / 300.0))
        motion_fade = motion_fade * motion_fade * (3.0 - 2.0 * motion_fade)
        if motion_fade > 0.015:
            direction = self.velocity.normalize()
            side_vector = pygame.Vector2(-direction.y, direction.x)
            length = min(radius * 2.2, speed * 0.018)
            cuts = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            for sign in (-1, 1):
                start = pygame.Vector2(center) - direction * (radius * 0.8) + side_vector * sign * radius * 0.48
                mid = start - direction * (length * 0.55)
                end = start - direction * length
                pygame.draw.line(cuts, (*accent, int(145 * motion_fade)),
                                 (round(start.x), round(start.y)),
                                 (round(mid.x), round(mid.y)), max(1, radius // 9))
                pygame.draw.line(cuts, (*accent, int(55 * motion_fade)),
                                 (round(mid.x), round(mid.y)),
                                 (round(end.x), round(end.y)), max(1, radius // 12))
            surface.blit(cuts, (0, 0))

        # Hit sparks bloom quickly and then dissolve with the hit envelope.
        if self.hit_flash > 0:
            hit = max(0.0, min(1.0, self.hit_flash))
            hit = hit * hit * (3.0 - 2.0 * hit)
            hit_layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(hit_layer, (255, 255, 255, int(170 * hit)),
                               center, radius + 7, 3)
            burst = pygame.Surface((radius * 5, radius * 5), pygame.SRCALPHA)
            origin = (radius * 2 + radius // 2, radius * 2 + radius // 2)
            for angle in range(0, 360, 45):
                a = math.radians(angle + game_time * 90.0)
                start = (origin[0] + math.cos(a) * (radius + 3),
                         origin[1] + math.sin(a) * (radius + 3))
                end = (origin[0] + math.cos(a) * (radius + 11),
                       origin[1] + math.sin(a) * (radius + 11))
                pygame.draw.line(burst, (*accent, int(190 * hit)),
                                 start, end, max(1, radius // 10))
            hit_layer.blit(burst, (center[0] - origin[0], center[1] - origin[1]))
            surface.blit(hit_layer, (0, 0))
