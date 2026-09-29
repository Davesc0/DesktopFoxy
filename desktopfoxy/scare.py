"""The jumpscare itself: click-through fullscreen overlays plus the scream."""

import random

from PyQt6 import QtCore, QtGui, QtWidgets

from .resources import asset
from .sound import Scream

SPRITE_FRAMES = 14  # the sprite sheet is a vertical strip of frames
FRAME_MS = 50

SCREEN_MODES = {
    "all": "All screens",
    "cursor": "Screen with the mouse",
    "primary": "Primary screen",
    "random": "Random screen",
}


def load_frames(path: str, count: int) -> list[QtGui.QPixmap]:
    sheet = QtGui.QImage(path)
    if sheet.isNull():
        raise FileNotFoundError(path)
    height = sheet.height() // count
    return [
        QtGui.QPixmap.fromImage(sheet.copy(0, i * height, sheet.width(), height))
        for i in range(count)
    ]


def pick_screens(mode: str) -> list[QtGui.QScreen]:
    screens = QtGui.QGuiApplication.screens()
    if mode == "all":
        return screens
    if mode == "random":
        return [random.choice(screens)]
    if mode == "cursor":
        screen = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos())
        if screen is not None:
            return [screen]
    return [QtGui.QGuiApplication.primaryScreen()]


class Overlay(QtWidgets.QWidget):
    """Transparent, always-on-top window that never takes focus or input,
    so whatever the victim is doing keeps working underneath."""

    def __init__(self, screen: QtGui.QScreen, frames: list[QtGui.QPixmap]):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool  # no taskbar entry
            | QtCore.Qt.WindowType.WindowTransparentForInput
            | QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setGeometry(screen.geometry())

        self._frames = frames
        self._index = 0

    def set_frame(self, index: int) -> None:
        self._index = index
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        frame = self._frames[self._index]
        size = frame.size().scaled(self.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        target = QtCore.QRect(QtCore.QPoint(0, 0), size)
        target.moveCenter(self.rect().center())

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(target, frame)


class Jumpscare(QtCore.QObject):
    """Owns the preloaded assets so a scare starts instantly."""

    finished = QtCore.pyqtSignal()

    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self._frames = load_frames(asset("fox.png"), SPRITE_FRAMES)
        self._scream = Scream(asset("scream.wav"))
        self._overlays: list[Overlay] = []
        self._frame = 0
        self._active = False

        self._ticker = QtCore.QTimer(self, interval=FRAME_MS)
        self._ticker.timeout.connect(self._tick)
        self._end = QtCore.QTimer(self, singleShot=True)
        self._end.timeout.connect(self._finish)

    @property
    def active(self) -> bool:
        return self._active

    def start(self, screen_mode: str, volume: int) -> None:
        if self._active:
            return
        self._active = True
        self._frame = 0

        self._overlays = [Overlay(s, self._frames) for s in pick_screens(screen_mode)]
        for overlay in self._overlays:
            overlay.show()
        self._scream.play(volume)

        self._ticker.start()
        animation_ms = SPRITE_FRAMES * FRAME_MS
        self._end.start(max(animation_ms, self._scream.duration_ms) + 100)

    def _tick(self) -> None:
        self._frame += 1
        if self._frame < SPRITE_FRAMES:
            for overlay in self._overlays:
                overlay.set_frame(self._frame)
        else:
            # Fox is gone after the last frame; the scream plays out.
            self._ticker.stop()
            self._close_overlays()

    def _close_overlays(self) -> None:
        for overlay in self._overlays:
            overlay.close()
        self._overlays = []

    def _finish(self) -> None:
        self._ticker.stop()
        self._close_overlays()
        self._active = False
        self.finished.emit()

    def abort(self) -> None:
        self._scream.stop()
        self._end.stop()
        self._finish()
