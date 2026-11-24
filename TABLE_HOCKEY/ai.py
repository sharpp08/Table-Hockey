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
        """Predict the puck's vertical crossing, reflecting off the top/bottom rails."""
        vx = puck.velocity.x
        if abs(vx) < 12.0:
            return self._fold_y(
                puck.pos.y + puck.velocity.y * 0.16,
                layout.inner_y + puck.radius,
                layout.inner_y + layout.inner_h - puck.radius,
            )
        travel = (target_x - puck.pos.x) / vx
        if travel <= 0.0:
            return puck.pos.y
        # Limit long-range guesses; distant predictions become unreliable after
        # several contacts with paddles or goal posts.
        travel = min(travel, 1.65)
        projected = puck.pos.y + puck.velocity.y * travel
        return self._fold_y(
            projected,
            layout.inner_y + puck.radius,
            layout.inner_y + layout.inner_h - puck.radius,
        )

    def update(self, paddle, puck, layout, dt, paddle_speed_scale=1.0):
        self.reaction_timer -= dt
        if self.reaction_timer <= 0.0:
            reaction = max(0.025, self.preset["reaction"])
            self.reaction_timer = reaction * self.rng.uniform(0.88, 1.08)

            home_x = layout.p2_goal_x - layout.inner_w * 0.135
            defend_x = layout.p2_goal_x - layout.inner_w * 0.225
            attack_x = layout.center_x + layout.inner_w * 0.075
            aggression = self.preset["aggression"]
            center_y = layout.center_y
            low_y = layout.inner_y + puck.radius
            high_y = layout.inner_y + layout.inner_h - puck.radius

            if puck.active:
                # The AI tracks the puck's likely future lane, not just its
                # current position. The target point is selected by threat level.
                toward_cpu = puck.velocity.x > 28.0 * layout.scale
                in_cpu_half = puck.pos.x > layout.center_x - layout.inner_w * 0.16
                threatening = toward_cpu and in_cpu_half

                if threatening:
                    # Intercept in front of the goal when there is time; retreat
                    # deeper when the puck is already close or moving very fast.
                    distance_to_goal = max(0.0, layout.p2_goal_x - puck.pos.x)
                    urgency = config.clamp(
                        1.0 - distance_to_goal / (layout.inner_w * 0.52), 0.0, 1.0
                    )
                    lead_time = config.lerp(0.24, 0.08, urgency)
                    intercept_x = puck.pos.x + puck.velocity.x * lead_time
                    intercept_x = config.clamp(
                        intercept_x,
                        layout.center_x + layout.inner_w * 0.025,
                        defend_x,
                    )
                    predicted_y = self._predict_y(puck, intercept_x, layout)
                    target_x = config.lerp(home_x, intercept_x, 0.78 + aggression * 0.22)
                    target_y = predicted_y
                    self.last_mode = "defend"
                elif puck.pos.x >= layout.center_x - layout.inner_w * 0.10:
                    # When the puck is moving away, close down space and prepare
                    # to challenge its next return instead of chasing its tail.
                    intercept_x = min(attack_x, max(home_x - layout.inner_w * 0.10,
                                                    puck.pos.x + paddle.radius * 0.8))
                    predicted_y = self._predict_y(puck, intercept_x, layout)
                    target_x = config.lerp(home_x, intercept_x, 0.42 + aggression * 0.42)
                    target_y = config.lerp(predicted_y, center_y, 0.08)
                    self.last_mode = "attack"
                else:
                    # Recover into a goal-side defensive position and shade
                    # toward the puck's projected lane.
                    target_x = home_x
                    predicted_y = self._predict_y(puck, home_x, layout)
                    target_y = config.lerp(center_y, predicted_y, 0.48)
                    self.last_mode = "recover"
            else:
                target_x = home_x
                target_y = config.lerp(center_y, puck.pos.y, 0.30)
                self.last_mode = "recover"

            # Better levels make more accurate reads, but retain a little
            # controlled imperfection so the CPU remains beatable.
            error = self.rng.uniform(-self.preset["aim_error"], self.preset["aim_error"])
            target_y += math.tan(math.radians(error)) * layout.inner_w * 0.055
            self.target.update(
                config.clamp(target_x, layout.p2_min_x, layout.p2_max_x),
                config.clamp(target_y, max(layout.min_y, low_y), min(layout.max_y, high_y)),
            )

        offset = self.target - paddle.pos
        dead_zone = max(1.8, paddle.radius * 0.028)
        direction = pygame.Vector2() if offset.length_squared() <= dead_zone ** 2 else offset.normalize()
        mode_factor = 0.96 if self.last_mode == "recover" else 1.0
        max_speed = self.preset["max_speed"] * layout.scale * paddle_speed_scale * mode_factor
        return direction, max_speed
