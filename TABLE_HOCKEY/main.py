"""Entry point for Table Hockey.

Run from the project root with the venv active:

    .\\venv\\Scripts\\python TABLE_HOCKEY\\main.py

All game modules live in the same folder, so add that folder to the path
before importing them.
"""

import os
import sys

# Make sibling modules (match, physics, config, ...) importable no matter
# where the script is launched from.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import pygame

import config
from audio import AudioManager
from match import Match
from settings import Layout, SettingsStore
from ui import TableRenderer


class TableHockeyApp:
    """Owns the window, audio, match and the main update/render loop."""

    def __init__(self):
        self.settings = SettingsStore()
        self._apply_video()

        pygame.font.init()

        self.audio = AudioManager()
        self.audio.apply_volumes(
            self.settings.get("master_volume", 0.8),
            self.settings.sfx_volume,
            self.settings.music_volume,
            self.settings.get("music_enabled", True),
        )
        self.audio.start_music()

        layout = Layout(*self.settings.resolution)
        self.match = Match(layout, self.settings, self.audio)

        self.renderer = TableRenderer(layout, self.settings.quality)
        # Scratch surface the world is drawn onto before being composited onto
        # the real display surface (used by screen shake).
        self.view = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_time = 0.0

    # ------------------------------------------------------------------ #
    def _apply_video(self):
        flags = pygame.FULLSCREEN if self.settings.fullscreen else 0
        self.screen = pygame.display.set_mode(self.settings.resolution, flags)
        pygame.display.set_caption(config.CAPTION)

    # ------------------------------------------------------------------ #
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Escape pauses during play, quits from the pause/menu state.
                if self.match.state in ("PLAYING", "COUNTDOWN", "GOAL"):
                    self.match.toggle_pause()
                else:
                    self.running = False
            elif event.key == pygame.K_p and self.match.is_active:
                self.match.toggle_pause()
            elif event.key == pygame.K_r and self.match.state == "GAMEOVER":
                self.match.reset_match()

    # ------------------------------------------------------------------ #
    def update(self, dt):
        self.game_time += dt
        keys = pygame.key.get_pressed()

        # match.update() advances state and returns audio/UI event names
        # ("count", "serve", "wall", "hit", "resume"); the audio cues are
        # fired inside Match via _play, so the returned list is consumed
        # here if any extra UI reactions are ever needed.
        events = self.match.update(dt, keys)

        # Drain the physics event queue (paddle/wall/goal) so the next
        # frame starts clean.
        self.match.drain_events()
        del events  # reserved for future HUD/audio reactions.

    # ------------------------------------------------------------------ #
    def draw(self):
        # The world is rendered onto a scratch surface so screen shake can be
        # applied when compositing it onto the real display surface (a blit
        # offset rather than a non-existent transform.offset).
        view = self.view
        self.renderer.blit(view)

        quality = self.settings.quality
        self.match.paddles[0].draw(view, quality, self.game_time)
        self.match.paddles[1].draw(view, quality, self.game_time)
        self.match.puck.draw(view, quality, self.game_time)
        self.match.effects.draw(view)

        self._draw_hud(view)

        shake = self.match.effects.shake_offset()
        if shake:
            self.screen.fill(config.COLOR_BLACK)
            self.screen.blit(view, shake)
        else:
            self.screen.blit(view, (0, 0))

        if self.match.state == "PAUSED":
            self._draw_overlay("PAUSED", "Press P to resume, Esc to quit")
        elif self.match.state == "GAMEOVER":
            self._draw_overlay(self._winner_text(), "Press R to play again, Esc to quit")

    def _apply_shake(self, shake_offset):
        """Composite the shaken view onto the display surface."""
        if not shake_offset:
            self.screen.blit(self.view, (0, 0))
            return
        self.screen.fill(config.COLOR_BLACK)
        self.screen.blit(self.view, shake_offset)

    def _winner_text(self):
        name = self.match.players[self.match.winner - 1].name
        return f"{name} WINS!"

    # ------------------------------------------------------------------ #
    def _draw_hud(self, surface):
        font = pygame.font.Font(None, 64)
        score1 = font.render(str(self.match.players[0].score), True, config.COLOR_P1)
        score2 = font.render(str(self.match.players[1].score), True, config.COLOR_P2)

        w = surface.get_width()
        surface.blit(score1, (w // 2 - 120, 24))
        surface.blit(score2, (w // 2 + 80, 24))

        if self.settings.get("show_match_timer", False):
            timer = font.render(
                self._format_time(self.match.match_time), True, config.COLOR_TEXT
            )
            surface.blit(timer, timer.get_rect(midtop=(w // 2, 8)))

        if self.match.state == "COUNTDOWN":
            whole = max(1, int(config.COUNTDOWN_SECONDS - self.match.countdown + 0.5))
            count_font = pygame.font.Font(None, 160)
            count = count_font.render(str(whole), True, config.COLOR_GOLD)
            surface.blit(
                count, count.get_rect(center=(w // 2, surface.get_height() // 2))
            )

    @staticmethod
    def _format_time(seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    # ------------------------------------------------------------------ #
    def _draw_overlay(self, title, subtitle):
        w, h = self.screen.get_size()
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        self.screen.blit(panel, (0, 0))

        title_img = pygame.font.Font(None, 96).render(title, True, config.COLOR_GOLD)
        sub_img = pygame.font.Font(None, 36).render(subtitle, True, config.COLOR_TEXT)
        self.screen.blit(title_img, title_img.get_rect(center=(w // 2, h // 2 - 40)))
        self.screen.blit(sub_img, sub_img.get_rect(center=(w // 2, h // 2 + 40)))

    # ------------------------------------------------------------------ #
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)

            self.update(dt)
            self.draw()
            pygame.display.flip()

        self.audio.stop()
        pygame.quit()


def main():
    app = TableHockeyApp()
    app.run()


if __name__ == "__main__":
    main()
