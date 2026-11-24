"""Reusable arcade-style UI widgets and table renderer for Table Hockey."""

import math

import pygame

import config


class UI:
    """Shared font helpers, panel and rounded-rect helpers."""

    @staticmethod
    def font(size, bold=False):
        # Default pygame font scales cleanly and avoids external font assets.
        return pygame.font.Font(None, max(12, int(size)), bold)

    @staticmethod
    def rounded_panel(surface, rect, color, alpha, radius=18, border=None):
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*color, alpha), (0, 0, rect.w, rect.h),
                         border_radius=radius)
        if border:
            pygame.draw.rect(panel, (*border[0], border[1], border[2], 255),
                             (0, 0, rect.w - 1, rect.h - 1), 2, border_radius=radius)
        surface.blit(panel, rect)

    @staticmethod
    def text_width(font, text):
        return font.size(text)[0]


class AnimatedButton:
    def __init__(self, rect, label, color=config.COLOR_P1, size=42, bold=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.font = UI.font(size, bold)
        self.hover_progress = 0.0
        self.click_progress = 0.0
        self.disabled = False

    def update(self, dt, mouse, focus=False):
        inside = self.rect.collidepoint(mouse) or focus
        target = 1.0 if inside and not self.disabled else 0.0
        self.hover_progress += (target - self.hover_progress) * min(1.0, dt * 14.0)
        self.click_progress = max(0.0, self.click_progress - dt * 5.0)

    def draw(self, surface, offset=(0, 0)):
        r = self.rect.move(offset)
        scale = 1.0 + self.click_progress * 0.05
        center = (r.centerx, r.centery)
        rect = pygame.Rect(0, 0, int(r.w * scale), int(r.h * scale))
        rect.center = center
        progress = self.hover_progress
        base = tuple(max(0, int(c * (1.15 + 0.25 * progress))) for c in config.COLOR_BG_LIGHT)
        UI.rounded_panel(surface, rect, base, 235, radius=12,
                         border=self.color if progress > 0.35 else edge_color)
        text = self.font.render(self.label, True, config.COLOR_TEXT)
        text_bg = pygame.Surface((text.get_width() + 10, text.get_height()), pygame.SRCALPHA)
        text_bg.blit(text, (5, 0))
        surface.blit(text_bg, text_bg.get_rect(center=center))
        # Subtle highlight sweep on hover
        if progress > 0.1:
            glow = config.scale_color(self.color, 1.1 + progress * 0.5)
            sweep = pygame.Surface((rect.w, 3), pygame.SRCALPHA)
            sweep.fill((*glow, int(180 * progress)))
            surface.blit(sweep, (rect.left, rect.top + 3))

    def handle_click(self, pos, focus=False):
        if self.disabled:
            return False
        if self.rect.collidepoint(pos) or focus:
            self.click_progress = 1.0
            return True
        return False



class TableRenderer:
    """Draws the complete air-hockey table once into a cached surface."""

    def __init__(self, layout, quality, theme="NEON"):
        self.layout = layout
        self.quality = quality
        self.theme = str(theme).upper()
        palettes = {
            "NEON": ((13, 16, 24), (20, 27, 44), (60, 72, 100), (90, 110, 150), (50, 60, 85), (18, 22, 34)),
            "CYBER": ((8, 13, 23), (14, 27, 45), (45, 105, 145), (75, 165, 210), (35, 82, 120), (12, 28, 48)),
            "SUNSET": ((20, 12, 25), (38, 20, 32), (130, 60, 80), (210, 110, 130), (100, 55, 75), (45, 20, 35)),
        }
        self.palette = palettes.get(self.theme, palettes["NEON"])
        self.surface = None
        self._build()

    def _build(self):
        l = self.layout
        w, h = l.w, l.h
        self.surface = pygame.Surface((w, h))
        bg_color, table_color, edge_color, line_color, faint_color, border_color = self.palette
        self.surface.fill(bg_color)

        # Background gradient for depth
        for i in range(24):
            y = int(i / 24 * h)
            shade = 0.65 + 0.35 * math.sin(i / 24 * math.pi)
            color = config.scale_color(bg_color, 0.7 + 0.35 * shade)
            pygame.draw.line(self.surface, color, (0, y), (w, y))

        # Table base (rounded)
        rect = pygame.Rect(int(l.table_x), int(l.table_y), int(l.table_w), int(l.table_h))
        radius = int(config.RADIUS * l.w)
        pygame.draw.rect(self.surface, (10, 13, 22), rect.inflate(28, 28), border_radius=radius + 14)
        pygame.draw.rect(self.surface, config.COLOR_TABLE_EDGE, rect.inflate(20, 20), border_radius=radius + 10)
        pygame.draw.rect(self.surface, table_color, rect, border_radius=radius)

        # Subtle inner vignette
        inner = pygame.Rect(int(l.inner_x), int(l.inner_y), int(l.inner_w), int(l.inner_h))
        vignette = pygame.Surface(inner.size, pygame.SRCALPHA)
        for i in range(14):
            m = 4 + i * 3
            a = max(0, 30 - i * 2)
            pygame.draw.rect(vignette, (0, 0, 0, a), (m, m, inner.w - m * 2, inner.h - m * 2), 1, border_radius=6)
        self.surface.blit(vignette, inner.topleft)

        # Center line + circle
        cx = int(l.center_x)
        pygame.draw.line(self.surface, line_color, (cx, l.inner_y), (cx, l.inner_y + l.inner_h), 3)
        ccr = int(l.inner_h * 0.16)
        pygame.draw.circle(self.surface, config.COLOR_LINE, (cx, int(l.center_y)), ccr, 3)
        pygame.draw.circle(self.surface, faint_color, (cx, int(l.center_y)), max(2, ccr // 4), 4)

        # Goal creases (face-off arcs toward each goal)
        for side in (-1, 1):
            gx = int(l.center_x + side * l.inner_w * 0.32)
            color = config.COLOR_P1 if side < 0 else config.COLOR_P2
            pygame.draw.circle(self.surface, config.scale_color(color, 0.6),
                               (gx, int(l.center_y)), int(l.inner_h * 0.20), 2)
            pygame.draw.circle(self.surface, config.scale_color(color, 0.45),
                               (gx, int(l.center_y)), int(l.inner_h * 0.10), 2)

        # Goal mouths (dark recessed slots)
        gd = int(l.goal_depth)
        top, bottom = int(l.goal_top), int(l.goal_bottom)
        for x, color in ((l.inner_x, config.COLOR_P1), (l.inner_x + l.inner_w, config.COLOR_P2)):
            side = -1 if x < l.center_x else 1
            if side < 0:
                rect = pygame.Rect(int(x) - gd, top, gd, bottom - top)
            else:
                rect = pygame.Rect(int(x), top, gd, bottom - top)
            pygame.draw.rect(self.surface, (8, 10, 16), rect)
            glow = config.scale_color(color, 0.8)
            pygame.draw.line(self.surface, glow,
                             (int(x), top), (int(x), bottom), 3)
            pygame.draw.line(self.surface, config.COLOR_WHITE,
                             (int(x), top), (int(x) + side * 6, top), 2)
            pygame.draw.line(self.surface, config.COLOR_WHITE,
                             (int(x), bottom), (int(x) + side * 6, bottom), 2)

        # Outer wall highlight
        pygame.draw.rect(self.surface, border_color,
                         pygame.Rect(int(l.table_x), int(l.table_y), int(l.table_w), int(l.table_h)),
                         4, border_radius=radius)

        # Subtle neon perimeter rails and goal-side light strips.
        accent_y = int(l.table_y + l.table_h * 0.035)
        rail_left = int(l.table_x + l.table_w * 0.12)
        rail_right = int(l.table_x + l.table_w * 0.88)
        for side, accent in ((-1, config.COLOR_P1), (1, config.COLOR_P2)):
            x = int(l.center_x + side * l.inner_w * 0.25)
            pygame.draw.line(self.surface, config.scale_color(accent, 0.48),
                             (x, int(l.table_y + 8)), (x, int(l.table_y + 15)), 2)
            pygame.draw.line(self.surface, config.scale_color(accent, 0.48),
                             (x, int(l.table_y + l.table_h - 15)),
                             (x, int(l.table_y + l.table_h - 8)), 2)
        pygame.draw.line(self.surface, config.scale_color(config.COLOR_P1, 0.38),
                         (rail_left, accent_y), (int(l.center_x - 12), accent_y), 2)
        pygame.draw.line(self.surface, config.scale_color(config.COLOR_P2, 0.38),
                         (int(l.center_x + 12), accent_y), (rail_right, accent_y), 2)
        # Goal-mouth glow accents are clipped to the table surface and cached.
        glow_layer = pygame.Surface((w, h), pygame.SRCALPHA)
        for gx, accent in ((l.inner_x, config.COLOR_P1), (l.inner_x + l.inner_w, config.COLOR_P2)):
            for thickness, alpha in ((12, 12), (7, 24), (3, 48)):
                pygame.draw.line(glow_layer, (*accent, alpha),
                                 (int(gx), top), (int(gx), bottom), thickness)
        self.surface.blit(glow_layer, (0, 0))

    def blit(self, surface):
        surface.blit(self.surface, (0, 0))
