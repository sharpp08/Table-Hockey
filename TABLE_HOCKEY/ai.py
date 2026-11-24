"""Anime-rival campaign CPU with predictive reads and deliberate reactions."""
import math
import random
import pygame
import config


class AIController:
    """Reads puck lanes, chooses attack/guard plans, and moves without twitching."""

    def __init__(self, preset, rng=None):
        self.rng = rng or random.Random()
        self.configure(preset)
        self.target = pygame.Vector2()
        self.planned_target = pygame.Vector2()
        self.replan_timer = 0.0
        self.last_mode = "recover"
        self.last_puck_velocity = pygame.Vector2()

    def configure(self, preset):
        self.preset = dict(preset)
        self.preset.setdefault("reaction", 0.12)
        self.preset.setdefault("tracking", 12.0)
        self.preset.setdefault("aim_error", 5.0)
        self.preset.setdefault("aggression", 0.4)

    def reset(self, position):
        self.target.update(position)
        self.planned_target.update(position)
        self.replan_timer = 0.0
        self.last_mode = "recover"
        self.last_puck_velocity.update(0, 0)

    @staticmethod
    def _fold_y(y, low, high):
        span = high - low
        if span <= 0:
            return low
        value = (y - low) % (span * 2.0)
        return low + (value if value <= span else span * 2.0 - value)

    def _predict(self, puck, target_x, layout):
        """Predict a rail-bounced intercept; damp long reads when collisions are uncertain."""
        vx = puck.velocity.x
        low = layout.inner_y + puck.radius
        high = layout.inner_y + layout.inner_h - puck.radius
        if abs(vx) < 24.0:
            t = min(0.22, abs(target_x - puck.pos.x) / max(120.0, puck.velocity.length()))
        else:
            t = (target_x - puck.pos.x) / vx
            if t <= 0:
                t = min(0.18, abs(target_x - puck.pos.x) / max(120.0, puck.velocity.length()))
        t = min(1.05, max(0.0, t))
        # A small velocity damping makes the read robust after paddle/post contacts.
        return self._fold_y(puck.pos.y + puck.velocity.y * t * 0.94, low, high), t

    def _choose_plan(self, paddle, puck, layout):
        cx, cy = layout.center_x, layout.center_y
        home_x = layout.p2_goal_x - layout.inner_w * 0.135
        guard_x = layout.p2_goal_x - layout.inner_w * 0.205
        low = layout.inner_y + puck.radius
        high = layout.inner_y + layout.inner_h - puck.radius
        aggression = self.preset["aggression"]

        if not puck.active:
            self.last_mode = "recover"
            return pygame.Vector2(home_x, config.lerp(cy, puck.pos.y, 0.12))

        toward_cpu = puck.velocity.x > 20.0 * layout.scale
        in_cpu_half = puck.pos.x > cx - layout.inner_w * 0.10
        danger = toward_cpu and in_cpu_half

        if danger:
            # Move to a reachable point between the puck and the CPU goal.
            urgency = config.clamp(
                1.0 - max(0.0, layout.p2_goal_x - puck.pos.x) / (layout.inner_w * 0.62),
                0.0, 1.0,
            )
            lead = config.lerp(0.30, 0.065, urgency)
            intercept_x = config.clamp(
                puck.pos.x + puck.velocity.x * lead,
                cx + layout.inner_w * 0.015, guard_x,
            )
            predicted_y, travel_time = self._predict(puck, intercept_x, layout)
            # If the predicted point is too far away to reach, defend the goal lane instead.
            reach = self.preset["max_speed"] * layout.scale * max(0.12, travel_time)
            vertical_error = abs(predicted_y - paddle.pos.y)
            if vertical_error > reach * 1.25:
                predicted_y = config.lerp(paddle.pos.y, predicted_y, 0.62)
            forward = config.lerp(0.58, 0.86, aggression) * (1.0 - urgency * 0.18)
            target = pygame.Vector2(config.lerp(home_x, intercept_x, forward), predicted_y)
            self.last_mode = "intercept"
        elif puck.pos.x > cx - layout.inner_w * 0.10:
            # Attack from behind the puck and bias contact toward an open shooting lane.
            read_x = puck.pos.x + (1.0 if puck.velocity.x >= 0 else -1.0) * paddle.radius * 2.0
            predicted_y, _ = self._predict(puck, read_x, layout)
            goal_y = cy + config.clamp((cy - predicted_y) * 0.22,
                                       -layout.inner_h * 0.18, layout.inner_h * 0.18)
            shot = pygame.Vector2(layout.p1_goal_x - puck.pos.x, goal_y - predicted_y)
            if shot.length_squared() > 1.0:
                shot.normalize_ip()
            contact_gap = paddle.radius + puck.radius + 3.0 * layout.scale
            attack = pygame.Vector2(puck.pos.x, predicted_y) - shot * contact_gap
            attack.x = config.clamp(
                max(attack.x, puck.pos.x + paddle.radius * 0.55),
                cx + paddle.radius * 0.65, layout.p2_max_x,
            )
            attack.y = config.lerp(predicted_y, goal_y, 0.22)
            self.last_mode = "attack"
            target = attack
        else:
            # Stay goal-side, but shade toward the puck's predicted return lane.
            predicted_y, _ = self._predict(puck, home_x, layout)
            shade = config.lerp(0.26, 0.54, aggression)
            target = pygame.Vector2(home_x, config.lerp(cy, predicted_y, shade))
            self.last_mode = "recover"

        # Apply a single small uncertainty per decision, not fresh random jitter each frame.
        error = self.rng.uniform(-self.preset["aim_error"], self.preset["aim_error"])
        target.y += math.tan(math.radians(error)) * layout.inner_w * 0.035
        target.x = config.clamp(target.x, layout.p2_min_x, layout.p2_max_x)
        target.y = config.clamp(target.y, max(layout.min_y, low), min(layout.max_y, high))
        return target

    def update(self, paddle, puck, layout, dt, paddle_speed_scale=1.0):
        dt = max(0.0, dt)
        self.replan_timer -= dt
        if self.replan_timer <= 0.0:
            self.planned_target = self._choose_plan(paddle, puck, layout)
            # Reaction time is a real planning cadence; elite levels reassess more often.
            reaction = max(0.025, float(self.preset["reaction"]))
            self.replan_timer = reaction * self.rng.uniform(0.82, 1.18)

        response = 1.0 - math.exp(-self.preset["tracking"] * dt)
        self.target += (self.planned_target - self.target) * response
        offset = self.target - paddle.pos
        dead_zone = max(1.2, paddle.radius * 0.012)
        direction = pygame.Vector2() if offset.length_squared() <= dead_zone * dead_zone else offset.normalize()
        mode_factor = 0.90 if self.last_mode == "recover" else 1.0
        max_speed = self.preset["max_speed"] * layout.scale * paddle_speed_scale * mode_factor
        return direction, max_speed
