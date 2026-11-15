"""Every sound in the game, synthesized from code (numpy). No recordings.

Run on its own to (re)build:  .venv/bin/python soundgen.py
The game calls build() at start-up; files go to .sound_cache/ (git-ignored)
and are only rebuilt when this file's VERSION changes.

  music_title  slow lyre arpeggios over a drone (Dorian mode)
  music_sea    a wandering lyre melody over a drone (Dorian mode)
  music_storm  fast low ostinato with drums (Phrygian mode)
  sea_loop     swelling waves and foam      wind_loop  howling gusts
  roar, splash, thunder, chime, chime_low    one-shot effects

The music and the two ambience loops repeat seamlessly: they are built on
a circle (filters and reverb wrap around the loop end).
"""

import os
import wave

import numpy as np

VERSION = "3"
SR = 22050                         # samples per second
D3 = 146.83                        # Hz, the tonic of every mode below

DORIAN = [0, 2, 3, 5, 7, 9, 10]    # ancient Greek modes (in semitones)
PHRYGIAN = [0, 1, 3, 5, 7, 8, 10]


# --- basics ---------------------------------------------------------------------

def seconds(n):
    return np.arange(int(n * SR)) / SR


def write(path, x, peak=0.85):
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    data = (x * 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)


def shape(x, gain):
    """Circular FFT filter: gain(freqs) -> multiplier. Loops stay seamless."""
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(spec * gain(freqs), len(x))


def band(lo, hi, soft=1.4):
    def gain(f):
        g = np.ones_like(f)
        if lo:
            g *= 1 / (1 + (lo / np.maximum(f, 1)) ** (2 * soft))
        if hi:
            g *= 1 / (1 + (f / hi) ** (2 * soft))
        return g
    return gain


def reverb(x, length=1.6, wet=0.28, seed=3):
    rng = np.random.default_rng(seed)
    t = seconds(length)
    ir = rng.standard_normal(len(t)) * np.exp(-t * 3.5)
    ir = np.pad(ir, (0, len(x) - len(ir))) if len(ir) < len(x) else ir[:len(x)]
    tail = np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(ir), len(x))
    tail *= np.std(x) / (np.std(tail) + 1e-9)
    return x * (1 - wet) + tail * wet


def place(track, sound, start):
    """Add a sound into a looping track, wrapping past the end."""
    idx = (np.arange(len(sound)) + int(start * SR)) % len(track)
    np.add.at(track, idx, sound)


