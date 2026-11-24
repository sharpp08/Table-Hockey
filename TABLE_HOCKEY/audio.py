"""
Table Hockey - audio engine.

Sound effects and the background track are synthesised locally, so the game
ships without external audio assets. The background track is a clean,
stereo modern-arcade synth loop with a soft bass pulse, warm chord bed and
light arpeggio. No sound-effect behaviour is changed.
"""

import math
import random
from array import array

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None

SAMPLE_RATE = 22050


def _tone(freq, ms, vol=0.5, shape="sine", attack=0.008, decay=None):
    """Return a 16-bit signed mono tone of length ms."""
    n = int(SAMPLE_RATE * ms / 1000.0)
    out = bytearray(n * 2)
    amp = 32767 * vol
    for i in range(n):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * freq * t
        if shape == "sine":
            v = math.sin(phase)
        elif shape == "square":
            v = 1.0 if math.sin(phase) >= 0 else -1.0
        elif shape == "sawtooth":
            v = 2.0 * ((freq * t) % 1.0) - 1.0
        else:
            v = random.uniform(-1, 1)
        env = min(1.0, t / max(0.001, attack))
        release_ms = decay if decay is not None else ms
        release_start = max(0.0, (ms - release_ms) / 1000.0)
        if t > release_start:
            env *= max(0.0, (ms / 1000.0 - t) / max(0.001, release_ms / 1000.0))
        sample = max(-32767, min(32767, int(amp * v * env)))
        out[i * 2:i * 2 + 2] = sample.to_bytes(2, "little", signed=True)
    return bytes(out)


def _mix(buffers):
    """Add a list of equal-length 16-bit mono buffers together, clamped."""
    if not buffers:
        return b""
    length = min(len(b) for b in buffers)
    out = bytearray(length)
    for i in range(0, length, 2):
        acc = sum(int.from_bytes(b[i:i + 2], "little", signed=True) for b in buffers)
        acc = max(-32767, min(32767, acc))
        out[i:i + 2] = acc.to_bytes(2, "little", signed=True)
    return bytes(out)


class AudioManager:
    """Wraps pygame.mixer and lazily builds all sound effects."""

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self._music_channel = None
        self._music_sound = None
        self._music_playing = False
        self.master = 0.8
        self.sfx = 0.8
        self.music_vol = 0.35
        self.music_enabled = True
        self._init_mixer()

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

    def apply_volumes(self, master, sfx, music_vol, music_enabled):
        self.master = master
        self.sfx = sfx
        self.music_vol = music_vol
        self.music_enabled = music_enabled
        for sound in self.sounds.values():
            sound.set_volume(max(0.0, min(1.0, master * sfx)))
        if self._music_channel is not None:
            self._music_channel.set_volume(max(0.0, min(1.0, master * music_vol)))

    def play(self, name):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    # ---- modern arcade background music -------------------------------- #
    def _make_music_loop(self):
        """Create an original 8.57-second stereo synth loop with a soft ending."""
        bpm = 112.0
        beat = 60.0 / bpm
        seconds = beat * 16.0  # four bars, four beats per bar
        count = int(SAMPLE_RATE * seconds)

        # Warm major/minor-seventh progression: Cmaj7, Am7, Fmaj7, Gsus2.
        chords = [
            (261.63, 329.63, 392.00, 493.88),
            (220.00, 261.63, 329.63, 392.00),
            (174.61, 220.00, 261.63, 329.63),
            (196.00, 246.94, 293.66, 392.00),
        ]
        roots = (130.81, 110.00, 87.31, 98.00)
        arp_order = (0, 2, 1, 2, 3, 2, 1, 2)
        left = [0.0] * count
        right = [0.0] * count

        # A restrained, rounded bass pulse on each beat.
        for i in range(count):
            t = i / SAMPLE_RATE
            bar = min(3, int(t / (beat * 4.0)))
            local = t - bar * beat * 4.0
            beat_phase = local % beat
            bass_env = math.exp(-beat_phase * 7.0)
            bass = math.sin(2.0 * math.pi * roots[bar] * t) * bass_env * 0.105
            # Soft sustained chord bed, deliberately kept below the melody.
            pad = 0.0
            for note in chords[bar]:
                pad += math.sin(2.0 * math.pi * note * t) * 0.018
            pad *= 0.82 + 0.18 * math.sin(2.0 * math.pi * local / (beat * 4.0))
            sample = bass + pad
            left[i] += sample
            right[i] += sample

        # Bright but gentle eighth-note arpeggio; each note has a rounded decay.
        step = beat / 2.0
        for step_index in range(64):
            start_time = step_index * step
            bar = min(3, int(start_time / (beat * 4.0)))
            position = int((start_time - bar * beat * 4.0) / step) % 8
            note = chords[bar][arp_order[position]]
            start = int(start_time * SAMPLE_RATE)
            end = min(count, start + int(step * SAMPLE_RATE * 0.94))
            phase = 0.0
            for sample_index in range(start, end):
                elapsed = (sample_index - start) / SAMPLE_RATE
                env = (1.0 - math.exp(-elapsed * 95.0)) * math.exp(-elapsed * 8.5)
                value = (math.sin(phase) + 0.18 * math.sin(phase * 2.0)) * 0.072 * env
                phase += 2.0 * math.pi * note / SAMPLE_RATE
                # Subtle alternating stereo placement, never hard-panned.
                if step_index % 2:
                    left[sample_index] += value * 0.88
                    right[sample_index] += value * 1.12
                else:
                    left[sample_index] += value * 1.12
                    right[sample_index] += value * 0.88

        # Short edge fades prevent clicks at the loop boundary.
        fade = max(1, int(SAMPLE_RATE * 0.025))
        stereo = array("h")
        for i in range(count):
            edge = min(1.0, i / fade, (count - 1 - i) / fade)
            l = max(-0.95, min(0.95, left[i] * edge))
            r = max(-0.95, min(0.95, right[i] * edge))
            stereo.append(int(l * 32767))
            stereo.append(int(r * 32767))
        return pygame.mixer.Sound(buffer=stereo.tobytes())

    def start_music(self):
        if not self.enabled or not self.music_enabled or self._music_playing:
            return
        try:
            self._music_sound = self._make_music_loop()
            self._music_channel = self._music_sound.play(-1)
            if self._music_channel is not None:
                self._music_channel.set_volume(max(0.0, min(1.0, self.master * self.music_vol)))
                self._music_playing = True
        except Exception as exc:
            print("[audio] background music unavailable:", exc)

    def stop_music(self):
        if self._music_channel is not None:
            try:
                self._music_channel.stop()
            except Exception:
                pass
        self._music_channel = None
        self._music_sound = None
        self._music_playing = False

    def stop(self):
        self.stop_music()
        for sound in self.sounds.values():
            try:
                sound.stop()
            except Exception:
                pass
