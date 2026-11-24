"""Predictive, difficulty-scaled arcade opponent controller."""
import math
import random
import pygame
import config


class AIController:
    """Reads puck velocity, predicts rail rebounds and chooses attack/defense lanes."""

    def __init__(self, preset, rng=None):
        self.rng = rng or random.Random()
        self.configure(preset)
        self.target = pygame.Vector2()
        self.reaction_timer = 0.0
        self.last_mode = "recover"

    def configure(self, preset):
        self.preset = dict(preset)
        self.reaction_timer = 0.0

    def reset(self, position):
        self.target.update(position)
        self.reaction_timer = 0.0
        self.last_mode = "recover"

    @staticmethod
    def _fold_y(y, low, high):
        span = high - low
        if span <= 0:
            return low
        value = (y - low) % (span * 2.0)
        return low + (value if value <= span else span * 2.0 - value)

    def _predict_y(self, puck, target_x, layout):
        vx = puck.velocity.x
        if abs(vx) < 20.0:
            return puck.pos.y
        travel = (target_x - puck.pos.x) / vx
        if travel <= 0.0 or travel > 2.5:
            return puck.pos.y
        projected = puck.pos.y + puck.velocity.y * travel
        return self._fold_y(projected,
            layout.inner_y + puck.radius,
            layout.inner_y + layout.inner_h - puck.radius)

    def update(self, paddle, puck, layout, dt, paddle_speed_scale=1.0):
        self.reaction_timer -= dt
        if self.reaction_timer <= 0.0:
            reaction = max(0.035, self.preset["reaction"])
            self.reaction_timer = reaction * self.rng.uniform(0.82, 1.18)
            home_x = layout.p2_goal_x - layout.inner_w * 0.13
            defend_x = layout.p2_goal_x - layout.inner_w * 0.205
            attack_x = layout.center_x + layout.inner_w * 0.075
            aggression = self.preset["aggression"]

            if puck.active and puck.pos.x >= layout.center_x - layout.inner_w * 0.10:
                approaching = puck.velocity.x > 45.0 * layout.scale
                # Intercept nearer the goal when a shot is coming quickly.
                intercept_x = defend_x if approaching else min(attack_x, puck.pos.x + paddle.radius * 0.7)
                predicted_y = self._predict_y(puck, intercept_x, layout)
                # Aim slightly behind the puck so contact drives it left.
                target_x = config.lerp(home_x, intercept_x, 0.48 + aggression * 0.55)
                target_y = predicted_y
                if not approaching:
                    target_y = config.lerp(target_y, layout.center_y, 0.10)
                self.last_mode = "defend" if approaching else "attack"
            else:
                # Hold a compact defensive line and shade toward the puck.
                target_x = home_x
                target_y = config.lerp(layout.center_y, puck.pos.y, 0.34)
                self.last_mode = "recover"

            # Difficulty controls both reaction noise and prediction precision.
            error = self.rng.uniform(-self.preset["aim_error"], self.preset["aim_error"])
            target_y += math.tan(math.radians(error)) * layout.inner_w * 0.075
            self.target.update(
                config.clamp(target_x, layout.p2_min_x, layout.p2_max_x),
                config.clamp(target_y, layout.min_y, layout.max_y),
            )

        offset = self.target - paddle.pos
        dead_zone = max(2.5, paddle.radius * 0.045)
        direction = pygame.Vector2() if offset.length_squared() <= dead_zone ** 2 else offset.normalize()
        # A small speed penalty while recovering makes lower difficulties feel less robotic.
        mode_factor = 0.92 if self.last_mode == "recover" else 1.0
        max_speed = self.preset["max_speed"] * layout.scale * paddle_speed_scale * mode_factor
        return direction, max_speed
