# ui/window.py

from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QFont
from ui.widgets import build_ui
from ui.widgets import reflow_thumbnails
from PySide6.QtCore import Qt


class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        from PySide6.QtGui import QIcon
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'archive-downloader.png')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle("Fapello Downloader")
        # Sempre maximizada e não redimensionável, mas pode minimizar
        # Tamanho fixo (exemplo: 1200x800), não redimensionável, pode minimizar/fechar
        self.setFixedSize(1200, 800)
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint)
        
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

        # Carregar estado salvo (checkboxes e link)
        try:
            from config import load_ui_state
            state = load_ui_state()
            # Restaurar checkboxes
            if hasattr(central_widget, 'checkboxes'):
                for key, cb in central_widget.checkboxes.items():
                    if key in state.get('checkboxes', {}):
                        cb.setChecked(state['checkboxes'][key])
            # Restaurar link
            if hasattr(central_widget, 'link_input') and 'last_link' in state:
                central_widget.link_input.setText(state['last_link'])
        except Exception as e:
            print(f"Erro ao restaurar estado da UI: {e}")

    def closeEvent(self, event):
        # Salvar estado das checkboxes e link
        try:
            from config import save_ui_state
            central = self.centralWidget()
            state = {
                'checkboxes': {k: cb.isChecked() for k, cb in getattr(central, 'checkboxes', {}).items()},
                'last_link': getattr(central, 'link_input', None).text() if hasattr(central, 'link_input') else ''
            }
            save_ui_state(state)
        except Exception as e:
            print(f"Erro ao salvar estado da UI: {e}")
        super().closeEvent(event)

    def run(self):
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            central = self.centralWidget()
            if not central or not hasattr(central, 'thumbnails_container'):
                return
            # Sempre refaz o layout das thumbnails ao redimensionar
            central.thumbnails_columns = 5
            reflow_thumbnails(central)
        except Exception:
            pass
