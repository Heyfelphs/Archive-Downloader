# ui/window.py

from PySide6.QtWidgets import QMainWindow
from ui.widgets import build_ui
from PySide6.QtCore import Qt


class AppWindow(QMainWindow):
    @staticmethod
    def _validate_int_setting(value, default):
        """Validate and convert value to int with fallback to default."""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def _validate_float_setting(value, default):
        """Validate and convert value to float with fallback to default."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
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
            from config import (
                load_ui_state,
                PICAZOR_CHECK_THREADS_DEFAULT,
                PICAZOR_CHECK_BATCH_DEFAULT,
                PICAZOR_CHECK_DELAY_DEFAULT,
            )
            state = load_ui_state()
            if not isinstance(state, dict):
                state = {}
            
            # Restaurar checkboxes
            if hasattr(central_widget, 'checkboxes'):
                checkboxes_state = state.get('checkboxes', {})
                if isinstance(checkboxes_state, dict):
                    for key, cb in central_widget.checkboxes.items():
                        if key in checkboxes_state:
                            cb.setChecked(bool(checkboxes_state[key]))
            
            # Restaurar link
            if hasattr(central_widget, 'link_input'):
                last_link = state.get('last_link', '')
                if isinstance(last_link, str):
                    central_widget.link_input.setText(last_link)
            
            # Restaurar settings do Picazor
            picazor_state = state.get('picazor_settings', {})
            if not isinstance(picazor_state, dict):
                picazor_state = {}
            
            if hasattr(central_widget, 'picazor_threads_input'):
                threads_value = self._validate_int_setting(
                    picazor_state.get('threads'), 
                    PICAZOR_CHECK_THREADS_DEFAULT
                )
                central_widget.picazor_threads_input.setValue(threads_value)
            
            if hasattr(central_widget, 'picazor_batch_input'):
                batch_value = self._validate_int_setting(
                    picazor_state.get('batch'), 
                    PICAZOR_CHECK_BATCH_DEFAULT
                )
                central_widget.picazor_batch_input.setValue(batch_value)
            
            if hasattr(central_widget, 'picazor_delay_input'):
                delay_value = self._validate_float_setting(
                    picazor_state.get('delay'), 
                    PICAZOR_CHECK_DELAY_DEFAULT
                )
                central_widget.picazor_delay_input.setValue(delay_value)
        except Exception as e:
            print(f"Erro ao restaurar estado da UI: {e}")

    def closeEvent(self, event):
        # Salvar estado das checkboxes e link
        try:
            from config import save_ui_state
            central = self.centralWidget()
            picazor_settings = {}
            if hasattr(central, 'picazor_threads_input'):
                try:
                    picazor_settings['threads'] = int(central.picazor_threads_input.value())
                except (ValueError, TypeError):
                    pass
            if hasattr(central, 'picazor_batch_input'):
                try:
                    picazor_settings['batch'] = int(central.picazor_batch_input.value())
                except (ValueError, TypeError):
                    pass
            if hasattr(central, 'picazor_delay_input'):
                try:
                    picazor_settings['delay'] = float(central.picazor_delay_input.value())
                except (ValueError, TypeError):
                    pass

            state = {
                'checkboxes': {k: cb.isChecked() for k, cb in getattr(central, 'checkboxes', {}).items()},
                'last_link': getattr(central, 'link_input', None).text() if hasattr(central, 'link_input') else '',
                'picazor_settings': picazor_settings,
            }
            save_ui_state(state)
        except Exception as e:
            print(f"Erro ao salvar estado da UI: {e}")
        super().closeEvent(event)
