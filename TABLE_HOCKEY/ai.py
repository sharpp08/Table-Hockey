"""Adaptive anime-rival CPU with fluid movement and competitive decisions."""
import math
import random

import pygame

import config


class AIController:
    """An aggressive opponent that constantly pressures and attacks."""

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
            # Stay forward and ready to launch the next attack; never retreat
            # to a passive goal-side home position.
            self.last_mode = "attack"
            return pygame.Vector2(
                layout.p2_min_x + w * 0.035,
                config.lerp(cy, puck.pos.y, 0.35),
            )

        in_cpu_half = puck.pos.x > cx

        if in_cpu_half:
            # Intercept the puck's future position instead of chasing its
            # current coordinates. Estimate how long the paddle needs to reach
            # the strike zone, then account for puck motion and rail bounces.
            max_ai_speed = max(1.0, self.preset["max_speed"] * layout.scale)
            approach_distance = paddle.pos.distance_to(puck.pos)
            intercept_time = config.clamp(
                approach_distance / max_ai_speed * 0.72,
                0.035,
                0.34,
            )
            future_x = puck.pos.x + puck.velocity.x * intercept_time
            future_y = puck.pos.y + puck.velocity.y * intercept_time
            right_limit = layout.inner_x + layout.inner_w - puck.radius
            if future_x > right_limit:
                future_x = right_limit - (future_x - right_limit)
            future_x = config.clamp(future_x, cx + puck.radius, right_limit)
            low_rail = layout.inner_y + puck.radius
            high_rail = layout.inner_y + layout.inner_h - puck.radius
            predicted_puck = pygame.Vector2(
                future_x,
                self._fold(future_y, low_rail, high_rail),
            )

            # Aim toward the part of the opponent goal least aligned with puck motion.
            goal_low = cy - h * 0.17
            goal_high = cy + h * 0.17
            if abs(puck.velocity.y) > 75.0:
                desired_goal_y = goal_low if puck.velocity.y > 0 else goal_high
            else:
                desired_goal_y = goal_low if puck.pos.y > cy else goal_high
            desired_goal_y += math.sin(self.clock * 1.7 + self.strafe_phase) * h * 0.025
            desired_goal_y = config.clamp(desired_goal_y, goal_low, goal_high)

            # Build the strike from the puck's predicted contact position.
            # The target must overlap the puck's collision radius slightly;
            # stopping outside that radius makes the CPU look like it is only following.
            shot = pygame.Vector2(layout.p1_goal_x - predicted_puck.x,
                                  desired_goal_y - predicted_puck.y)
            if shot.length_squared() > 1.0:
                shot.normalize_ip()
            else:
                shot.update(-1.0, 0.0)

            contact_gap = max(
                1.0,
                paddle.radius + puck.radius - max(4.0, 0.20 * layout.scale),
            )
            contact = predicted_puck - shot * contact_gap
            # Keep the approach line stable so the CPU drives through the puck
            # instead of orbiting beside it.
            contact.x = config.clamp(contact.x,
                                     layout.p2_min_x, layout.p2_max_x)
            contact.y = config.clamp(contact.y, max(layout.min_y, low),
                                      min(layout.max_y, high))
            distance_to_contact = paddle.pos.distance_to(contact)
            urgency = config.clamp(distance_to_contact / max(1.0, w * 0.22), 0.0, 1.0)
            # Do not blend back toward the home/guard position here:
            # that blend is what caused the CPU to stop beside the puck.
            # Commit to the contact coordinate and drive through the strike.
            target = pygame.Vector2(contact.x, contact.y)
            self.last_mode = "attack"

        else:
            # Puck is on the player's half: stay at the forward edge of the
            # CPU's legal zone and pressure the return lane. The paddle cannot
            # cross the center line, so it prepares to attack immediately.
            press_x = min(layout.p2_max_x, layout.p2_min_x + w * 0.035)
            predicted_y, travel = self._predict(puck, press_x, layout)
            y_offset = math.sin(self.clock * 1.35 + self.strafe_phase) * h * 0.012
            target = pygame.Vector2(
                press_x,
                config.clamp(predicted_y + y_offset, low, high),
            )
            self.last_mode = "attack"

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
            3.0 if attacking else (1.65 if threat else 1.0)
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
            0.92 if self.last_mode == "recover"
            else (1.12 if self.last_mode == "attack" else 1.18)
        )
        base_speed = self.preset["max_speed"] * layout.scale * paddle_speed_scale
        desired_speed = base_speed * mode_factor
        braking_distance = max(
            paddle.radius * (0.10 if attacking else 0.8),
            desired_speed * desired_speed / (3400.0 if attacking else 1900.0),
        )
        if distance < braking_distance:
            desired_speed *= max(0.72 if attacking else 0.22, distance / braking_distance)
        return direction, desired_speed
