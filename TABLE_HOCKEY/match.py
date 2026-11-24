"""Match state machine: countdown, goals, pause and win conditions."""

import random

import pygame

import config
from ai import AIController
from effects import EffectsManager
from paddle import Paddle
from physics import PhysicsEngine
from puck import Puck
from settings import Layout
from player import Player, HumanController, P2_CONTROLLER


class Match:
    def __init__(self, layout, settings, audio=None, level=1, player_skin_id=0):
        self.layout = layout
        self.level = max(1, min(30, int(level)))
        self.settings = settings
        self.audio = audio
        self.rng = random.Random()
        self.mode = "single"
        self.players = [
            Player(1, "PLAYER 1", config.COLOR_P1),
            Player(2, "CPU", config.COLOR_P2),
        ]
        self.paddle_speed_scale = settings.get("paddle_speed", 1.0)
        self.puck_speed_scale = settings.get("puck_speed", 1.0)
        self.paddles = [
            Paddle(-1, layout.paddle_start(-1), layout.paddle_r, config.COLOR_P1),
            Paddle(+1, layout.paddle_start(+1), layout.paddle_r, config.COLOR_P2),
        ]
        self.paddles[0].skin_id = max(0, min(30, int(player_skin_id)))
        self.puck = Puck(layout.puck_start(1), layout.puck_r)
        self.physics = PhysicsEngine(layout, self.puck_speed_scale)
        self.ai = AIController(self._level_ai_preset(settings.ai_preset), random.Random())
        self.effects = EffectsManager(settings.quality, random.Random())

        self.state = "COUNTDOWN"
        self.countdown = config.COUNTDOWN_SECONDS
        self.countdown_audio = 3
        self.goal_timer = 0.0
        self.last_goal = 0
        self.match_time = 0.0
        self.pause_return_state = "PLAYING"
        self.winner = 0
        self.celebration_color = config.COLOR_GOLD
        self.events = []
        self.goal_pos = pygame.Vector2(layout.center_x, layout.center_y)

        self.reset_for_serve(1)
        self.effects.clear()

    # ------------------------------------------------------------------ #
    def _level_ai_preset(self, base_preset=None):
        """Scale an already aggressive CPU into an elite opponent over 30 levels."""
        progress = (self.level - 1) / 29.0
        curve = progress ** 0.88
        base = dict(base_preset or config.AI_BASE_PRESET)
        return {
            "max_speed": base["max_speed"] + 500.0 * curve,
            "reaction": max(0.025, base["reaction"] - 0.015 * curve),
            "aim_error": max(0.35, base["aim_error"] - 1.65 * curve),
            "aggression": min(0.99, base["aggression"] + 0.17 * curve),
            "tracking": 14.0 + 19.0 * curve,
        }

    def configure_settings(self, settings):
        self.settings = settings
        self.paddle_speed_scale = settings.get("paddle_speed", 1.0)
        self.puck_speed_scale = settings.get("puck_speed", 1.0)
        self.physics.configure(layout=None, speed_scale=self.puck_speed_scale)
        self.ai.configure(self._level_ai_preset(settings.ai_preset))
        self.effects.configure(settings.quality)
        self.effects.bounds = (self.layout.w, self.layout.h)

    def configure_layout(self, layout):
        self.layout = layout
        self.physics.configure(layout=layout, speed_scale=self.puck_speed_scale)
        self.puck.reset(layout.puck_start(1), layout.puck_r)
        self.paddles[0].reset(layout.paddle_start(-1), layout.paddle_r)
        self.paddles[1].reset(layout.paddle_start(+1), layout.paddle_r)
        self.effects.configure(self.settings.quality, bounds=(layout.w, layout.h))

    def reset_for_serve(self, serve_to):
        self.puck.reset(self.layout.puck_start(serve_to), self.layout.puck_r)
        self.paddles[0].reset(self.layout.paddle_start(-1), self.layout.paddle_r)
        self.paddles[1].reset(self.layout.paddle_start(+1), self.layout.paddle_r)
        self.ai.reset(self.paddles[1].pos)
        self.effects.clear()
        self.state = "COUNTDOWN"
        self.countdown = config.COUNTDOWN_SECONDS
        self.countdown_audio = 3
        self.goal_timer = 0.0

    def reset_match(self, serve_to=1):
        self.players[0].score = 0
        self.players[1].score = 0
        self.match_time = 0.0
        self.winner = 0
        self.last_goal = 0
        self.effects.clear()
        self.effects.stop_celebration()
        self.reset_for_serve(serve_to)
    # ------------------------------------------------------------------ #
    def update(self, dt, keys=None):
        """Advance the match. Returns a list of UI/audio event names."""
        dt = min(max(dt, 0.0), 0.05)
        keys = keys or pygame.key.get_pressed()
        out = []

        if self.state == "PAUSED":
            return out

        if self.state == "GAMEOVER":
            self.effects.update(dt)
            self.effects.start_celebration(self.celebration_color)
            return out

        if self.state == "COUNTDOWN":
            self.countdown -= dt
            whole = config.COUNTDOWN_SECONDS - self.countdown
            audio_count = int(whole)
            if audio_count < self.countdown_audio and audio_count >= 1:
                self.countdown_audio = audio_count
                out.append("count")
                self._play("count")
            if self.countdown <= 0:
                self.state = "PLAYING"
                self._serve()
                out.append("serve")
            return out

        if self.state == "GOAL":
            self.goal_timer -= dt
            self.effects.update(dt)
            if self.goal_timer <= 0:
                self.reset_for_serve(-self.last_goal)
                out.append("resume")
            return out

        # PLAYING
        self.match_time += dt

        binds = self.settings.get("keybindings", {"up": "w", "left": "a", "down": "s", "right": "d"})
        try:
            p1_controller = HumanController(
                pygame.key.key_code(binds.get("up", "w")),
                pygame.key.key_code(binds.get("down", "s")),
                pygame.key.key_code(binds.get("left", "a")),
                pygame.key.key_code(binds.get("right", "d")),
            )
        except (ValueError, TypeError):
            p1_controller = HumanController(pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d)
        p1_dir = p1_controller.direction(keys)
        self.paddles[0].update(p1_dir, dt, self.layout, self.paddle_speed_scale)

        if self.mode == "single":
            direction, max_speed = self.ai.update(
                self.paddles[1], self.puck, self.layout, dt, self.paddle_speed_scale
            )
            self.paddles[1].update(direction, dt, self.layout,
                                   self.paddle_speed_scale, max_speed=max_speed)
        else:
            p2_dir = P2_CONTROLLER.direction(keys)
            self.paddles[1].update(p2_dir, dt, self.layout, self.paddle_speed_scale)

        events = self.physics.update(self.puck, self.paddles, dt)
        for event in events:
            self.events.append(event)
            if event["type"] == "wall":
                out.append("wall")
                self._play("wall")
                self.effects.impact(
                    event["pos"], event["normal"], config.COLOR_WHITE,
                    strength=min(1.4, event["speed"] / 700.0),
                )
            elif event["type"] == "paddle":
                out.append("hit")
                self._play("hit")
                color = config.COLOR_P1 if event["paddle"] == 0 else config.COLOR_P2
                self.effects.impact(
                    event["pos"], event["normal"], color,
                    strength=min(1.4, event["speed"] / 650.0),
                )
            elif event["type"] == "goal":
                self._on_goal(event["scorer"])
                break

        self.effects.update(dt)
        self.events = [e for e in self.events if e["type"] != "goal"]
        return out

    def _serve(self):
        target = -self.last_goal if self.last_goal else 1
        speed = config.PUCK_MAX_SPEED * 0.50 * self.layout.scale * self.puck_speed_scale
        speed = min(config.PUCK_MAX_SPEED, max(config.PUCK_MIN_SPEED, speed)) * self.layout.scale
        self.puck.launch(target, speed, self.rng)

    def _on_goal(self, scorer):
        scorer = int(scorer)
        self.players[scorer - 1].score += 1
        self.last_goal = scorer
        self.goal_pos = self.layout.goal_scored(-scorer + 2)
        self.state = "GOAL"
        self.goal_timer = config.GOAL_CELEBRATION
        color = self.players[scorer - 1].color
        self.effects.goal(self.goal_pos, color)
        self._play("goal")
        self.events.append({"type": "goal", "scorer": scorer, "pos": pygame.Vector2(self.goal_pos)})
        if self.players[scorer - 1].score >= self.settings.win_score:
            self.winner = scorer
            self.state = "GAMEOVER"
            self.celebration_color = color
            self.effects.clear()
            self.effects.start_celebration(color)
            self._play("win" if scorer == 1 else "lose")
            return

    def pause(self, resume_state=None):
        if self.state in ("PLAYING", "COUNTDOWN", "GOAL"):
            self.pause_return_state = resume_state or self.state
            self.state = "PAUSED"

    def resume(self):
        if self.state == "PAUSED":
            self.state = self.pause_return_state

    def toggle_pause(self, resume_state=None):
        if self.state == "PAUSED":
            self.resume()
        else:
            self.pause(resume_state)

    def drain_events(self):
        out, self.events = self.events, []
        return out

    @property
    def is_active(self):
        return self.state in ("PLAYING", "COUNTDOWN", "GOAL")

    def _play(self, name):
        if self.audio is not None:
            self.audio.play(name)
