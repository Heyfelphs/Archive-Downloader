# app.py

import sys
from PySide6.QtWidgets import QApplication
from ui.window import AppWindow


def start_app():
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())