def note_hz(degree, mode, octave=0, root=D3):
    steps = mode[degree % 7] + 12 * (degree // 7 + octave)
    return root * 2 ** (steps / 12)


# --- instruments ----------------------------------------------------------------

def lyre(freq, length=2.2, amp=1.0):
    """A plucked string: harmonics that fade faster the higher they are."""
    t = seconds(length)
    x = np.zeros_like(t)
    for n in range(1, 9):
        x += (1 / n ** 1.3) * np.exp(-t * (1.6 + 1.1 * n)) * \
            np.sin(2 * np.pi * n * freq * (1 + 0.0004 * n * n) * t)
    attack = np.minimum(1, t / 0.004)
    return x * attack * amp


def drone(length, freqs, rng):
    """Soft held notes, tuned to whole cycles so the loop has no click."""
    t = seconds(length)
    x = np.zeros_like(t)
    for f, a in freqs:
        f = round(f * length) / length
        swell = 0.75 + 0.25 * np.sin(2 * np.pi * t / length * 2 +
                                     rng.uniform(0, 6.28))
        x += a * swell * (np.sin(2 * np.pi * f * t) +
                          0.25 * np.sin(2 * np.pi * 2 * f * t))
    return x


def drum(length=0.5, amp=1.0):
    t = seconds(length)
    pitch = 95 * np.exp(-t * 9) + 42
    phase = 2 * np.pi * np.cumsum(pitch) / SR
    return np.sin(phase) * np.exp(-t * 7) * amp


# --- music ----------------------------------------------------------------------

def melody(rng, beats, mode, low=0, high=9):
    """A wandering phrase: small steps, rests, landing on the tonic or fifth."""
    notes, beat, degree = [], 0.0, rng.choice([0, 4])
    while beat < beats - 1:
        length = rng.choice([1, 1, 1, 2, 2, 3])
        if rng.random() < 0.18:
            beat += length                         # a rest
            continue
        notes.append((beat, degree, length))
        beat += length
        degree = int(np.clip(degree + rng.choice([-2, -1, -1, 1, 1, 2, 0]),
                             low, high))
        if beat % 8 >= 6:
            degree = rng.choice([0, 4, 7])         # cadence
    return notes


def music_sea(rng):
    bpm, beats = 66, 32
    beat_s = 60 / bpm
    length = beats * beat_s
    track = drone(length, [(D3 / 2, 0.5), (D3 * 0.75, 0.35)], rng) * 0.35
    for beat, degree, n in melody(rng, beats, DORIAN):
        place(track, lyre(note_hz(degree, DORIAN), 2.0 + n * 0.4, 0.9),
              beat * beat_s)
        if beat % 8 == 0:                          # a low bass pluck
            place(track, lyre(D3 / 2, 3.0, 0.6), beat * beat_s)
    return reverb(track)


def music_title(rng):
    bpm, beats = 56, 32
    beat_s = 60 / bpm
    length = beats * beat_s
    track = drone(length, [(D3 / 2, 0.6), (D3 * 0.75, 0.3), (D3, 0.15)],
                  rng) * 0.4
    chords = [[0, 4, 7, 9], [3, 5, 7, 10], [0, 2, 4, 7], [4, 6, 8, 11]]
    for bar in range(beats // 4):
        chord = chords[bar % len(chords)]
        for k, degree in enumerate(chord):
            when = (bar * 4 + k * 0.75) * beat_s
            place(track, lyre(note_hz(degree, DORIAN), 3.0, 0.7), when)
        if bar % 2 == 1:                           # a reply in the high voice
            d = chord[-1] + int(rng.choice([1, 2, -1]))
            place(track, lyre(note_hz(d, DORIAN, 1), 2.5, 0.45),
                  (bar * 4 + 3.25) * beat_s)
    return reverb(track, length=2.2, wet=0.35)


def music_storm(rng):
    bpm, beats = 116, 32
    beat_s = 60 / bpm
    length = beats * beat_s
    track = drone(length, [(D3 / 4, 0.7), (D3 / 4 * 2 ** (1 / 12), 0.25)],
                  rng) * 0.35
    riff = [0, 0, 1, 0, 3, 1, 0, -2]               # eighth notes, low register
    for k in range(beats * 2):
        degree = riff[k % len(riff)] + (2 if (k // 16) % 2 else 0)
        place(track, lyre(note_hz(degree, PHRYGIAN, -1), 0.6, 0.8),
              k * beat_s / 2)
    for b in range(beats):
        if b % 2 == 0:
            place(track, drum(0.5, 1.6), b * beat_s)
        if b % 4 == 3:
            place(track, drum(0.4, 0.9), (b + 0.5) * beat_s)
    for beat, degree, n in melody(rng, beats, PHRYGIAN, 4, 11):
        if rng.random() < 0.6:
            place(track, lyre(note_hz(degree, PHRYGIAN), 1.2, 0.5),
                  beat * beat_s)
    return reverb(track, length=1.2, wet=0.22)


# --- ambience loops -------------------------------------------------------------

def sea_loop(rng, length=10.0):
    t = seconds(length)
    rumble = shape(rng.standard_normal(len(t)),
                   lambda f: band(0, 900)(f) / np.sqrt(np.maximum(f, 20)))
    foam = shape(rng.standard_normal(len(t)), band(2500, 7000))
    swell = (0.5 + 0.5 * np.sin(2 * np.pi * t / 5.0)) ** 2 * 0.7 + \
            (0.5 + 0.5 * np.sin(2 * np.pi * t / 2.5 + 1.3)) ** 3 * 0.3
    rumble /= np.std(rumble)
    foam /= np.std(foam)
    return rumble * (0.35 + 0.65 * swell) + foam * swell ** 3 * 0.35


def wind_loop(rng, length=12.0):
    t = seconds(length)
    x = np.zeros_like(t)
    for k, (center, width, period) in enumerate(
            [(380, 60, 6.0), (520, 45, 4.0), (760, 70, 3.0), (300, 200, 12.0)]):
        voice = shape(rng.standard_normal(len(t)),
                      band(center - width, center + width, soft=3))
        voice /= np.std(voice)
        gust = 0.5 + 0.5 * np.sin(2 * np.pi * t / period + k * 1.7)
        x += voice * gust ** 2
    return x


# --- effects --------------------------------------------------------------------

def splash(rng):
    t = seconds(1.0)
    hiss = shape(rng.standard_normal(len(t)), band(700, 6000))
    hiss = hiss / np.std(hiss) * np.exp(-t * 6) * np.minimum(1, t / 0.006)
    bubbles = np.zeros_like(t)
    for k in range(6):
        start = rng.uniform(0.05, 0.5)
        f0 = rng.uniform(350, 800)
        tb = np.clip(t - start, 0, None)
        bubbles += (t > start) * np.sin(2 * np.pi * f0 * tb * (1 + 3 * tb)) \
            * np.exp(-tb * 30) * 0.35
    return hiss + bubbles


def roar(rng):
    t = seconds(2.4)
    pitch = 72 - 26 * t / 2.4
    phase = 2 * np.pi * np.cumsum(pitch) / SR
    voice = sum(np.sin(phase * n) / n for n in range(1, 12))
    growl = 0.6 + 0.4 * np.sin(2 * np.pi * 17 * t)
    rumble = shape(rng.standard_normal(len(t)), band(30, 420))
    rumble /= np.std(rumble)
    env = np.minimum(1, t / 0.25) * np.exp(-np.clip(t - 1.2, 0, None) * 2.5)
    return (voice * growl * 0.8 + rumble * 0.6) * env


def thunder(rng):
    t = seconds(4.0)
    crack = shape(rng.standard_normal(len(t)), band(1500, 8000))
    crack = crack / np.std(crack) * np.exp(-t * 25)
    rumble = shape(rng.standard_normal(len(t)), band(20, 160))
    rumble /= np.std(rumble)
    rolls = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * t * 1.3)) * \
        np.abs(np.sin(2 * np.pi * t * 0.55))
    return crack * 0.9 + rumble * rolls * np.exp(-t * 0.8) * \
        np.minimum(1, t / 0.08)


def chime(freq):
    t = seconds(2.2)
    x = np.zeros_like(t)
    for ratio, amp, decay in [(1, 1, 2.2), (2.0, 0.5, 3.0), (2.76, 0.4, 3.8),
                              (4.07, 0.25, 5.5), (5.4, 0.15, 7.0)]:
        x += amp * np.exp(-t * decay) * np.sin(2 * np.pi * freq * ratio * t)
    return x * np.minimum(1, t / 0.003)


# --- build everything ------------------------------------------------------------

def build(folder):
    """Write all sounds into folder (skipped if already built)."""
    stamp = os.path.join(folder, "VERSION")
    if os.path.exists(stamp) and open(stamp).read() == VERSION:
        return folder
    os.makedirs(folder, exist_ok=True)
    rng = np.random.default_rng(2026)
    sounds = {
        "music_title.wav": music_title(rng),
        "music_sea.wav": music_sea(rng),
        "music_storm.wav": music_storm(rng),
        "sea_loop.wav": sea_loop(rng),
        "wind_loop.wav": wind_loop(rng),
        "splash.wav": splash(rng),
        "roar.wav": roar(rng),
        "thunder.wav": thunder(rng),
        "chime.wav": chime(880.0),
        "chime_low.wav": chime(440.0 * 2 ** (3 / 12)),
    }
    for name, x in sounds.items():
        write(os.path.join(folder, name), x)
    with open(stamp, "w") as f:
        f.write(VERSION)
    return folder


if __name__ == "__main__":
    import time
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, ".sound_cache")
    if os.path.exists(os.path.join(out, "VERSION")):
        os.remove(os.path.join(out, "VERSION"))
    t0 = time.perf_counter()
    build(out)
    print(f"built in {time.perf_counter() - t0:.1f}s ->", out)
