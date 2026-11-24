"""Adaptive campaign CPU with predictive interceptions and smooth movement."""
import math
import random
import pygame
import config


class AIController:
    """Predicts rail rebounds, protects its goal, and attacks from behind the puck."""

    def __init__(self, preset, rng=None):
        self.rng = rng or random.Random()
        self.configure(preset)
        self.target = pygame.Vector2()
        self.last_mode = "recover"

    def configure(self, preset):
        self.preset = dict(preset)

    def reset(self, position):
        self.target.update(position)
        self.last_mode = "recover"

    @staticmethod
    def _fold_y(y, low, high):
        span = high - low
        if span <= 0:
            return low
        value = (y - low) % (span * 2.0)
        return low + (value if value <= span else span * 2.0 - value)

    def _predict_y(self, puck, target_x, layout):
        """Estimate vertical puck position at a future x, including rail bounces."""
        vx = puck.velocity.x
        low = layout.inner_y + puck.radius
        high = layout.inner_y + layout.inner_h - puck.radius
        if abs(vx) < 18.0:
            return self._fold_y(puck.pos.y + puck.velocity.y * 0.12, low, high)
        travel = (target_x - puck.pos.x) / vx
        if travel <= 0:
            return self._fold_y(puck.pos.y, low, high)
        # Long predictions are damped because future paddle/post contacts are unknown.
        travel = min(travel, 1.25)
        return self._fold_y(puck.pos.y + puck.velocity.y * travel, low, high)

    def _desired_target(self, paddle, puck, layout):
        center_x, center_y = layout.center_x, layout.center_y
        home_x = layout.p2_goal_x - layout.inner_w * 0.13
        guard_x = layout.p2_goal_x - layout.inner_w * 0.22
        low_y = layout.inner_y + puck.radius
        high_y = layout.inner_y + layout.inner_h - puck.radius
        aggression = self.preset["aggression"]

        if not puck.active:
            self.last_mode = "recover"
            return pygame.Vector2(home_x, config.lerp(center_y, puck.pos.y, 0.18))

        toward_cpu = puck.velocity.x > 24.0 * layout.scale
        in_cpu_half = puck.pos.x > center_x - layout.inner_w * 0.12
        danger = toward_cpu and in_cpu_half

        if danger:
            # Choose a reachable interception point in front of the goal.
            goal_distance = max(0.0, layout.p2_goal_x - puck.pos.x)
            urgency = config.clamp(1.0 - goal_distance / (layout.inner_w * 0.58), 0.0, 1.0)
            lead = config.lerp(0.25, 0.075, urgency)
            intercept_x = config.clamp(
                puck.pos.x + puck.velocity.x * lead,
                center_x + layout.inner_w * 0.025,
                guard_x,
            )
            predicted_y = self._predict_y(puck, intercept_x, layout)
            # At high levels the CPU steps farther forward, but falls back when danger is immediate.
            forward = config.lerp(0.62, 0.88, aggression) * (1.0 - urgency * 0.20)
            target = pygame.Vector2(config.lerp(home_x, intercept_x, forward), predicted_y)
            self.last_mode = "intercept"
        elif puck.pos.x > center_x - layout.inner_w * 0.08:
            # Approach from the right side so a contact drives the puck toward the player's goal.
            approach_x = config.clamp(
                puck.pos.x + paddle.radius * config.lerp(1.65, 1.18, aggression),
                center_x + paddle.radius,
                layout.p2_max_x,
            )
            predicted_y = self._predict_y(puck, approach_x, layout)
            # Aim slightly away from the center line to create varied attacks.
            lane = config.lerp(center_y, predicted_y, 0.72)
            target = pygame.Vector2(approach_x, lane)
            self.last_mode = "attack"
        else:
            # Hold a compact defensive shape near the center until the puck returns.
            predicted_y = self._predict_y(puck, home_x, layout)
            shade = config.lerp(0.32, 0.62, aggression)
            target = pygame.Vector2(home_x, config.lerp(center_y, predicted_y, shade))
            self.last_mode = "recover"

        # Small controlled uncertainty prevents perfect robotic saves.
        error = self.rng.uniform(-self.preset["aim_error"], self.preset["aim_error"])
        target.y += math.tan(math.radians(error)) * layout.inner_w * 0.045
        target.x = config.clamp(target.x, layout.p2_min_x, layout.p2_max_x)
        target.y = config.clamp(target.y, max(layout.min_y, low_y), min(layout.max_y, high_y))
        return target

    def update(self, paddle, puck, layout, dt, paddle_speed_scale=1.0):
        desired = self._desired_target(paddle, puck, layout)
        # Re-plan continuously, but blend target changes to avoid twitchy CPU movement.
        response = 1.0 - math.exp(-self.preset["tracking"] * max(0.0, dt))
        self.target += (desired - self.target) * response

        offset = self.target - paddle.pos
        dead_zone = max(1.5, paddle.radius * 0.018)
        if offset.length_squared() <= dead_zone * dead_zone:
            direction = pygame.Vector2()
        else:
            direction = offset.normalize()

        mode_factor = 0.94 if self.last_mode == "recover" else 1.0
        max_speed = self.preset["max_speed"] * layout.scale * paddle_speed_scale * mode_factor
        return direction, max_speed
