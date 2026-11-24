"""
Table Hockey - Shared configuration, constants, colors and layout metrics.

Everything that describes the table geometry, the color palette and the
global tuning numbers lives here so the rest of the codebase can rely on
a single source of truth.
"""

import math

# --------------------------------------------------------------------------- #
# Window / display
# --------------------------------------------------------------------------- #
BASE_RESOLUTION = (1280, 720)          # internal logical resolution
RESOLUTIONS = [
    (960, 540),
    (1280, 720),
    (1600, 900),
]
CAPTION = "TABLE HOCKEY"

# --------------------------------------------------------------------------- #
# Colors (r, g, b)
# --------------------------------------------------------------------------- #
COLOR_BLACK        = (8, 10, 16)
COLOR_BG           = (13, 16, 24)
COLOR_BG_LIGHT     = (26, 31, 45)
COLOR_TABLE        = (20, 27, 44)
COLOR_TABLE_EDGE   = (60, 72, 100)
COLOR_TABLE_BORDER = (18, 22, 34)
COLOR_LINE         = (90, 110, 150)
COLOR_LINE_FAINT   = (50, 60, 85)
COLOR_WHITE        = (235, 240, 250)
COLOR_TEXT         = (225, 230, 240)
COLOR_TEXT_DIM     = (135, 145, 165)

COLOR_P1           = (56, 140, 255)    # blue
COLOR_P1_LIGHT     = (150, 200, 255)
COLOR_P1_DARK      = (30, 80, 170)
COLOR_P2           = (255, 80, 80)     # red
COLOR_P2_LIGHT     = (255, 160, 160)
COLOR_P2_DARK      = (170, 40, 40)
COLOR_PUCK         = (240, 245, 255)
COLOR_GOLD         = (255, 200, 90)
COLOR_GOAL_FLASH   = (255, 255, 255)

# --------------------------------------------------------------------------- #
# Table layout (fractions of the base 1280x720 resolution).
# The game scales these by width/height at runtime so it works at any
# resolution / fullscreen.
# --------------------------------------------------------------------------- #
TABLE_W = 0.90
TABLE_H = 0.84
BORDER = 0.012          # wall thickness
RADIUS = 0.055         # corner rounding
GOAL_W = 0.36          # goal opening height
GOAL_DEPTH = 0.045     # how far the goal mouth sits into the table

PADDLE_R = 0.046       # paddle radius
PUCK_R   = 0.022       # puck radius

# Physics tuning (per-second values)
PUCK_ACCEL   = 2700.0  # extra velocity applied on a paddle hit (px/s at base)
PUCK_FRICTION = 0.66   # exponential friction factor per second
PUCK_MIN_SPEED = 180.0 # px/s at base resolution
PUCK_MAX_SPEED = 1680.0
PADDLE_SPEED   = 650.0 # px/s at base resolution
PADDLE_ACCEL_FACTOR = 1.68  # how much paddle velocity boosts the puck
PADDLE_KICK      = 720.0   # base kick on a paddle hit (px/s at base)

GOAL_CELEBRATION = 1.35    # seconds of the goal animation
COUNTDOWN_SECONDS = 2     # pre-serve countdown
MATCH_TIMER = False       # show an elapsed timer in the HUD

# Campaign-driven CPU baseline. Level 1 should already feel alert and capable;
# the campaign curve still adds speed, reaction time and precision through level 30.
AI_BASE_PRESET = {
    # Level 1 remains aggressive, but gives new players time to react.
    "reaction": 0.11,
    "max_speed": 560.0,
    "aim_error": 8.0,
    "aggression": 0.58,
}

# Default settings (used when no config file exists yet)
DEFAULT_SETTINGS = {
    "master_volume": 0.8,
    "sfx_volume": 0.8,
    "music_volume": 0.35,
    "music_enabled": True,
    "puck_speed": 1.0,        # 0.5 .. 1.5
    "paddle_speed": 1.0,      # 0.5 .. 1.5
    "win_score": 5,           # 3 .. 10
    "fullscreen": False,
    "show_fps": True,
    "screen_shake": True,
    "fps_cap": 60,
    "keybindings": {"up": "w", "left": "a", "down": "s", "right": "d"},
    "resolution": BASE_RESOLUTION,
    "graphics_quality": "HIGH",  # LOW, MEDIUM, HIGH
    "table_theme": "NEON",
    "show_match_timer": MATCH_TIMER,
}

# Graphics quality flags
QUALITY_FLAGS = {
    "LOW":    {"trails": False, "glow": False, "particles": 0,  "blur": False},
    "MEDIUM": {"trails": True,  "glow": False, "particles": 24, "blur": False},
    "HIGH":   {"trails": True,  "glow": True,  "particles": 60, "blur": True},
}


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def lerp(a, b, t):
    return a + (b - a) * t


def scale_color(c, f):
    """Return color c multiplied by brightness factor f, clamped 0..255."""
    return (clamp(int(c[0] * f), 0, 255),
            clamp(int(c[1] * f), 0, 255),
            clamp(int(c[2] * f), 0, 255))
