import sys
from pathlib import Path

# PyInstaller unpacks bundled data into sys._MEIPASS; in development the
# assets folder sits next to the package.
_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def asset(name: str) -> str:
    return str(_BASE / "assets" / name)
