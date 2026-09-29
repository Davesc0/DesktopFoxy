# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller DesktopFoxy.spec --clean --noconfirm

# Qt bits this app never touches; dropping them keeps the exe small.
QT_BLOAT = (
    "opengl32sw.dll",  # software OpenGL fallback, ~20 MB
    "Qt6Pdf", "Qt6Network", "Qt6Svg", "Qt6Quick", "Qt6Qml",
    "Qt6OpenGL", "Qt6VirtualKeyboard", "d3dcompiler",
    "qtuiotouchplugin", "libcrypto", "libssl", "qpdf", "qsvg", "qtvirtualkeyboard", "qnetworklistmanager",
)

a = Analysis(
    ['DesktopFoxy.py'],
    datas=[('assets', 'assets')],
    excludes=['tkinter', 'unittest', 'pydoc', 'ssl', '_ssl', '_hashlib', 'hashlib',
              'PyQt6.QtNetwork', 'PyQt6.QtMultimedia'],
    noarchive=False,
    optimize=2,
)
a.binaries = [b for b in a.binaries if not any(x.lower() in b[0].lower() for x in QT_BLOAT)]
a.datas = [d for d in a.datas if 'translations' not in d[0].lower()]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DesktopFoxy',
    debug=False,
    strip=False,
    upx=False,  # UPX-packed exes get flagged by antivirus far more often
    runtime_tmpdir=None,
    console=False,
    icon=['assets/icon.ico'],
)
