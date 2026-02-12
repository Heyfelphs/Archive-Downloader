# ui/window.py

from PySide6.QtWidgets import QMainWindow, QApplication, QMessageBox
from ui.widgets import (
    build_ui,
    apply_theme,
    label_from_theme,
    theme_from_label,
    normalize_theme_name,
    THEMES,
)
from ui.link_utils import parse_supported_link
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeySequence


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

    def _apply_window_theme(self, theme_name: str):
        theme = THEMES.get(normalize_theme_name(theme_name), THEMES["dark"])
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {theme['window_bg']};
            }}
            QLabel {{
                color: {theme['text']};
            }}
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
                padding: 5px;
                border-radius: 3px;
            }}
            QComboBox {{
                background-color: {theme['input_bg']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
                padding: 4px 6px;
                border-radius: 3px;
            }}
            QCheckBox {{
                color: {theme['text']};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            """
        )
    
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
        
        # Build UI
        central_widget = build_ui(self)
        self.setCentralWidget(central_widget)
        self._apply_window_theme("dark")
        apply_theme(central_widget, "dark")

        def on_theme_changed(label: str):
            theme_name = theme_from_label(label)
            self._apply_window_theme(theme_name)
            apply_theme(central_widget, theme_name)

        if hasattr(central_widget, "theme_combo") and central_widget.theme_combo is not None:
            central_widget.theme_combo.currentTextChanged.connect(on_theme_changed)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        # Carregar estado salvo (checkboxes e link)
        try:
            from config import (
                load_ui_state,
                DEFAULT_THEME,
                PICAZOR_CHECK_THREADS_DEFAULT,
                PICAZOR_CHECK_BATCH_DEFAULT,
                PICAZOR_CHECK_DELAY_DEFAULT,
            )
            state = load_ui_state()
            if not isinstance(state, dict):
                state = {}

            theme_name = state.get("theme", DEFAULT_THEME)
            if hasattr(central_widget, "theme_combo") and central_widget.theme_combo is not None:
                central_widget.theme_combo.setCurrentText(label_from_theme(theme_name))
                on_theme_changed(central_widget.theme_combo.currentText())
            else:
                self._apply_window_theme(theme_name)
                apply_theme(central_widget, theme_name)
            
            # Restaurar checkboxes
            if hasattr(central_widget, 'checkboxes'):
                checkboxes_state = state.get('checkboxes', {})
                if isinstance(checkboxes_state, dict):
                    for key, cb in central_widget.checkboxes.items():
                        if key in checkboxes_state:
                            cb.setChecked(bool(checkboxes_state[key]))
            
            # Restaurar site/modelo
            last_site = state.get('last_site', '')
            last_model = state.get('last_model', '')
            if hasattr(central_widget, 'site_combo') and isinstance(last_site, str):
                if last_site in [central_widget.site_combo.itemText(i) for i in range(central_widget.site_combo.count())]:
                    central_widget.site_combo.setCurrentText(last_site)
            if hasattr(central_widget, 'model_input'):
                if isinstance(last_model, str) and last_model:
                    central_widget.model_input.setText(last_model)
                else:
                    last_link = state.get('last_link', '')
                    if isinstance(last_link, str) and last_link:
                        parsed = parse_supported_link(last_link)
                        if parsed:
                            site_label, model = parsed
                            if hasattr(central_widget, 'site_combo'):
                                central_widget.site_combo.setCurrentText(site_label)
                            central_widget.model_input.setText(model)
                        else:
                            central_widget.model_input.setText(last_link)
            
            # Restaurar settings do Picazor
            picazor_state = state.get('picazor_settings', {})
            if not isinstance(picazor_state, dict):
                picazor_state = {}

            # Restaurar ultima pasta escolhida (usada quando "Escolher pasta" estiver marcado)
            last_folder = state.get('last_chosen_folder')
            if isinstance(last_folder, str) and last_folder.strip():
                central_widget.last_chosen_folder = last_folder

            
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
        # Garantir que threads sejam finalizadas antes de fechar a janela
        try:
            central = self.centralWidget()
            if central is not None:
                fetch_worker = getattr(central, "fetch_worker", None)
                if fetch_worker and fetch_worker.isRunning():
                    fetch_worker.stop()
                    fetch_worker.wait(2000)

                download_worker = getattr(central, "download_worker", None)
                if download_worker and download_worker.isRunning():
                    download_worker.stop()
                    download_worker.wait(2000)

                thumbnail_workers = getattr(central, "_thumbnail_workers", [])
                for worker in list(thumbnail_workers):
                    if worker and worker.isRunning():
                        worker.wait(2000)
        except Exception as e:
            print(f"Erro ao encerrar threads: {e}")

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
                'last_site': getattr(central, 'site_combo', None).currentText() if hasattr(central, 'site_combo') else '',
                'last_model': getattr(central, 'model_input', None).text() if hasattr(central, 'model_input') else '',
                'picazor_settings': picazor_settings,
                'last_chosen_folder': getattr(central, 'last_chosen_folder', ''),
                'theme': theme_from_label(getattr(central, 'theme_combo', None).currentText()) if hasattr(central, 'theme_combo') else 'dark',
            }
            save_ui_state(state)
        except Exception as e:
            print(f"Erro ao salvar estado da UI: {e}")
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Paste) or (
                event.key() == Qt.Key_V and event.modifiers() & Qt.ControlModifier
            ):
                text = QApplication.clipboard().text()
                parsed = parse_supported_link(text)
                if parsed:
                    site_label, model = parsed
                    return self._confirm_paste_link(site_label, model)
        return super().eventFilter(obj, event)

    def _confirm_paste_link(self, site_label: str, model: str) -> bool:
        central = self.centralWidget()
        if not hasattr(central, 'site_combo') or not hasattr(central, 'model_input'):
            return False
        message = f"Detectei um link do {site_label}. Deseja preencher automaticamente?"
        result = QMessageBox.question(
            self,
            "Link detectado",
            message,
            QMessageBox.Yes | QMessageBox.No,
        )
        if result == QMessageBox.Yes:
            central.site_combo.setCurrentText(site_label)
            central.model_input.setText(model)
            return True
        return False
