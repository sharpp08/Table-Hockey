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
        self.motion_trail = []
        self.trail_sample_timer = 0.0
        self._overlay = None
        self._overlay_size = None
        self._glow = None
        self._glow_size = None

    def reset(self, position, radius=None):
        self.pos.update(position)
        self.previous_pos = self.pos.copy()
        self.velocity.update(0, 0)
        if radius is not None:
            self.radius = float(radius)
        self.hit_flash = 0.0
        self.motion_trail.clear()
        self.trail_sample_timer = 0.0

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

        # Keep a short history of positions for a smooth, fading anime afterimage.
        self.trail_sample_timer += max(0.0, dt)
        moving = self.velocity.length_squared() > 75.0 * 75.0
        if moving and self.trail_sample_timer >= 0.025:
            self.motion_trail.append((self.pos.copy(), 0.0))
            self.trail_sample_timer = 0.0
        elif not moving:
            self.trail_sample_timer = min(self.trail_sample_timer, 0.025)
        updated_trail = []
        for position, age in self.motion_trail:
            age += max(0.0, dt)
            if age < 0.34:
                updated_trail.append((position, age))
        self.motion_trail = updated_trail[-9:]

    def draw(self, surface, quality, game_time=0.0):
        center = (round(self.pos.x), round(self.pos.y))
        radius = max(4, round(self.radius))
        skin = get_skin(self.skin_id) if self.side < 0 and self.skin_id > 0 else None
        body = skin["color"] if skin else self.color
        accent = skin["accent"] if skin else config.COLOR_WHITE

        if quality.get("glow", False):
            glow_r = radius + max(8, radius // 2)
            glow_size = (glow_r * 2 + 2, glow_r * 2 + 2)
            if self._glow is None or self._glow_size != glow_size:
                self._glow = pygame.Surface(glow_size, pygame.SRCALPHA)
                self._glow_size = glow_size
            glow = self._glow
            glow.fill((0, 0, 0, 0))
            gc = (glow_r + 1, glow_r + 1)
            for extra, alpha in ((radius // 2, 12), (radius // 3, 22), (6, 38)):
                pygame.draw.circle(glow, (*self.color, alpha), gc, radius + extra)
            surface.blit(glow, (center[0] - gc[0], center[1] - gc[1]))

        # Reuse a single overlay for afterimages, motion cuts and hit sparks.
        size = surface.get_size()
        has_afterimages = bool(self.motion_trail)
        if has_afterimages:
            if self._overlay is None or self._overlay_size != size:
                self._overlay = pygame.Surface(size, pygame.SRCALPHA)
                self._overlay_size = size
            layer = self._overlay
            layer.fill((0, 0, 0, 0))
            for trail_pos, age in self.motion_trail:
                fade = max(0.0, 1.0 - age / 0.34)
                fade = fade * fade
                alpha = int(92 * fade)
                if alpha <= 2:
                    continue
                ghost_radius = max(3, int(radius * (0.82 + 0.12 * fade)))
                ghost_center = (round(trail_pos.x), round(trail_pos.y))
                pygame.draw.circle(layer, (*body, int(alpha * 0.30)),
                                   ghost_center, ghost_radius + 3)
                pygame.draw.circle(layer, (*accent, int(alpha * 0.72)),
                                   ghost_center, ghost_radius + 1, max(1, radius // 10))
                pygame.draw.circle(layer, (*body, alpha), ghost_center, ghost_radius)
            surface.blit(layer, (0, 0))

        # Drop shadow, metallic rim, and campaign skin materials.
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

        speed = self.velocity.length()
        motion_fade = max(0.0, min(1.0, (speed - 55.0) / 300.0))
        motion_fade = motion_fade * motion_fade * (3.0 - 2.0 * motion_fade)
        if motion_fade > 0.015 or self.hit_flash > 0:
            if self._overlay is None or self._overlay_size != size:
                self._overlay = pygame.Surface(size, pygame.SRCALPHA)
                self._overlay_size = size
            layer = self._overlay
            layer.fill((0, 0, 0, 0))

            if motion_fade > 0.015:
                direction = self.velocity.normalize()
                side_vector = pygame.Vector2(-direction.y, direction.x)
                length = min(radius * 2.2, speed * 0.018)
                for sign in (-1, 1):
                    start = pygame.Vector2(center) - direction * (radius * 0.8) + side_vector * sign * radius * 0.48
                    mid = start - direction * (length * 0.55)
                    end = start - direction * length
                    pygame.draw.line(layer, (*accent, int(145 * motion_fade)),
                                     (round(start.x), round(start.y)),
                                     (round(mid.x), round(mid.y)), max(1, radius // 9))
                    pygame.draw.line(layer, (*accent, int(55 * motion_fade)),
                                     (round(mid.x), round(mid.y)),
                                     (round(end.x), round(end.y)), max(1, radius // 12))

            if self.hit_flash > 0:
                hit = max(0.0, min(1.0, self.hit_flash))
                hit = hit * hit * (3.0 - 2.0 * hit)
                pygame.draw.circle(layer, (255, 255, 255, int(170 * hit)),
                                   center, radius + 7, 3)
                origin = (center[0], center[1])
                for angle in range(0, 360, 45):
                    a = math.radians(angle + game_time * 90.0)
                    start = (round(origin[0] + math.cos(a) * (radius + 3)),
                             round(origin[1] + math.sin(a) * (radius + 3)))
                    end = (round(origin[0] + math.cos(a) * (radius + 11)),
                           round(origin[1] + math.sin(a) * (radius + 11)))
                    pygame.draw.line(layer, (*accent, int(190 * hit)),
                                     start, end, max(1, radius // 10))
            surface.blit(layer, (0, 0))
