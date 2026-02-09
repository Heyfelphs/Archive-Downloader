# ui/window.py

from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QFont
from ui.widgets import build_ui
from ui.widgets import reflow_thumbnails
from PySide6.QtCore import Qt


class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fapello Downloader")
        self.setGeometry(100, 100, 1200, 700)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        # Build UI
        central_widget = build_ui(self)
        self.setCentralWidget(central_widget)

    def run(self):
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            central = self.centralWidget()
            if not central or not hasattr(central, 'thumbnails_container'):
                return
            thumbnails_container = central.thumbnails_container
            # Determine available width inside the scroll area / container
            available = thumbnails_container.width()
            if available <= 0:
                parent = thumbnails_container.parentWidget()
                if parent:
                    available = parent.width()
            # thumbnail + spacing heuristic
            thumb_size = 80
            spacing = 8
            cols = max(1, available // (thumb_size + spacing))
            if getattr(central, 'thumbnails_columns', None) != cols:
                central.thumbnails_columns = cols
                reflow_thumbnails(central)
        except Exception:
            pass
