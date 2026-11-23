"""
Table Hockey - settings persistence and runtime layout.

Two concerns live here:

1.  SettingsStore : load/save a JSON config file with sane defaults.
2.  Layout        : converts the fractional table metrics in config.py into
                    pixel coordinates for the current resolution, so every
                    screen (menu, HUD, physics) can share one geometry.
"""

import json
import os
import copy

import config
from config import clamp, DEFAULT_SETTINGS, QUALITY_FLAGS

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save", "settings.json")


class SettingsStore:
    """Holds the user configuration and persists it to disk as JSON."""

    def __init__(self):
        self.data = copy.deepcopy(DEFAULT_SETTINGS)
        self.load()

    # -- persistence -------------------------------------------------------- #
    def load(self):
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for key, value in raw.items():
                    if key in self.data:
                        self.data[key] = value
            # validate
            self._validate()
        except (json.JSONDecodeError, OSError) as exc:
            # Corrupt or unreadable file - fall back to defaults.
            print("[settings] could not load config, using defaults:", exc)
            self.data = copy.deepcopy(DEFAULT_SETTINGS)

    def save(self):
        self._validate()
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        try:
            serialisable = copy.deepcopy(self.data)
            serialisable["resolution"] = list(self.data["resolution"])
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(serialisable, f, indent=2)
            return True
        except OSError as exc:
            print("[settings] could not save config:", exc)
            return False

    def _validate(self):
        d = self.data
        d["master_volume"] = clamp(float(d.get("master_volume", 0.8)), 0.0, 1.0)
        d["sfx_volume"]    = clamp(float(d.get("sfx_volume", 0.8)), 0.0, 1.0)
        d["music_volume"]  = clamp(float(d.get("music_volume", 0.35)), 0.0, 1.0)
        d["music_enabled"] = bool(d.get("music_enabled", True))
        d["puck_speed"]    = clamp(float(d.get("puck_speed", 1.0)), 0.5, 1.5)
        d["paddle_speed"]  = clamp(float(d.get("paddle_speed", 1.0)), 0.5, 1.5)
        d["win_score"]     = int(clamp(int(d.get("win_score", 5)), 3, 10))
        d["ai_difficulty"] = d.get("ai_difficulty", "NORMAL").upper()
        if d["ai_difficulty"] not in config.AI_PRESETS:
            d["ai_difficulty"] = "NORMAL"
        d["fullscreen"]    = bool(d.get("fullscreen", False))
        res = tuple(d.get("resolution", config.BASE_RESOLUTION))
        d["resolution"]    = res if res in config.RESOLUTIONS else config.BASE_RESOLUTION
        d["graphics_quality"] = str(d.get("graphics_quality", "HIGH")).upper()
        if d["graphics_quality"] not in QUALITY_FLAGS:
            d["graphics_quality"] = "HIGH"
        d["show_match_timer"] = bool(d.get("show_match_timer", False))
        d["show_fps"] = bool(d.get("show_fps", True))
        d["screen_shake"] = bool(d.get("screen_shake", True))
        try:
            d["fps_cap"] = int(d.get("fps_cap", 60))
        except (TypeError, ValueError):
            d["fps_cap"] = 60
        if d["fps_cap"] not in (0, 30, 60, 120):
            d["fps_cap"] = 60
        defaults = {"up": "w", "left": "a", "down": "s", "right": "d"}
        bindings = d.get("keybindings", {})
        if not isinstance(bindings, dict):
            bindings = {}
        clean = {}
        for action, default_key in defaults.items():
            key = str(bindings.get(action, default_key)).lower()
            clean[action] = key if key and len(key) <= 16 else default_key
        if len(set(clean.values())) != len(clean):
            clean = defaults
        d["keybindings"] = clean

    # -- accessors ---------------------------------------------------------- #
    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        if key in self.data:
            self.data[key] = value
            self._validate()

    @property
    def quality(self):
        return QUALITY_FLAGS[self.data["graphics_quality"]]

    @property
    def resolution(self):
        return tuple(self.data["resolution"])

    @property
    def fullscreen(self):
        return bool(self.data["fullscreen"])

    @property
    def win_score(self):
        return int(self.data["win_score"])

    @property
    def ai_preset(self):
        return config.DIFFICULTY[self.data["ai_difficulty"]]

    @property
    def sfx_volume(self):
        return self.data["sfx_volume"] * self.data["master_volume"]

    @property
    def music_volume(self):
        return self.data["music_volume"] * self.data["master_volume"]

class Layout:
    """Pixel-space geometry for a given window size (w, h)."""

    def __init__(self, w, h):
        self.w, self.h = int(w), int(h)
        s = self.w / config.BASE_RESOLUTION[0]   # uniform scale factor
        self.scale = s

        t = config.TABLE_W * self.w
        th = config.TABLE_H * self.h
        self.table_x = (self.w - t) / 2.0
        self.table_y = (self.h - th) / 2.0
        self.table_w = t
        self.table_h = th

        b = max(2, int(config.BORDER * self.w))
        self.border = b
        # inner playing field (inside the walls)
        self.inner_x = self.table_x + b
        self.inner_y = self.table_y + b
        self.inner_w = t - 2 * b
        self.inner_h = th - 2 * b

        self.goal_w = config.GOAL_W * th
        self.goal_depth = config.GOAL_DEPTH * self.w
        self.goal_top = self.inner_y + (self.inner_h - self.goal_w) / 2.0
        self.goal_bottom = self.goal_top + self.goal_w

        self.paddle_r = config.PADDLE_R * self.w
        self.puck_r = config.PUCK_R * self.w

        self.center_x = self.inner_x + self.inner_w / 2.0
        self.center_y = self.inner_y + self.inner_h / 2.0

        # Paddle safe zones (each stays in its own half, inside the walls)
        self.p1_min_x = self.inner_x + self.paddle_r
        self.p1_max_x = self.center_x - self.paddle_r
        self.p2_min_x = self.center_x + self.paddle_r
        self.p2_max_x = self.inner_x + self.inner_w - self.paddle_r
        self.min_y = self.inner_y + self.paddle_r
        self.max_y = self.inner_y + self.inner_h - self.paddle_r

    # convenience ---------------------------------------------------------- #
    def puck_start(self, serve_to):
        """Starting puck position; serve_to is -1 (toward P1 half) or +1."""
        return (self.center_x + serve_to * self.inner_w * 0.02, self.center_y)

    def paddle_start(self, side):
        """side: -1 for player 1, +1 for player 2."""
        x = self.center_x + side * self.inner_w * 0.28
        return (x, self.center_y)

    def goal_scored(self, side):
        """side -1 => right goal (P2's) was hit; +1 => left goal (P1's)."""
        x = self.p2_goal_x if side == -1 else self.p1_goal_x
        return (x, self.center_y)

    @property
    def p1_goal_x(self):
        return self.inner_x

    @property
    def p2_goal_x(self):
        return self.inner_x + self.inner_w

