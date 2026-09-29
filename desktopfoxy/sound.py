"""Scream playback through the plain Windows sound API.

Qt Multimedia drags FFmpeg into the build (tens of MB) just to play one WAV,
so this uses the stdlib ``winsound`` module instead. ``PlaySound`` has no
volume control, so quieter copies of the WAV are rendered into the temp
folder on demand.
"""

import tempfile
import wave
from array import array
from pathlib import Path

try:
    import winsound
except ImportError:  # not on Windows: stay silent instead of crashing
    winsound = None


class Scream:
    def __init__(self, path: str):
        self._path = path
        with wave.open(path, "rb") as wav:
            self._params = wav.getparams()
            self._frames = wav.readframes(wav.getnframes())
        self.duration_ms = round(1000 * self._params.nframes / self._params.framerate)
        self._cache_dir = Path(tempfile.gettempdir()) / "DesktopFoxy"
        self._variants: dict[int, str] = {100: path}

    def _file_for(self, volume: int) -> str:
        if volume in self._variants:
            return self._variants[volume]
        if self._params.sampwidth != 2:  # only 16-bit PCM is scaled
            return self._path

        factor = volume / 100
        samples = array("h", self._frames)
        scaled = array("h", (int(s * factor) for s in samples))

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        out = self._cache_dir / f"scream_{volume}.wav"
        with wave.open(str(out), "wb") as wav:
            wav.setparams(self._params)
            wav.writeframes(scaled.tobytes())
        self._variants[volume] = str(out)
        return str(out)

    def play(self, volume: int) -> None:
        if winsound is None or volume <= 0:
            return
        flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
        winsound.PlaySound(self._file_for(volume), flags)

    def stop(self) -> None:
        if winsound is not None:
            winsound.PlaySound(None, 0)
