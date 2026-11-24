"""Table Hockey application entry point with a central screen state manager."""
import os
import sys
import json

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import pygame
import config
from audio import AudioManager
from match import Match
from settings import Layout, SettingsStore
from ui import TableRenderer
from states import StateManager
from skins import get_skin


class TableHockeyApp:
    def __init__(self):
        pygame.init()
        self.settings = SettingsStore()
        self._apply_video()
        pygame.font.init()
        self.audio = AudioManager()
        self._apply_audio()
        self.audio.start_music()
        self.current_level = self._load_current_level()
        self.player_skin_id = self._load_player_skin()
        self._build_match()
        self.clock = pygame.time.Clock()
        self.fixed_dt = 1.0 / 120.0
        self._update_accumulator = 0.0
        self.running = True
        self.game_time = 0.0
        self.show_fps = bool(self.settings.get("show_fps", True))
        self.states = StateManager(self)
        self.fps_font = self._font(22)
        self._font_cache = {}
        self._hud_panel_cache = {}

    def _apply_video(self):
        flags = pygame.FULLSCREEN if self.settings.fullscreen else 0
        self.screen = pygame.display.set_mode(self.settings.resolution, flags)
        pygame.display.set_caption(config.CAPTION)

    def _apply_audio(self):
        self.audio.apply_volumes(
            self.settings.get("master_volume", 0.8),
            self.settings.get("sfx_volume", 0.8),
            self.settings.get("music_volume", 0.35),
            self.settings.get("music_enabled", True),
        )
        if self.settings.get("music_enabled", True):
            self.audio.start_music()
        else:
            self.audio.stop_music()

    def _load_current_level(self):
        path = os.path.join(_THIS_DIR, "save", "high_scores.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return max(1, min(30, int(data.get("current_level", 1)))) if isinstance(data, dict) else 1
        except (OSError, ValueError, TypeError, AttributeError):
            return 1

    def _load_player_skin(self):
        path = os.path.join(_THIS_DIR, "save", "high_scores.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return max(0, min(30, int(data.get("equipped_skin", 0)))) if isinstance(data, dict) else 0
        except (OSError, ValueError, TypeError, AttributeError):
            return 0

    def _build_match(self):
        self.layout = Layout(*self.screen.get_size())
        self.match = Match(self.layout, self.settings, self.audio, level=self.current_level,
                           player_skin_id=self.player_skin_id)
        self.renderer = TableRenderer(self.layout, self.settings.quality, self.settings.get("table_theme", "NEON"))
        self.view = pygame.Surface(self.layout_size)

    @property
    def layout_size(self):
        return self.screen.get_size()

    def new_match(self):
        self._build_match()

    def apply_runtime_settings(self, rebuild_video=False):
        if rebuild_video:
            # Preserve the live match when settings are opened from PAUSED.
            old_layout = self.layout
            puck_pos = self.match.puck.pos.copy()
            puck_velocity = self.match.puck.velocity.copy()
            puck_active = self.match.puck.active
            paddle_data = [(p.pos.copy(), p.velocity.copy()) for p in self.match.paddles]
            self._apply_video()
            self.layout = Layout(*self.screen.get_size())
            if (old_layout.w, old_layout.h) != (self.layout.w, self.layout.h):
                sx, sy = self.layout.w / old_layout.w, self.layout.h / old_layout.h
                self.match.configure_layout(self.layout)
                self.match.puck.pos.update(puck_pos.x * sx, puck_pos.y * sy)
                self.match.puck.velocity.update(puck_velocity.x * sx, puck_velocity.y * sy)
                self.match.puck.active = puck_active
                for paddle, (position, velocity) in zip(self.match.paddles, paddle_data):
                    paddle.pos.update(position.x * sx, position.y * sy)
                    paddle.previous_pos = paddle.pos.copy()
                    paddle.velocity.update(velocity.x * sx, velocity.y * sy)
                self.match.ai.reset(self.match.paddles[1].pos)
            self.match.configure_settings(self.settings)
            self.renderer = TableRenderer(self.layout, self.settings.quality, self.settings.get("table_theme", "NEON"))
            self.view = pygame.Surface(self.layout_size)
        else:
            self.match.configure_settings(self.settings)
            self.renderer = TableRenderer(self.layout, self.settings.quality, self.settings.get("table_theme", "NEON"))
        self._apply_audio()
        self.show_fps = bool(self.settings.get("show_fps", True))

    def draw_match(self, surface=None):
        target = surface or self.screen
        view = self.view
        if view.get_size() != target.get_size():
            self.view = pygame.Surface(target.get_size())
            view = self.view
        self.renderer.blit(view)
        quality = self.settings.quality
        self.match.paddles[0].draw(view, quality, self.game_time)
        self.match.paddles[1].draw(view, quality, self.game_time)
        self.match.puck.draw(view, quality, self.game_time)
        self.match.effects.draw(view)
        self._draw_hud(view)
        shake = self.match.effects.shake_offset() if self.settings.get("screen_shake", True) else (0, 0)
        target.fill(config.COLOR_BLACK)
        target.blit(view, shake)

    def _font(self, size):
        size = max(14, int(size))
        font = self._font_cache.get(size)
        if font is None:
            font = pygame.font.Font(None, size)
            self._font_cache[size] = font
        return font

    def _draw_hud(self, surface):
        """Anime sports-broadcast HUD with team plates and campaign progress."""
        w, h = surface.get_size()
        cx = w // 2
        plate_w = max(132, min(190, int(w * 0.16)))
        plate_h = max(54, int(h * 0.085))
        top = max(12, int(h * 0.018))
        gap = max(12, int(w * 0.018))
        left_rect = pygame.Rect(cx - gap // 2 - plate_w, top, plate_w, plate_h)
        right_rect = pygame.Rect(cx + gap // 2, top, plate_w, plate_h)

        def team_plate(rect, accent, label, score, align_right=False):
            key = (rect.size, accent)
            panel = self._hud_panel_cache.get(key)
            if panel is None:
                panel = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(panel, (5, 10, 22, 205), panel.get_rect(), border_radius=10)
                pygame.draw.rect(panel, (*accent, 215), panel.get_rect(), 2, border_radius=10)
                bar_x = rect.w - 5 if align_right else 3
                pygame.draw.rect(panel, (*accent, 235),
                                 (bar_x, 8, 2, rect.h - 16), border_radius=1)
                self._hud_panel_cache[key] = panel
            surface.blit(panel, rect.topleft)
            label_font = self._font(max(16, int(plate_h * 0.27)))
            score_font = self._font(max(34, int(plate_h * 0.70)))
            label_image = label_font.render(label, True, accent)
            score_image = score_font.render(str(score), True, config.COLOR_WHITE)
            label_x = rect.right - 12 if align_right else rect.left + 12
            label_anchor = label_image.get_rect(
                midright=(label_x, rect.top + int(plate_h * 0.28))
            ) if align_right else label_image.get_rect(
                midleft=(label_x, rect.top + int(plate_h * 0.28))
            )
            score_anchor = score_image.get_rect(
                midright=(rect.right - 13, rect.bottom - 8)
            ) if align_right else score_image.get_rect(
                midleft=(rect.left + 13, rect.bottom - 8)
            )
            surface.blit(label_image, label_anchor)
            shadow = score_font.render(str(score), True, accent)
            surface.blit(shadow, score_anchor.move(2, 2))
            surface.blit(score_image, score_anchor)

        team_plate(left_rect, config.COLOR_P1, "PLAYER", self.match.players[0].score)
        team_plate(right_rect, config.COLOR_P2, "CPU", self.match.players[1].score, True)

        level_font = self._font(max(18, int(h * 0.032)))
        level_text = level_font.render(
            f"LEVEL {self.match.level:02d} / 30", True, config.COLOR_GOLD
        )
        surface.blit(level_text, level_text.get_rect(midtop=(cx, top + plate_h + 7)))
        bar_w = max(100, int(w * 0.13))
        bar_y = top + plate_h + 31
        bar = pygame.Rect(cx - bar_w // 2, bar_y, bar_w, 4)
        pygame.draw.rect(surface, (32, 43, 62), bar, border_radius=2)
        progress = pygame.Rect(bar.x, bar.y, int(bar.w * self.match.level / 30), bar.h)
        pygame.draw.rect(surface, config.COLOR_GOLD, progress, border_radius=2)

        if self.settings.get("show_match_timer", False):
            small = pygame.font.Font(None, 22)
            timer = small.render(self._format_time(self.match.match_time), True, config.COLOR_TEXT)
            surface.blit(timer, timer.get_rect(midtop=(cx, bar_y + 9)))

        if self.match.state == "COUNTDOWN":
            whole = max(1, int(config.COUNTDOWN_SECONDS - self.match.countdown + 0.5))
            count_font = self._font(150)
            count = count_font.render(str(whole), True, config.COLOR_GOLD)
            outline = count_font.render(str(whole), True, config.COLOR_P1)
            rect = count.get_rect(center=(cx, h // 2))
            surface.blit(outline, rect.move(4, 4))
            surface.blit(count, rect)

    @staticmethod
    def _format_time(seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def update(self, dt):
        self.game_time += dt
        self.states.update(dt)

    def draw(self):
        self.states.draw(self.screen)
        if self.show_fps:
            fps = self.fps_font.render(f"{self.clock.get_fps():.0f} FPS", True, config.COLOR_TEXT_DIM)
            self.screen.blit(fps, (12, 10))
        pygame.display.flip()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        else:
            self.states.handle_event(event)

    def run(self):
        while self.running:
            cap = int(self.settings.get("fps_cap", 60))
            frame_dt = min(self.clock.tick(0 if cap <= 0 else cap) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self._update_accumulator += frame_dt
            # Run gameplay at a stable 120 Hz regardless of display refresh rate.
            steps = 0
            while self._update_accumulator >= self.fixed_dt and steps < 8:
                self.update(self.fixed_dt)
                self._update_accumulator -= self.fixed_dt
                steps += 1
            if steps >= 8:
                self._update_accumulator = 0.0
            self.draw()
        self.audio.stop()
        pygame.quit()


def main():
    TableHockeyApp().run()


if __name__ == "__main__":
    main()
