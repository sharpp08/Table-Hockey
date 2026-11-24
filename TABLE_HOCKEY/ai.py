"""Adaptive anime-rival CPU with fluid movement and competitive decisions."""
import math
import random

import pygame

import config


class AIController:
    """A reactive opponent that patrols, intercepts, pressures and attacks dynamically."""

    def __init__(self, preset, rng=None):
        self.rng = rng or random.Random()
        self.configure(preset)
        self.target = pygame.Vector2()
        self.planned_target = pygame.Vector2()
        self.replan_timer = 0.0
        self.last_mode = "recover"
        self.last_puck_velocity = pygame.Vector2()
        self.clock = 0.0
        self.strafe_phase = self.rng.uniform(0.0, math.tau)
        self.commitment = 0.0

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
        self.commitment = 0.0

    @staticmethod
    def _fold(value, low, high):
        span = high - low
        if span <= 0:
            return low
        offset = (value - low) % (2.0 * span)
        return low + (offset if offset <= span else 2.0 * span - offset)

    def _predict(self, puck, target_x, layout):
        """Estimate where the puck reaches a vertical lane, including rail bounces."""
        vx = puck.velocity.x
        speed = max(150.0, puck.velocity.length())
        if abs(vx) < 30.0:
            travel = min(0.48, abs(target_x - puck.pos.x) / speed)
        else:
            travel = (target_x - puck.pos.x) / vx
            if travel < 0.0:
                travel = min(0.30, abs(target_x - puck.pos.x) / speed)
        travel = config.clamp(travel, 0.0, 0.92)
        low = layout.inner_y + puck.radius
        high = layout.inner_y + layout.inner_h - puck.radius
        # Blend a short and long read: distant predictions are less trustworthy.
        raw_y = puck.pos.y + puck.velocity.y * travel
        predicted = self._fold(raw_y, low, high)
        confidence = 1.0 - 0.38 * min(1.0, travel / 0.92)
        predicted = config.lerp(puck.pos.y, predicted, confidence)
        return predicted, travel

    def _choose_plan(self, paddle, puck, layout):
        cx, cy = layout.center_x, layout.center_y
        w, h = layout.inner_w, layout.inner_h
        home_x = layout.p2_goal_x - w * 0.13
        guard_x = layout.p2_goal_x - w * 0.205
        low = layout.inner_y + puck.radius
        high = layout.inner_y + layout.inner_h - puck.radius
        aggression = self.preset["aggression"]
        speed = max(1.0, puck.velocity.length())

        if not puck.active:
            self.last_mode = "recover"
            return pygame.Vector2(home_x, config.lerp(cy, puck.pos.y, 0.10))

        toward_cpu = puck.velocity.x > 18.0 * layout.scale
        in_cpu_half = puck.pos.x > cx
        danger = toward_cpu and puck.pos.x > cx - w * 0.16

        if danger:
            # Read the lane in front of the goal, not just the puck's current position.
            urgency = config.clamp(
                1.0 - (layout.p2_goal_x - puck.pos.x) / (w * 0.68), 0.0, 1.0
            )
            intercept_x = config.lerp(guard_x, home_x - w * 0.025, urgency)
            predicted_y, travel = self._predict(puck, intercept_x, layout)
            reachable = self.preset["max_speed"] * layout.scale * max(0.10, travel)
            if abs(predicted_y - paddle.pos.y) > reachable:
                predicted_y = config.lerp(paddle.pos.y, predicted_y, 0.48)
            # Move forward only when the paddle can plausibly reach the lane.
            forward = config.lerp(0.24, 0.76, urgency) * (0.55 + aggression * 0.45)
            target = pygame.Vector2(
                config.lerp(home_x, intercept_x, forward), predicted_y
            )
            self.last_mode = "intercept"

        elif in_cpu_half:
            # Approach from behind the puck and choose a changing shot lane.
            approach = config.clamp((puck.pos.x - cx) / (w * 0.48), 0.0, 1.0)
            lead_x = config.lerp(puck.pos.x + paddle.radius * 1.7,
                                 puck.pos.x + paddle.radius * 0.85, aggression)
            read_x = config.clamp(lead_x, cx + puck.radius, layout.p2_max_x)
            predicted_y, travel = self._predict(puck, read_x, layout)

            # Aim toward the part of the opponent goal least aligned with puck motion.
            goal_low = cy - h * 0.17
            goal_high = cy + h * 0.17
            if abs(puck.velocity.y) > 75.0:
                desired_goal_y = goal_low if puck.velocity.y > 0 else goal_high
            else:
                desired_goal_y = goal_low if puck.pos.y > cy else goal_high
            desired_goal_y += math.sin(self.clock * 1.7 + self.strafe_phase) * h * 0.025
            desired_goal_y = config.clamp(desired_goal_y, goal_low, goal_high)

            shot = pygame.Vector2(layout.p1_goal_x - puck.pos.x,
                                  desired_goal_y - predicted_y)
            if shot.length_squared() > 1.0:
                shot.normalize_ip()
            else:
                shot.update(-1.0, 0.0)

            contact_gap = paddle.radius + puck.radius + 4.0 * layout.scale
            contact = pygame.Vector2(puck.pos.x, predicted_y) - shot * contact_gap
            # Don't rush straight at the puck: take a moving angle around it.
            orbit = math.sin(self.clock * 1.25 + self.strafe_phase) * paddle.radius * 0.30
            contact.y += orbit * (0.35 + aggression)
            contact.x = config.clamp(contact.x,
                                     cx + paddle.radius * 0.55, layout.p2_max_x)
            contact.y = config.clamp(contact.y, max(layout.min_y, low),
                                      min(layout.max_y, high))
            # On slow pucks, close distance; on fast pucks, lead the future contact.
            # Commit to the strike instead of merely shadowing the puck.
            # Move decisively to the contact point, then let paddle momentum drive
            # the puck toward the selected goal lane.
            distance_to_contact = paddle.pos.distance_to(contact)
            urgency = config.clamp(distance_to_contact / max(1.0, w * 0.22), 0.0, 1.0)
            commit = 0.88 + 0.10 * urgency
            target = pygame.Vector2(
                config.lerp(home_x, contact.x, commit),
                config.lerp(paddle.pos.y, contact.y, 0.92),
            )
            self.last_mode = "attack"

        else:
            # The CPU doesn't camp on one x coordinate: it shades forward and
            # follows the puck's projected return lane with a gentle lateral sweep.
            predicted_y, travel = self._predict(puck, home_x, layout)
            depth = config.clamp((cx - puck.pos.x) / (w * 0.55), 0.0, 1.0)
            forward_pressure = config.lerp(0.0, w * 0.075, aggression) * (1.0 - depth)
            x_sweep = math.sin(self.clock * 0.82 + self.strafe_phase) * w * 0.018
            shade = config.lerp(0.30, 0.62, aggression)
            y_sweep = math.sin(self.clock * 1.08 + self.strafe_phase) * h * 0.018
            target = pygame.Vector2(
                home_x - forward_pressure + x_sweep,
                config.lerp(cy, predicted_y, shade) + y_sweep,
            )
            self.last_mode = "recover"

        # A little uncertainty per decision keeps the CPU human-like, not random.
        error = self.rng.uniform(-self.preset["aim_error"], self.preset["aim_error"])
        target.y += math.tan(math.radians(error)) * w * 0.022
        target.x = config.clamp(target.x, layout.p2_min_x, layout.p2_max_x)
        target.y = config.clamp(target.y, max(layout.min_y, low),
                                min(layout.max_y, high))
        return target

    def update(self, paddle, puck, layout, dt, paddle_speed_scale=1.0):
        dt = max(0.0, dt)
        self.clock += dt
        self.replan_timer -= dt

        if self.replan_timer <= 0.0:
            self.planned_target = self._choose_plan(paddle, puck, layout)
            # Reaction cadence varies slightly so decisions don't look scripted.
            reaction = max(0.035, float(self.preset["reaction"]))
            self.replan_timer = reaction * self.rng.uniform(0.78, 1.24)

        # Smooth target pursuit, with stronger response when the puck threatens goal.
        threat = self.last_mode == "intercept"
        attacking = self.last_mode == "attack"
        tracking = self.preset["tracking"] * (
            1.42 if attacking else (1.30 if threat else 1.0)
        )
        response = 1.0 - math.exp(-tracking * dt)
        self.target += (self.planned_target - self.target) * response

        offset = self.target - paddle.pos
        distance = offset.length()
        dead_zone = max(0.8, paddle.radius * 0.006)
        if distance <= dead_zone:
            direction = pygame.Vector2()
        else:
            direction = offset / distance

        # Ease speed with distance to target; avoid constant full-speed sliding.
        mode_factor = (
            0.88 if self.last_mode == "recover"
            else (1.16 if self.last_mode == "attack" else 1.08)
        )
        base_speed = self.preset["max_speed"] * layout.scale * paddle_speed_scale
        desired_speed = base_speed * mode_factor
        braking_distance = max(paddle.radius * 0.8, desired_speed * desired_speed / 1900.0)
        if distance < braking_distance:
            desired_speed *= max(0.22, distance / braking_distance)
        return direction, desired_speed
