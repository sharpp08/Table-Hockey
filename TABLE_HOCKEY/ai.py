"""Imperfect, difficulty-scaled opponent controller."""

import math
import random

import pygame

import config


class AIController:
    """Choose delayed targets rather than tracking the puck perfectly."""

    def __init__(self, preset, rng=None):
        self.rng = rng or random.Random()
        self.configure(preset)
        self.target = pygame.Vector2()
        self.reaction_timer = 0.0

    def configure(self, preset):
        self.preset = dict(preset)
        self.reaction_timer = 0.0

    def reset(self, position):
        self.target.update(position)
        self.reaction_timer = 0.0

    @staticmethod
    def _fold_y(y, low, high):
        """Reflect a projected Y position between the horizontal rails."""
        span = high - low
        if span <= 0:
            return low
        n = (y - low) % (span * 2.0)
        return low + (n if n <= span else span * 2.0 - n)

    def _predict_y(self, puck, target_x, layout):
        if abs(puck.velocity.x) < 15.0:
            return puck.pos.y
        travel = (target_x - puck.pos.x) / puck.velocity.x
        if travel <= 0 or travel > 2.2:
            return puck.pos.y
        projected = puck.pos.y + puck.velocity.y * travel
        return self._fold_y(
            projected,
            layout.inner_y + puck.radius,
            layout.inner_y + layout.inner_h - puck.radius,
        )

    def update(self, paddle, puck, layout, dt, paddle_speed_scale=1.0):
        """Return (direction, max_speed) for the right-hand paddle."""
        self.reaction_timer -= dt
        if self.reaction_timer <= 0.0:
            reaction = self.preset["reaction"]
            self.reaction_timer = reaction * self.rng.uniform(0.82, 1.18)
            home_x = layout.p2_goal_x - layout.inner_w * 0.13
            defend_x = layout.p2_goal_x - layout.inner_w * 0.20
            error_angle = math.radians(
                self.rng.uniform(-self.preset["aim_error"], self.preset["aim_error"])
            )
            error_y = math.tan(error_angle) * layout.inner_w * 0.13

            if puck.active and puck.pos.x >= layout.center_x - layout.inner_w * 0.04:
                # Move behind the puck to strike it toward the left goal. When a
                # fast shot approaches, favor an intercept line near our goal.
                approaching = puck.velocity.x > 80.0 * layout.scale
                target_x = defend_x if approaching else puck.pos.x + paddle.radius * 0.72
                predicted_y = self._predict_y(puck, target_x, layout)
                aggression = self.preset["aggression"]
                target_x = config.lerp(home_x, target_x, 0.55 + aggression)
                self.target.update(target_x, predicted_y + error_y)
            else:
                # Recover to goal, but continue loosely following the puck.
                follow = config.lerp(layout.center_y, puck.pos.y, 0.42)
                self.target.update(home_x, follow + error_y * 0.45)

            self.target.x = config.clamp(self.target.x, layout.p2_min_x, layout.p2_max_x)
            self.target.y = config.clamp(self.target.y, layout.min_y, layout.max_y)

        offset = self.target - paddle.pos
        dead_zone = max(3.0, paddle.radius * 0.06)
        if offset.length_squared() <= dead_zone * dead_zone:
            direction = pygame.Vector2()
        else:
            direction = offset.normalize()
        max_speed = self.preset["max_speed"] * layout.scale * paddle_speed_scale
        return direction, max_speed
