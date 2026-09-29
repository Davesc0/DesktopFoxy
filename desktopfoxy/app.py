"""Tray icon, settings and the once-a-second dice roll."""

import os
import random
import sys

from PyQt6 import QtCore, QtGui, QtWidgets

from . import __version__, autostart
from .resources import asset
from .scare import SCREEN_MODES, Jumpscare

# The whole point of the mod: every second, a 1 in X chance of Foxy.
CHANCES = [
    (100, "1/100 (Very frequent)"),
    (500, "1/500 (Frequent)"),
    (1000, "1/1000 (Medium)"),
    (5000, "1/5000 (Rare)"),
    (10000, "1/10000 (Default)"),
    (50000, "1/50000 (Very rare)"),
]
VOLUMES = [100, 75, 50, 25, 0]
ROLL_MS = 1000
SNOOZE_MS = 60 * 60 * 1000

DEFAULTS = {"chance": 10000, "volume": 50, "screens": "all"}


class FoxyApp(QtCore.QObject):
    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self._settings = QtCore.QSettings()
        self.chance = self._load("chance", int, [c for c, _ in CHANCES])
        self.volume = self._load("volume", int, VOLUMES)
        self.screens = self._load("screens", str, list(SCREEN_MODES))

        self.scare = Jumpscare(self)

        self._roller = QtCore.QTimer(self, interval=ROLL_MS)
        self._roller.timeout.connect(self._roll)
        self._snooze = QtCore.QTimer(self, singleShot=True)
        self._snooze.timeout.connect(lambda: self.set_paused(False))

        autostart.refresh()
        self._build_tray()
        self.set_paused(False)

    # ---- settings ---- #

    def _load(self, key: str, kind: type, allowed: list):
        value = self._settings.value(key, DEFAULTS[key], type=kind)
        return value if value in allowed else DEFAULTS[key]

    def _save(self, key: str, value) -> None:
        setattr(self, key, value)
        self._settings.setValue(key, value)

    def set_chance(self, chance: int) -> None:
        self._save("chance", chance)

    def set_volume(self, volume: int) -> None:
        self._save("volume", volume)

    def set_screens(self, mode: str) -> None:
        self._save("screens", mode)

    # ---- scheduling ---- #

    @property
    def paused(self) -> bool:
        return self._pause_action.isChecked()

    def _roll(self) -> None:
        if random.randrange(self.chance) == 0:
            self.trigger()

    def trigger(self) -> None:
        self.scare.start(self.screens, self.volume)

    def set_paused(self, paused: bool) -> None:
        self._pause_action.setChecked(paused)
        if paused:
            self._roller.stop()
        else:
            self._snooze.stop()
            self._roller.start()
        self._update_tooltip()

    def snooze(self) -> None:
        self.set_paused(True)
        self._snooze.start(SNOOZE_MS)
        self._update_tooltip()

    # ---- tray ---- #

    def _update_tooltip(self) -> None:
        if self._snooze.isActive():
            state = "snoozed for an hour"
        elif self.paused:
            state = "paused"
        else:
            state = "watching you"
        self._tray.setToolTip(f"Desktop Foxy - {state}")

    def _choice_menu(self, title: str, options, current, on_pick) -> QtWidgets.QMenu:
        menu = QtWidgets.QMenu(title, self._menu)
        group = QtGui.QActionGroup(menu)
        for value, label in options:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(value == current)
            action.triggered.connect(lambda _=False, v=value: on_pick(v))
            group.addAction(action)
        return menu

    def _build_tray(self) -> None:
        self._menu = QtWidgets.QMenu()
        header = self._menu.addAction(f"Desktop Foxy {__version__}")
        header.setEnabled(False)
        self._menu.addSeparator()

        self._menu.addAction("Test jumpscare!", self.trigger)
        self._pause_action = self._menu.addAction("Paused")
        self._pause_action.setCheckable(True)
        self._pause_action.triggered.connect(self.set_paused)
        self._menu.addAction("Snooze for 1 hour", self.snooze)
        self._menu.addSeparator()

        self._menu.addMenu(self._choice_menu(
            "Chance per second", CHANCES, self.chance, self.set_chance))
        self._menu.addMenu(self._choice_menu(
            "Volume", [(v, f"{v}%" if v else "Mute") for v in VOLUMES],
            self.volume, self.set_volume))
        self._menu.addMenu(self._choice_menu(
            "Screens", SCREEN_MODES.items(), self.screens, self.set_screens))

        startup = self._menu.addAction("Start with Windows")
        startup.setCheckable(True)
        startup.setChecked(autostart.is_enabled())
        startup.setEnabled(autostart.supported())
        if not autostart.supported():
            startup.setText("Start with Windows (exe only)")
        startup.toggled.connect(autostart.set_enabled)
        self._menu.addSeparator()

        self._menu.addAction("Quit", QtWidgets.QApplication.quit)

        self._tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon(asset("icon.ico")), self)
        self._tray.setContextMenu(self._menu)
        self._tray.show()


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("DesktopFoxy")
    app.setApplicationName("DesktopFoxy")
    app.setQuitOnLastWindowClosed(False)

    # One fox is enough: a second launch (e.g. autostart + double-click) just exits.
    lock = QtCore.QLockFile(os.path.join(QtCore.QDir.tempPath(), "DesktopFoxy.lock"))
    if not lock.tryLock(0):
        return 0

    foxy = FoxyApp()
    if "--scare-now" in sys.argv:
        QtCore.QTimer.singleShot(500, foxy.trigger)
    if "--scare-and-quit" in sys.argv:  # smoke test for builds
        QtCore.QTimer.singleShot(500, foxy.trigger)
        foxy.scare.finished.connect(app.quit)

    return app.exec()
