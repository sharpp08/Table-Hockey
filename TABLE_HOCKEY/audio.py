"""
Table Hockey - audio engine.

All sounds are synthesised with the stdlib ``audioop`` / ``math`` modules so
the game ships without any binary asset files.  If ``pygame.mixer`` cannot be
initialised (e.g. no audio device on a CI box) the engine degrades to a
silent no-op so the game still runs.

Background "music" is a tiny looping chord arpeggio generated on the fly.
"""

import math
import random

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None

SAMPLE_RATE = 22050


def _tone(freq, ms, vol=0.5, shape="sine", attack=0.008, decay=None):
    """Return a bytes object with an 8-bit signed mono tone of length ms."""
    decay = decay if decay is not None else ms
    n = int(SAMPLE_RATE * ms / 1000.0)
    out = bytearray(n)
    amp = 32767 * vol
    total = max(1, n - int(n * decay / 1000.0) if decay else n)
    for i in range(n):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * freq * t
        if shape == "sine":
            v = math.sin(phase)
        elif shape == "square":
            v = 1.0 if math.sin(phase) >= 0 else -1.0
        elif shape == "sawtooth":
            v = 2.0 * ((freq * t) % 1.0) - 1.0
        else:  # noise-ish for thumps
            v = random.uniform(-1, 1)
        # simple envelope: fast attack, exponential-ish release
        env = min(1.0, t / attack)
        release = max(0.0, 1.0 - t / (ms / 1000.0))
        env *= (release ** 1.6)
        sample = int(amp * v * env)
        sample = max(-32767, min(32767, sample))
        out[i * 2:i * 2 + 2] = sample.to_bytes(2, "little", signed=True)
        _ = total  # keep reference for clarity
    return bytes(out)


def _mix(buffers):
    """Add a list of equal-length byte buffers together, clamped."""
    length = min(len(b) for b in buffers)
    out = bytearray(length)
    for i in range(length // 2):
        acc = 0
        for b in buffers:
            acc += int.from_bytes(b[i * 2:i * 2 + 2], "little", signed=True)
        acc = max(-32767, min(32767, acc))
        out[i * 2:i * 2 + 2] = acc.to_bytes(2, "little", signed=True)
    return bytes(out)


class AudioManager:
    """Wraps pygame.mixer and lazily builds all sound effects."""

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self._music_channel = None
        self._music_playing = False
        self.master = 0.8
        self.sfx = 0.8
        self.music_vol = 0.35
        self.music_enabled = True
        self._init_mixer()

    # ------------------------------------------------------------------ #
    def _init_mixer(self):
        if pygame is None:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SAMPLE_RATE, -16, 2, 512)
            self.enabled = True
            self._build_sounds()
        except Exception as exc:
            print("[audio] mixer unavailable, running silent:", exc)
            self.enabled = False

    def _build_sounds(self):
        def load(name, data):
            self.sounds[name] = pygame.mixer.Sound(buffer=data)

        load("hit", _mix([_tone(320, 90, 0.6, "sine", 0.004),
                          _tone(700, 60, 0.25, "square", 0.004)]))
        load("wall", _tone(150, 70, 0.4, "sine", 0.004, decay=60))
        load("goal", _mix([_tone(523, 200, 0.5, "sine"),
                           _tone(659, 200, 0.5, "sine"),
                           _tone(784, 300, 0.5, "sine", decay=280)]))
        load("count", _tone(440, 120, 0.4, "square", 0.004))
        load("click", _tone(600, 40, 0.3, "sine", 0.003, decay=40))
        load("win", _mix([_tone(523, 180, 0.5), _tone(659, 180, 0.5),
                          _tone(784, 180, 0.5), _tone(1046, 400, 0.5, decay=380)]))
        load("lose", _mix([_tone(330, 200, 0.45, "sine", 0.005),
                           _tone(247, 350, 0.45, "sine", 0.005, decay=330)]))

    # ------------------------------------------------------------------ #
    def apply_volumes(self, master, sfx, music_vol, music_enabled):
        self.master = master
        self.sfx = sfx
        self.music_vol = music_vol
        self.music_enabled = music_enabled
        for s in self.sounds.values():
            s.set_volume(max(0.0, min(1.0, master * sfx)))
        if self._music_channel is not None:
            self._music_channel.set_volume(max(0.0, min(1.0, master * music_vol)))

    def play(self, name):
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    # ---- background music: a looping generated chord arpeggio -------- #
    def _make_music_loop(self):
        """Build one loop of a gentle arpeggio as a Sound we can repeat."""
        chord = [523.25, 659.25, 784.0, 659.25]   # C E G E
        step_ms = 380
        chunks = []
        for f in chord * 4:
            chunks.append(_tone(f, step_ms, 0.22, "sine", 0.02, decay=step_ms))
        data = b"".join(chunks)
        return pygame.mixer.Sound(buffer=data)

    def start_music(self):
        if not self.enabled or not self.music_enabled:
            return
        if self._music_playing:
            return
        try:
            loop = self._make_music_loop()
            self._music_channel = loop.play(-1)
            self._music_channel.set_volume(max(0.0, min(1.0, self.master * self.music_vol)))
            self._music_playing = True
        except Exception:
            pass

    def stop_music(self):
        if self._music_channel is not None:
            try:
                self._music_channel.stop()
            except Exception:
                pass
        self._music_channel = None
        self._music_playing = False

    def stop(self):
        self.stop_music()
        for s in self.sounds.values():
            try:
                s.stop()
            except Exception:
                pass
