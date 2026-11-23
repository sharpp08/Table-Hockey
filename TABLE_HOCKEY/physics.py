"""Sub-stepped air-hockey physics and collision resolution."""

import math

import pygame

import config


class PhysicsEngine:
    def __init__(self, layout, speed_scale=1.0):
        self.layout = layout
        self.speed_scale = speed_scale

    def configure(self, layout=None, speed_scale=None):
        if layout is not None:
            self.layout = layout
        if speed_scale is not None:
            self.speed_scale = speed_scale

    def _speed_limits(self):
        s = self.layout.scale * self.speed_scale
        return config.PUCK_MIN_SPEED * s, config.PUCK_MAX_SPEED * s

    def _limit_speed(self, puck):
        speed = puck.velocity.length()
        mn, mx = self._speed_limits()
        if speed > mx:
            puck.velocity.scale_to_length(mx)
        elif 0.001 < speed < mn and puck.active:
            puck.velocity.scale_to_length(mn)

    def update(self, puck, paddles, dt):
        events = []
        if not puck.active or dt <= 0:
            return events
        dt = min(dt, 0.05)
        travel = puck.velocity.length() * dt
        steps = max(1, min(16, int(math.ceil(travel / max(4.0, puck.radius * 0.42)))))
        step_dt = dt / steps

        for _ in range(steps):
            puck.pos += puck.velocity * step_dt
            goal = self._collide_walls(puck, events)
            if goal:
                puck.active = False
                events.append({"type": "goal", "scorer": goal, "pos": puck.pos.copy()})
                break
            self._collide_posts(puck, events)
            for i, paddle in enumerate(paddles):
                self._collide_paddle(puck, paddle, i, events)
            puck.velocity *= math.exp(-config.PUCK_FRICTION * step_dt)
            self._limit_speed(puck)

        puck.record_trail()
        return events

    def _wall_event(self, events, puck, normal):
        events.append({
            "type": "wall", "pos": puck.pos.copy(),
            "normal": pygame.Vector2(normal), "speed": puck.velocity.length(),
        })

    def _collide_walls(self, puck, events):
        l = self.layout
        top = l.inner_y + puck.radius
        bottom = l.inner_y + l.inner_h - puck.radius
        if puck.pos.y < top:
            puck.pos.y = top
            if puck.velocity.y < 0:
                puck.velocity.y = -puck.velocity.y * 0.97
                self._wall_event(events, puck, (0, 1))
        elif puck.pos.y > bottom:
            puck.pos.y = bottom
            if puck.velocity.y > 0:
                puck.velocity.y = -puck.velocity.y * 0.97
                self._wall_event(events, puck, (0, -1))

        lane_t = l.goal_top + puck.radius * 0.28
        lane_b = l.goal_bottom - puck.radius * 0.28
        in_lane = lane_t <= puck.pos.y <= lane_b
        left, right = l.inner_x, l.inner_x + l.inner_w

        if puck.pos.x - puck.radius < left:
            if in_lane and puck.pos.x <= left - puck.radius * 0.18:
                return 2
            if not in_lane:
                puck.pos.x = left + puck.radius
                if puck.velocity.x < 0:
                    puck.velocity.x = -puck.velocity.x * 0.97
                    self._wall_event(events, puck, (1, 0))
        elif puck.pos.x + puck.radius > right:
            if in_lane and puck.pos.x >= right + puck.radius * 0.18:
                return 1
            if not in_lane:
                puck.pos.x = right - puck.radius
                if puck.velocity.x > 0:
                    puck.velocity.x = -puck.velocity.x * 0.97
                    self._wall_event(events, puck, (-1, 0))
        return 0

    def _collide_posts(self, puck, events):
        l = self.layout
        pr = max(3.0, l.border * 0.46)
        posts = [(l.inner_x, l.goal_top), (l.inner_x, l.goal_bottom),
                 (l.inner_x + l.inner_w, l.goal_top),
                 (l.inner_x + l.inner_w, l.goal_bottom)]
        for x, y in posts:
            key = f"post_{x},{y}"
            delta = puck.pos - pygame.Vector2(x, y)
            min_d = puck.radius + pr
            dist_sq = delta.length_squared()
            if dist_sq >= min_d * min_d:
                puck.contacts.discard(key)
                continue
            dist = math.sqrt(dist_sq) if dist_sq > 1e-9 else 0.0
            normal = delta / dist if dist else pygame.Vector2(0, -1)
            puck.pos = pygame.Vector2(x, y) + normal * (min_d + 0.35)
            closing = puck.velocity.dot(normal)
            if closing < 0 and key not in puck.contacts:
                puck.velocity -= normal * closing * 1.96
                self._wall_event(events, puck, normal)
            puck.contacts.add(key)

    def _collide_paddle(self, puck, paddle, index, events):
        key = f"paddle_{index}"
        delta = puck.pos - paddle.pos
        min_d = puck.radius + paddle.radius
        dist_sq = delta.length_squared()
        if dist_sq >= min_d * min_d:
            puck.contacts.discard(key)
            return
        dist = math.sqrt(dist_sq) if dist_sq > 1e-9 else 0.0
        normal = delta / dist if dist else pygame.Vector2(-paddle.side, 0)
        puck.pos = paddle.pos + normal * (min_d + 0.35)

        if key not in puck.contacts:
            relative = puck.velocity - paddle.velocity
            closing = relative.dot(normal)
            tangent = puck.velocity - normal * puck.velocity.dot(normal)
            mn, _ = self._speed_limits()
            reflected = max(abs(closing) * 1.04, mn * 0.70)
            drive = max(0.0, paddle.velocity.dot(normal)) * config.PADDLE_ACCEL_FACTOR
            kick = config.PADDLE_KICK * self.layout.scale * self.speed_scale * 0.18
            puck.velocity = tangent * 0.96 + normal * (reflected + drive + kick)
            puck.velocity += paddle.velocity * 0.16
            self._limit_speed(puck)
            paddle.hit_flash = 1.0
            events.append({
                "type": "paddle", "paddle": index, "pos": puck.pos.copy(),
                "normal": normal.copy(), "speed": puck.velocity.length(),
            })
        puck.contacts.add(key)
