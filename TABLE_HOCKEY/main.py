"""Table Hockey application entry point with a central screen state manager."""
import os
import sys

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


class TableHockeyApp:
    def __init__(self):
        pygame.init()
        self.settings = SettingsStore()
        self._apply_video()
        pygame.font.init()
        self.audio = AudioManager()
        self._apply_audio()
        self.audio.start_music()
        self._build_match()
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_time = 0.0
        self.show_fps = bool(self.settings.get("show_fps", True))
        self.states = StateManager(self)
        self.fps_font = pygame.font.Font(None, 22)

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

    def _build_match(self):
        self.layout = Layout(*self.settings.resolution)
        self.match = Match(self.layout, self.settings, self.audio)
        self.renderer = TableRenderer(self.layout, self.settings.quality)
        self.view = pygame.Surface(self.layout_size, pygame.SRCALPHA)

    @property
    def layout_size(self):
        return self.settings.resolution

    def new_match(self):
        self._build_match()

    def apply_runtime_settings(self, rebuild_video=False):
        if rebuild_video:
            self._apply_video()
            self._build_match()
        else:
            self.match.configure_settings(self.settings)
            self.renderer = TableRenderer(self.layout, self.settings.quality)
        self._apply_audio()
        self.show_fps = bool(self.settings.get("show_fps", True))

    def draw_match(self, surface=None):
        target = surface or self.screen
        view = self.view
        if view.get_size() != target.get_size():
            self.view = pygame.Surface(target.get_size(), pygame.SRCALPHA)
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

    def _draw_hud(self, surface):
        font = pygame.font.Font(None, max(34, int(surface.get_width() * 0.05)))
        w = surface.get_width()
        score1 = font.render(str(self.match.players[0].score), True, config.COLOR_P1)
        score2 = font.render(str(self.match.players[1].score), True, config.COLOR_P2)
        surface.blit(score1, (w // 2 - 100, 20))
        surface.blit(score2, (w // 2 + 65, 20))
        small = pygame.font.Font(None, 25)
        label = small.render(f"{self.settings.get('ai_difficulty', 'NORMAL')}  •  FIRST TO {self.settings.win_score}", True, config.COLOR_TEXT_DIM)
        surface.blit(label, label.get_rect(midtop=(w // 2, 82)))
        if self.settings.get("show_match_timer", False):
            timer = small.render(self._format_time(self.match.match_time), True, config.COLOR_TEXT)
            surface.blit(timer, timer.get_rect(midtop=(w // 2, 108)))
        if self.match.state == "COUNTDOWN":
            whole = max(1, int(config.COUNTDOWN_SECONDS - self.match.countdown + 0.5))
            count = pygame.font.Font(None, 150).render(str(whole), True, config.COLOR_GOLD)
            surface.blit(count, count.get_rect(center=(w // 2, surface.get_height() // 2)))

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
            dt = self.clock.tick(0 if cap <= 0 else cap) / 1000.0
            dt = min(dt, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
        self.audio.stop()
        pygame.quit()


def main():
    TableHockeyApp().run()


if __name__ == "__main__":
    main()
