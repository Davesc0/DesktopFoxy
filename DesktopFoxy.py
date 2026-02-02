import random
import time
import threading
import sys
import os
from PIL import Image
import pystray
from pystray import MenuItem as item, Menu
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl

# Global variables
running = True
icon_obj = None
volume = 0.5  # 0.0 - 1.0
jumpscare_chance = 10000  # 1 in X chance
qt_app = None
jumpscare_trigger = None
active_jumpscare_window = None

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---- Signal emitter for thread-safe jumpscare triggering ---- #
class JumpscareTrigger(QtCore.QObject):
    trigger = QtCore.pyqtSignal()

# ---- QT Jumpscare Window ---- #
class JumpscareWindow(QtWidgets.QWidget):
    def __init__(self, sprite_path, sound_path, volume=0.5, num_frames=14):
        super().__init__()
        
        # Fullscreen, frameless, always on top, but TRANSPARENT TO MOUSE/KEYBOARD
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint | 
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.Tool |  # Don't show in taskbar
            QtCore.Qt.WindowType.WindowTransparentForInput  # KEY FIX: Pass through input!
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)  # Don't steal focus
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)  # Never take focus
        
        self.showFullScreen()
        
        # Get screen size for scaling frames
        screen_geometry = QtWidgets.QApplication.primaryScreen().geometry()
        self.screen_width = screen_geometry.width()
        self.screen_height = screen_geometry.height()

        # Load and split sprite sheet into frames
        sprite = Image.open(sprite_path).convert("RGBA")
        frame_height = sprite.height // num_frames
        self.frames = []
        
        for i in range(num_frames):
            frame = sprite.crop((0, i * frame_height, sprite.width, (i + 1) * frame_height))
            data = frame.tobytes("raw", "RGBA")
            qimg = QtGui.QImage(data, frame.width, frame.height, QtGui.QImage.Format.Format_RGBA8888)
            self.frames.append(QtGui.QPixmap.fromImage(qimg))

        self.frame_index = 0
        self.animation_done = False

        # Animation timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(50)

        # Setup audio playback with QSoundEffect
        self.sound_effect = QSoundEffect()
        self.sound_effect.setSource(QUrl.fromLocalFile(sound_path))
        self.sound_effect.setVolume(volume)
        
        # Close window after sound duration (approximate 1.7 seconds based on your wav)
        QtCore.QTimer.singleShot(2000, self.close)
        
        # Play sound
        self.sound_effect.play()

    def next_frame(self):
        """Advance to next animation frame"""
        if self.frame_index < len(self.frames) - 1:
            self.frame_index += 1
            self.update()
        else:
            # Hide image after last frame, sound continues
            self.animation_done = True
            self.timer.stop()
            self.update()

    def paintEvent(self, event):
        """Render current frame"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        
        if not self.animation_done and self.frames:
            frame = self.frames[self.frame_index]
            scaled = frame.scaled(
                self.screen_width, 
                self.screen_height,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            x = (self.screen_width - scaled.width()) // 2
            y = (self.screen_height - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        global active_jumpscare_window
        self.sound_effect.stop()
        active_jumpscare_window = None
        event.accept()

# ---- Jumpscare function (called in main thread via signal) ---- #
def show_jumpscare():
    """Display jumpscare window"""
    global active_jumpscare_window
    
    # Prevent multiple jumpscares at once
    if active_jumpscare_window is not None:
        return
    
    sprite_path = get_resource_path("fox.png")
    sound_path = get_resource_path("scream.wav")

    active_jumpscare_window = JumpscareWindow(sprite_path, sound_path, volume)
    active_jumpscare_window.show()

# ---- Background thread for random jumpscares ---- #
def jumpscare_loop():
    """Randomly trigger jumpscares based on configured chance"""
    global running, jumpscare_chance, jumpscare_trigger
    
    while running:
        if random.randint(1, jumpscare_chance) == 1:
            # Emit signal to trigger jumpscare in main thread
            if jumpscare_trigger:
                jumpscare_trigger.trigger.emit()
        time.sleep(1)

# ---- System tray menu functions ---- #
def set_volume(icon, item, new_volume):
    """Update global volume setting"""
    global volume
    volume = max(0.0, min(1.0, new_volume))
    print(f"Volume: {int(volume * 100)}%")
    icon.menu = create_menu()

def set_chance(icon, item, new_chance):
    """Update jumpscare probability"""
    global jumpscare_chance
    jumpscare_chance = max(100, new_chance)
    print(f"Chance: 1/{jumpscare_chance}")
    icon.menu = create_menu()

def quit_app(icon, item):
    """Gracefully quit application"""
    global running, qt_app
    running = False
    if qt_app:
        QtCore.QTimer.singleShot(0, qt_app.quit)
    icon.stop()

def trigger_test_jumpscare(icon, item):
    """Manually trigger a test jumpscare"""
    global jumpscare_trigger
    if jumpscare_trigger:
        jumpscare_trigger.trigger.emit()

def create_menu():
    """Create system tray menu"""
    global volume, jumpscare_chance
    
    def check(condition):
        return "[X]" if condition else "[ ]"
    
    return Menu(
        item('Foxy Jumpscare', None, enabled=False),
        item(f'Chance: 1/{jumpscare_chance}', None, enabled=False),
        Menu.SEPARATOR,
        item('Test jumpscare!', trigger_test_jumpscare),
        Menu.SEPARATOR,
        item('Volume', Menu(
            item(f'{check(volume == 1.0)} 100%', lambda i, j: set_volume(i, j, 1.0)),
            item(f'{check(volume == 0.75)} 75%', lambda i, j: set_volume(i, j, 0.75)),
            item(f'{check(volume == 0.5)} 50%', lambda i, j: set_volume(i, j, 0.5)),
            item(f'{check(volume == 0.25)} 25%', lambda i, j: set_volume(i, j, 0.25)),
            item(f'{check(volume == 0.0)} Mute', lambda i, j: set_volume(i, j, 0.0)),
        )),
        item('Set chance', Menu(
            item(f'{check(jumpscare_chance == 100)} 1/100 (Very frequent)', lambda i, j: set_chance(i, j, 100)),
            item(f'{check(jumpscare_chance == 500)} 1/500 (Frequent)', lambda i, j: set_chance(i, j, 500)),
            item(f'{check(jumpscare_chance == 1000)} 1/1000 (Medium)', lambda i, j: set_chance(i, j, 1000)),
            item(f'{check(jumpscare_chance == 5000)} 1/5000 (Rare)', lambda i, j: set_chance(i, j, 5000)),
            item(f'{check(jumpscare_chance == 10000)} 1/10000 (Default)', lambda i, j: set_chance(i, j, 10000)),
            item(f'{check(jumpscare_chance == 50000)} 1/50000 (Very rare)', lambda i, j: set_chance(i, j, 50000)),
        )),
        Menu.SEPARATOR,
        item('Quit', quit_app)
    )

def create_tray_icon():
    """Create system tray icon"""
    icon_path = get_resource_path("icon.ico")
    image = Image.open(icon_path)
    global icon_obj
    icon_obj = pystray.Icon("foxy_jumpscare", image, "Foxy Jumpscare", create_menu())
    return icon_obj

def run_tray_icon():
    """Run tray icon in separate thread"""
    icon = create_tray_icon()
    icon.run()

# ---- Main function ---- #
def main():
    """Initialize and run the application"""
    global running, qt_app, jumpscare_trigger
    
    print("Foxy Jumpscare started!")
    print(f"Chance: 1/{jumpscare_chance}")
    print(f"Volume: {int(volume * 100)}%")
    
    # Create QApplication in main thread
    qt_app = QtWidgets.QApplication(sys.argv)
    
    # Don't quit app when last window is closed
    qt_app.setQuitOnLastWindowClosed(False)
    
    # Create signal emitter for thread-safe jumpscare triggering
    jumpscare_trigger = JumpscareTrigger()
    jumpscare_trigger.trigger.connect(show_jumpscare)
    
    # Start background thread for random jumpscares
    jumpscare_thread = threading.Thread(target=jumpscare_loop, daemon=True)
    jumpscare_thread.start()
    
    # Start tray icon in separate thread
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()
    
    # Run Qt event loop in main thread
    sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()