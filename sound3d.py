"""Music and sound effects for the voyage, all synthesized by soundgen.py.

Three music tracks crossfade: slow lyre arpeggios on the title and ending,
a wandering lyre melody at sea, a fast drum-driven ostinato while the
cyclone hunts. Sea waves always play; storm wind swells as the cyclone
closes in. One-shot effects: kraken roar and splash, thunder, chimes.
Set ODYSSEY_MUTE=1 to run silently (used by the automated tests).
"""

import os

from panda3d.core import Filename

import soundgen

MUSIC = {"title": "music_title.wav", "sea": "music_sea.wav",
         "storm": "music_storm.wav"}
MUSIC_VOLUME = 0.55
EFFECTS = {"roar": "roar.wav", "splash": "splash.wav",
           "thunder": "thunder.wav", "chime": "chime.wav",
           "chime_low": "chime_low.wav", "ithaca": "ithaca.wav"}
FADE_PER_SECOND = 0.6


class Sound:
    def __init__(self, base, folder):
        self.base = base
        self.muted = bool(os.environ.get("ODYSSEY_MUTE"))

        def path(name):
            return Filename.fromOsSpecific(os.path.join(folder, name))

        if self.muted:
            return
        soundgen.build(folder)
        self.music = {}
        for key, name in MUSIC.items():
            track = base.loader.loadMusic(path(name))
            track.setLoop(True)
            track.setVolume(0.0)
            self.music[key] = track
        self.music_volume = {key: 0.0 for key in self.music}

        self.sea = base.loader.loadSfx(path("sea_loop.wav"))
        self.sea.setLoop(True)
        self.sea.setVolume(0.45)
        self.sea.play()
        self.wind = base.loader.loadSfx(path("wind_loop.wav"))
        self.wind.setLoop(True)
        self.wind.setVolume(0.0)
        self.wind.play()
        self.wind_volume = 0.0

        self.effects = {key: base.loader.loadSfx(path(name))
                        for key, name in EFFECTS.items()}

    def play(self, name, volume=1.0, start=0.0):
        if self.muted:
            return
        sfx = self.effects[name]
        sfx.stop()
        sfx.setVolume(volume)
        sfx.setTime(start)
        sfx.play()

    def thunder(self):
        self.play("thunder", 0.9)

    def celebrate(self):
        """The homecoming. Returns how long it lasts (seconds)."""
        if self.muted:
            return 0.0
        self.play("ithaca", 1.0)
        return self.effects["ithaca"].length()

    def update(self, dt, music, wind):
        """music: 'title' / 'sea' / 'storm' / None; wind: 0..1."""
        if self.muted:
            return
        step = FADE_PER_SECOND * dt
        for key, track in self.music.items():
            target = MUSIC_VOLUME if key == music else 0.0
            v = self.music_volume[key]
            v = min(target, v + step) if v < target else max(target, v - step)
            self.music_volume[key] = v
            if v > 0 and track.status() != track.PLAYING:
                track.play()
            elif v <= 0 and track.status() == track.PLAYING:
                track.stop()
            track.setVolume(v)
        self.wind_volume += (wind - self.wind_volume) * min(1.0, dt * 2)
        self.wind.setVolume(self.wind_volume)
