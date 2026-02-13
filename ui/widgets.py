from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QCheckBox, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QProgressBar, QTextEdit, QFileDialog,
    QSpinBox, QDoubleSpinBox, QMessageBox, QGraphicsOpacityEffect,
    QAbstractSpinBox
)
from PySide6.QtCore import Qt, QTimer, QUrl, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QPixmap, QIcon, QDesktopServices, QColor, QPainter
from pathlib import Path
from datetime import datetime
import os
import html
import time
from ui.link_utils import SUPPORTED_SITES, build_url, normalize_site_model, parse_supported_link
from ui.workers import DownloadWorker, FetchWorker, ThumbnailWorker
from config import (
    APP_NAME_COLOR,
    PICAZOR_CHECK_BATCH_DEFAULT,
)

FIXED_PICAZOR_THREADS = 4
FIXED_PICAZOR_DELAY = 0.1


THEMES = {
    "dark": {
        "window_bg": "#1e1e1e",
        "panel_bg": "#1e1e1e",
        "widget_bg": "#2d2d2d",
        "widget_bg_alt": "#181818",
        "input_bg": "#2d2d2d",
        "text": "#ffffff",
        "text_muted": "#888888",
        "border": "#444444",
        "border_soft": "#333333",
        "accent": "#7b5cff",
        "accent_hover": "#8a6bff",
        "accent_pressed": "#6a4df0",
        "button_bg": "#2d2d2d",
        "button_hover": "#3d3d3d",
        "button_pressed": "#444444",
        "button_disabled_bg": "#1a1a1a",
        "button_disabled_text": "#666666",
        "progress_primary": "#7b5cff",
        "progress_secondary": "#a58bff",
        "pause_bg": "#6f4bff",
        "pause_hover": "#7d5aff",
        "pause_pressed": "#5f3cf0",
        "cancel_bg": "#5a2e8a",
        "cancel_hover": "#6a38a2",
        "cancel_pressed": "#4b2574",
        "status_ok": "#90EE90",
    },
    "light": {
        "window_bg": "#f2f2f2",
        "panel_bg": "#ffffff",
        "widget_bg": "#f6f6f6",
        "widget_bg_alt": "#ffffff",
        "input_bg": "#ffffff",
        "text": "#111111",
        "text_muted": "#666666",
        "border": "#cccccc",
        "border_soft": "#dddddd",
        "accent": "#6a49ff",
        "accent_hover": "#7a5bff",
        "accent_pressed": "#5839f0",
        "button_bg": "#f0f0f0",
        "button_hover": "#e6e6e6",
        "button_pressed": "#dcdcdc",
        "button_disabled_bg": "#efefef",
        "button_disabled_text": "#9a9a9a",
        "progress_primary": "#6a49ff",
        "progress_secondary": "#9b86ff",
        "pause_bg": "#6f4bff",
        "pause_hover": "#7d5aff",
        "pause_pressed": "#5f3cf0",
        "cancel_bg": "#6a34a5",
        "cancel_hover": "#7a3fbd",
        "cancel_pressed": "#582b8d",
        "status_ok": "#2e8b57",
    },
}

THEME_LABELS = {
    "Escuro": "dark",
    "Claro": "light",
}
THEME_LABELS_REVERSE = {
    "dark": "Escuro",
    "light": "Claro",
}


def normalize_theme_name(theme_name: str) -> str:
    value = (theme_name or "").strip().lower()
    if value in THEMES:
        return value
    return "dark"


def theme_from_label(label: str) -> str:
    return THEME_LABELS.get(label, "dark")


def label_from_theme(theme_name: str) -> str:
    return THEME_LABELS_REVERSE.get(normalize_theme_name(theme_name), "Escuro")


def apply_theme(central_widget, theme_name: str):
    theme = THEMES.get(normalize_theme_name(theme_name), THEMES["dark"])

    def _set(widget, style):
        if widget is not None:
            widget.setStyleSheet(style)

    label_style = f"color: {theme['text']}; font-size: 11px;"
    label_title_style = f"color: {theme['text']}; font-weight: bold;"
    muted_label_style = f"color: {theme['text_muted']}; font-size: 10px;"

    top_widget = getattr(central_widget, "top_widget", None)
    left_panel = getattr(central_widget, "left_panel", None)
    footer = getattr(central_widget, "footer", None)
    footer_label = getattr(central_widget, "footer_label", None)
    preview_label = getattr(central_widget, "preview_label", None)
    log_label = getattr(central_widget, "log_label", None)

    _set(
        top_widget,
        f"background-color: {theme['panel_bg']}; border-bottom: 1px solid {theme['border_soft']};",
    )
    _set(
        left_panel,
        f"background-color: {theme['panel_bg']}; border-right: 1px solid {theme['border_soft']};",
    )
    _set(
        footer,
        f"background-color: {theme['panel_bg']}; border-top: 1px solid {theme['border_soft']};",
    )
    _set(footer_label, muted_label_style)

    _set(getattr(central_widget, "site_label", None), label_title_style)
    _set(getattr(central_widget, "model_label", None), label_title_style)
    _set(getattr(central_widget, "theme_label", None), label_title_style)
    _set(preview_label, f"color: {theme['text']}; font-size: 12px;")
    _set(log_label, label_style)

    input_style = (
        f"QLineEdit {{ background-color: {theme['input_bg']}; color: {theme['text']}; "
        f"border: 1px solid {theme['border']}; padding: 5px; border-radius: 3px; }}"
    )
    combo_style = (
        f"QComboBox {{ background-color: {theme['input_bg']}; color: {theme['text']}; "
        f"border: 1px solid {theme['border']}; padding: 4px 6px; border-radius: 3px; }}"
    )

    _set(getattr(central_widget, "model_input", None), input_style)
    _set(getattr(central_widget, "site_combo", None), combo_style)
    _set(getattr(central_widget, "theme_combo", None), combo_style)

    button_style = (
        "QPushButton {"
        f"background-color: {theme['button_bg']}; color: {theme['text']}; "
        f"border: 1px solid {theme['border']}; border-radius: 3px; font-weight: bold;"
        "}"
        "QPushButton:hover:!disabled {"
        f"background-color: {theme['button_hover']};"
        "}"
        "QPushButton:pressed {"
        f"background-color: {theme['button_pressed']};"
        "}"
        "QPushButton:disabled {"
        f"color: {theme['button_disabled_text']}; background-color: {theme['button_disabled_bg']}; "
        f"border: 1px solid {theme['border_soft']};"
        "}"
    )
    accent_button_style = (
        "QPushButton {"
        f"background-color: {theme['accent']}; color: #000000; "
        "border: none; border-radius: 3px; font-weight: bold;"
        "}"
        "QPushButton:hover:!disabled {"
        f"background-color: {theme['accent_hover']};"
        "}"
        "QPushButton:pressed {"
        f"background-color: {theme['accent_pressed']};"
        "}"
        "QPushButton:disabled {"
        f"background-color: {theme['button_disabled_bg']}; color: {theme['button_disabled_text']};"
        "}"
    )
    pause_button_style = (
        "QPushButton {"
        f"background-color: {theme['pause_bg']}; color: #ffffff; "
        "border: none; border-radius: 3px; font-weight: bold;"
        "}"
        "QPushButton:hover:!disabled {"
        f"background-color: {theme['pause_hover']};"
        "}"
        "QPushButton:pressed {"
        f"background-color: {theme['pause_pressed']};"
        "}"
        "QPushButton:disabled {"
        f"background-color: {theme['button_disabled_bg']}; color: {theme['button_disabled_text']};"
        "}"
    )
    cancel_button_style = (
        "QPushButton {"
        f"background-color: {theme['cancel_bg']}; color: #ffffff; "
        "border: none; border-radius: 3px; font-weight: bold;"
        "}"
        "QPushButton:hover:!disabled {"
        f"background-color: {theme['cancel_hover']};"
        "}"
        "QPushButton:pressed {"
        f"background-color: {theme['cancel_pressed']};"
        "}"
        "QPushButton:disabled {"
        f"background-color: {theme['button_disabled_bg']}; color: {theme['button_disabled_text']};"
        "}"
    )

    _set(getattr(central_widget, "checar_btn", None), button_style)
    _set(getattr(central_widget, "download_btn", None), accent_button_style)
    _set(getattr(central_widget, "pause_btn", None), pause_button_style)
    _set(getattr(central_widget, "cancel_btn", None), cancel_button_style)

    checkbox_style = (
        "QCheckBox {"
        f"color: {theme['text']}; font-size: 11px;"
        "}"
        "QCheckBox::indicator {"
        "width: 16px; height: 16px;"
        "}"
    )
    for cb in getattr(central_widget, "checkboxes", {}).values():
        _set(cb, checkbox_style)

    spin_style = (
        "QSpinBox, QDoubleSpinBox {"
        f"background-color: {theme['input_bg']}; color: {theme['text']}; "
        f"border: 1px solid {theme['border']}; padding: 2px 4px; border-radius: 3px;"
        "}"
    )
    _set(getattr(central_widget, "picazor_threads_input", None), spin_style)
    _set(getattr(central_widget, "picazor_batch_input", None), spin_style)
    _set(getattr(central_widget, "picazor_delay_input", None), spin_style)

    for label in getattr(central_widget, "labels", {}).values():
        _set(label, label_style)

    status_label = None
    if isinstance(getattr(central_widget, "labels", None), dict):
        status_label = central_widget.labels.get("status")
    if status_label is not None:
        _set(status_label, f"color: {theme['status_ok']}; font-size: 11px;")

    _set(getattr(left_panel, "picazor_title", None), label_style)
    _set(getattr(left_panel, "threads_label", None), label_style)
    _set(getattr(left_panel, "batch_label", None), label_style)
    _set(getattr(left_panel, "delay_label", None), label_style)

    separator = getattr(left_panel, "separator", None)
    _set(separator, f"background-color: {theme['border']};")

    progress_bar = getattr(central_widget, "progress_bar", None)
    _set(
        progress_bar,
        "QProgressBar {"
        f"background-color: {theme['widget_bg']}; border: 1px solid {theme['border']}; "
        "border-radius: 3px; height: 20px;"
        "}"
        "QProgressBar::chunk {"
        f"background-color: {theme['progress_primary']};"
        "}",
    )
    file_progress_bar = getattr(central_widget, "file_progress_bar", None)
    _set(
        file_progress_bar,
        "QProgressBar {"
        f"background-color: {theme['widget_bg']}; border: 1px solid {theme['border']}; "
        "border-radius: 3px; height: 16px;"
        "}"
        "QProgressBar::chunk {"
        f"background-color: {theme['progress_secondary']};"
        "}",
    )

    log_widget = getattr(central_widget, "log_widget", None)
    _set(
        log_widget,
        "QTextEdit {"
        f"background-color: {theme['widget_bg']}; color: {theme['text']}; "
        f"border: 1px solid {theme['border']}; border-radius: 3px; "
        "font-family: 'Courier New', monospace; font-size: 10px;"
        "}"
        "QScrollBar:vertical {"
        f"background-color: {theme['widget_bg']}; width: 8px; border: none;"
        "}"
        "QScrollBar::handle:vertical {"
        f"background-color: {theme['border']}; border-radius: 4px;"
        "}"
        "QScrollBar::handle:vertical:hover {"
        f"background-color: {theme['border_soft']};"
        "}",
    )

    thumbnails_container = getattr(central_widget, "thumbnails_container", None)
    _set(
        thumbnails_container,
        f"background-color: {theme['widget_bg_alt']}; border: 1px solid {theme['border']}; "
        "border-radius: 3px; QListWidget::item { margin: 0; padding: 0; }",
    )





def build_ui(parent):
    """Build and configure the UI elements for the application window."""
    
    # Central widget
    central_widget = QWidget()
    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    
    # Top section with link input and buttons
    top_section, site_combo, model_input, site_label, model_label = create_top_section(central_widget)
    main_layout.addWidget(top_section)
    
    # Painel central dividido: esquerda (opções/status/log) e direita (preview)
    center_panel = QWidget()
    center_layout = QHBoxLayout(center_panel)
    center_layout.setContentsMargins(8, 0, 8, 8)
    center_layout.setSpacing(12)

    # Esquerda: painel de opções/status/log
    left_panel, labels_dict, checkboxes_dict = create_left_panel()
    left_panel.setMinimumWidth(260)
    left_panel.setMaximumWidth(340)
    # Log e progresso ficam juntos em um layout vertical
    left_vbox = QVBoxLayout()
    left_vbox.setContentsMargins(0, 0, 0, 0)
    left_vbox.setSpacing(8)
    left_vbox.addWidget(left_panel)

    # Barra de progresso
    progress_bar = QProgressBar()
    progress_bar.setStyleSheet("""
        QProgressBar {
            background-color: #2d2d2d;
            border: 1px solid #444;
            border-radius: 3px;
            height: 20px;
        }
        QProgressBar::chunk {
            background-color: #ffbf00;
        }
    """)
    progress_bar.setValue(0)
    progress_bar.setMinimumHeight(20)
    progress_bar.setTextVisible(True)
    progress_bar.setFormat("%p%")
    progress_bar.setVisible(False)
    file_progress_bar = QProgressBar()
    file_progress_bar.setStyleSheet("""
        QProgressBar {
            background-color: #2d2d2d;
            border: 1px solid #444;
            border-radius: 3px;
            height: 16px;
        }
        QProgressBar::chunk {
            background-color: #3fa9f5;
        }
    """)
    file_progress_bar.setRange(0, 100)
    file_progress_bar.setValue(0)
    file_progress_bar.setTextVisible(True)
    file_progress_bar.setFormat("%p%")
    file_progress_bar.setMinimumHeight(16)
    file_progress_bar.setVisible(False)
    left_vbox.addWidget(progress_bar)
    left_vbox.addWidget(file_progress_bar)

    # Log de atividades
    log_label = QLabel("log de atividades:")
    log_label.setStyleSheet("color: #ffffff; font-size: 11px;")
    log_widget = QTextEdit()
    log_widget.setReadOnly(True)
    log_widget.setStyleSheet("""
        QTextEdit {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 10px;
        }
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 8px;
            border: none;
        }
        QScrollBar::handle:vertical {
            background-color: #444;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #555;
        }
    """)
    log_widget.setMinimumHeight(150)
    log_widget._log_buffer = []
    log_widget._log_timer = QTimer(log_widget)
    log_widget._log_timer.setSingleShot(True)
    log_widget._log_timer.setInterval(120)
    def _flush_log_buffer():
        buffer = log_widget._log_buffer
        if not buffer:
            return
        log_widget.append("<br>".join(buffer))
        log_widget._log_buffer = []
        scrollbar = log_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    log_widget._flush_log_buffer = _flush_log_buffer
    log_widget._log_timer.timeout.connect(_flush_log_buffer)
    left_vbox.addWidget(log_label)
    left_vbox.addWidget(log_widget, 1)

    left_container = QWidget()
    left_container.setLayout(left_vbox)
    center_layout.addWidget(left_container, 1)

    # Direita: painel de preview (thumbnails)
    preview_container = QWidget()
    preview_layout = QVBoxLayout(preview_container)
    preview_layout.setContentsMargins(0, 0, 0, 0)
    preview_layout.setSpacing(4)
    preview_label = QLabel("preview de download")
    preview_label.setStyleSheet("color: #ffffff; font-size: 12px;")
    preview_layout.addWidget(preview_label)
    thumbnails_container = QListWidget()
    thumbnails_container.setViewMode(QListWidget.IconMode)
    thumbnails_container.setResizeMode(QListWidget.Adjust)
    thumbnails_container.setMovement(QListWidget.Static)
    thumbnails_container.setSpacing(10)
    thumb_size = 220  # Aumenta tamanho
    thumbnails_container.setIconSize(QSize(thumb_size, thumb_size))
    thumbnails_container.setGridSize(QSize(thumb_size, thumb_size))
    thumbnails_container.setStyleSheet("background-color: #181818; border: 1px solid #444; border-radius: 3px; QListWidget::item { margin: 0; padding: 0; }")
    thumbnails_container.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    def set_fixed_thumb_grid():
        try:
            width = thumbnails_container.width() - thumbnails_container.frameWidth() * 2
        except RuntimeError:
            return
        cols = 4
        spacing = thumbnails_container.spacing()
        thumb_size = int((width - (cols - 1) * spacing) / cols)
        thumbnails_container.setIconSize(QSize(thumb_size, thumb_size))
        thumbnails_container.setGridSize(QSize(thumb_size, thumb_size))
    QTimer.singleShot(100, set_fixed_thumb_grid)
    preview_layout.addWidget(thumbnails_container, 1)
    center_layout.addWidget(preview_container, 3)

    main_layout.addWidget(center_panel, 1)

    # Footer
    footer = QFrame()
    footer.setStyleSheet("background-color: #1e1e1e; border-top: 1px solid #333;")
    footer_layout = QHBoxLayout(footer)
    footer_layout.setContentsMargins(10, 6, 10, 6)
    footer_layout.setSpacing(6)
    year = datetime.now().year
    footer_label = QLabel(
        f"Copyright {year} <a href='https://github.com/Heyfelphs'>Heyfelphs</a> (GitHub)"
    )
    footer_label.setStyleSheet("color: #888888; font-size: 10px;")
    footer_label.setOpenExternalLinks(True)
    footer_label.setAlignment(Qt.AlignCenter)
    footer_layout.addWidget(footer_label, 1)
    theme_container = QWidget()
    theme_layout = QHBoxLayout(theme_container)
    theme_layout.setContentsMargins(0, 0, 0, 0)
    theme_layout.setSpacing(6)
    theme_label = QLabel("Tema:")
    theme_label.setStyleSheet("color: #ffffff; font-size: 10px;")
    theme_combo = QComboBox()
    theme_combo.addItems(["Escuro", "Claro"])
    theme_combo.setMinimumHeight(22)
    theme_combo.setMaximumHeight(22)
    theme_combo.setMinimumWidth(80)
    theme_combo.setMaximumWidth(90)
    theme_layout.addWidget(theme_label)
    theme_layout.addWidget(theme_combo)
    footer_layout.addWidget(theme_container, 0, Qt.AlignRight)
    main_layout.addWidget(footer)

    # Store references for later access
    central_widget.site_combo = site_combo
    central_widget.model_input = model_input
    central_widget.theme_combo = theme_combo
    central_widget.site_label = site_label
    central_widget.model_label = model_label
    central_widget.theme_label = theme_label
    central_widget.top_widget = top_section
    central_widget.log_label = log_label
    central_widget.preview_label = preview_label
    central_widget.footer = footer
    central_widget.footer_label = footer_label
    central_widget.left_panel = left_panel
    central_widget.labels = labels_dict
    central_widget.checkboxes = checkboxes_dict
    central_widget.progress_bar = progress_bar
    central_widget.file_progress_bar = file_progress_bar
    central_widget.log_widget = log_widget
    central_widget.thumbnails_container = thumbnails_container
    central_widget.thumb_list = thumbnails_container
    if hasattr(left_panel, "picazor_threads_input"):
        central_widget.picazor_threads_input = left_panel.picazor_threads_input
    if hasattr(left_panel, "picazor_batch_input"):
        central_widget.picazor_batch_input = left_panel.picazor_batch_input
    if hasattr(left_panel, "picazor_delay_input"):
        central_widget.picazor_delay_input = left_panel.picazor_delay_input
    if hasattr(left_panel, "picazor_container"):
        central_widget.picazor_container = left_panel.picazor_container

    # Conectar mudança de site para mostrar/esconder controles Picazor
    def on_site_changed(index):
        if hasattr(central_widget, "picazor_container"):
            is_picazor = site_combo.currentText() == "Picazor"
            central_widget.picazor_container.setVisible(is_picazor)

    site_combo.currentIndexChanged.connect(on_site_changed)
    # default number of columns for thumbnails grid (fixo em 4)
    central_widget.thumbnails_columns = 4
    # limit how many thumbnails are kept in the grid
    central_widget.thumbnails_limit = 12
    # Default download root
    appdata_dir = os.getenv("APPDATA")
    if appdata_dir:
        default_root = Path(appdata_dir) / "Hey_Felphs Archive-Downloader"
    else:
        default_root = Path.home() / "Hey_Felphs Archive-Downloader"
    default_root.mkdir(parents=True, exist_ok=True)
    central_widget.download_root = default_root
    if "destino" in labels_dict:
        labels_dict["destino"].setVisible(False)

    def update_destino_label():
        if "destino" not in labels_dict:
            return
        choose_folder_cb = central_widget.checkboxes.get("escolher_pasta")
        if choose_folder_cb is not None and choose_folder_cb.isChecked():
            base_dir = getattr(central_widget, "download_root", Path("catalog") / "models")
            labels_dict["destino"].setText(f"Destino: {base_dir}")
            labels_dict["destino"].setVisible(True)
        else:
            labels_dict["destino"].setVisible(False)
        labels_dict["destino"].setVisible(True)

    central_widget._update_destino_label = update_destino_label
    choose_folder_cb = central_widget.checkboxes.get("escolher_pasta")
    if choose_folder_cb is not None:
        choose_folder_cb.stateChanged.connect(lambda _: update_destino_label())
    update_destino_label()
    apply_theme(central_widget, "dark")
    return central_widget


def create_top_section(parent):
    """Create the top section with link input and buttons."""
    top_widget = QFrame()
    top_widget.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #333;")
    layout = QHBoxLayout(top_widget)
    layout.setContentsMargins(15, 10, 15, 10)
    layout.setSpacing(10)
    
    # Site label and dropdown
    site_label = QLabel("Site:")
    site_label.setStyleSheet("color: #ffffff; font-weight: bold;")
    layout.addWidget(site_label)

    site_combo = QComboBox()
    site_combo.addItems(list(SUPPORTED_SITES.keys()))
    site_combo.setMinimumHeight(32)
    site_combo.setMinimumWidth(120)
    layout.addWidget(site_combo)

    # Model label and input
    model_label = QLabel("Modelo:")
    model_label.setStyleSheet("color: #ffffff; font-weight: bold;")
    layout.addWidget(model_label)

    model_input = QLineEdit()
    model_input.setPlaceholderText("coco20002 ou link completo")
    model_input.setStyleSheet("""
        QLineEdit {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444;
            padding: 5px;
            border-radius: 3px;
        }
    """)
    model_input.setMinimumHeight(32)
    layout.addWidget(model_input, 1)

    
    # Checar button - starts disabled
    checar_btn = QPushButton("Checar")
    checar_btn.setMinimumWidth(80)
    checar_btn.setMinimumHeight(32)
    checar_btn.setEnabled(False)
    checar_btn.setStyleSheet("""
        QPushButton {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 3px;
            font-weight: bold;
        }
        QPushButton:hover:!disabled {
            background-color: #3d3d3d;
        }
        QPushButton:pressed {
            background-color: #444;
        }
        QPushButton:disabled {
            color: #666;
            background-color: #1a1a1a;
            border: 1px solid #333;
        }
    """)
    checar_btn.parent_widget = parent
    checar_btn.model_input = model_input
    layout.addWidget(checar_btn)
    
    # Download button - starts disabled and hidden
    download_btn = QPushButton("DOWNLOAD")
    download_btn.setMinimumWidth(100)
    download_btn.setMinimumHeight(32)
    download_btn.setEnabled(False)
    download_btn.setVisible(True)
    download_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {APP_NAME_COLOR};
            color: #000000;
            border: none;
            border-radius: 3px;
            font-weight: bold;
        }}
        QPushButton:hover:!disabled {{
            background-color: #ffc933;
        }}
        QPushButton:pressed {{
            background-color: #e6a800;
        }}
        QPushButton:disabled {{
            background-color: #999;
            color: #666;
        }}
    """)
    layout.addWidget(download_btn)

    # Pausar/Retomar button
    pause_btn = QPushButton("Pausar")
    pause_btn.setMinimumWidth(90)
    pause_btn.setMinimumHeight(32)
    pause_btn.setEnabled(False)
    pause_btn.setVisible(False)
    pause_btn.setStyleSheet("""
        QPushButton {
            background-color: #ff6b35;
            color: #ffffff;
            border: none;
            border-radius: 3px;
            font-weight: bold;
        }
        QPushButton:hover:!disabled {
            background-color: #ff8555;
        }
        QPushButton:pressed {
            background-color: #e64820;
        }
        QPushButton:disabled {
            background-color: #999;
            color: #666;
        }
    """)
    layout.addWidget(pause_btn)
    parent.pause_btn = pause_btn

    # Cancelar button (mostrado apenas quando pausado)
    cancel_btn = QPushButton("Cancelar")
    cancel_btn.setMinimumWidth(90)
    cancel_btn.setMinimumHeight(32)
    cancel_btn.setEnabled(False)
    cancel_btn.setVisible(False)
    cancel_btn.setStyleSheet("""
        QPushButton {
            background-color: #7a1f1f;
            color: #ffffff;
            border: none;
            border-radius: 3px;
            font-weight: bold;
        }
        QPushButton:hover:!disabled {
            background-color: #8f2a2a;
        }
        QPushButton:pressed {
            background-color: #5c1717;
        }
        QPushButton:disabled {
            background-color: #999;
            color: #666;
        }
    """)
    layout.addWidget(cancel_btn)
    parent.cancel_btn = cancel_btn
    
    # Store buttons in parent for external access
    parent.checar_btn = checar_btn
    parent.download_btn = download_btn
    
    # Connect link input to enable/disable checar button
    def on_link_changed():
        has_text = len(model_input.text().strip()) > 0
        checar_btn.setEnabled(has_text)
        # Reset download button when link changes
        if has_text:
            download_btn.setVisible(True)
            download_btn.setEnabled(False)
        # Manter label destino visivel com base no modo atual
        if hasattr(parent, "_update_destino_label"):
            parent._update_destino_label()
        # Esconder barra de progresso quando novo link é inserido
        if hasattr(parent, "progress_bar"):
            parent.progress_bar.setVisible(False)
        if hasattr(parent, "file_progress_bar"):
            parent.file_progress_bar.setVisible(False)
        if hasattr(parent, "pause_btn"):
            parent.pause_btn.setVisible(False)
            parent.pause_btn.setEnabled(False)
            parent.pause_btn.setText("Pausar")
        parent._download_complete_called = False
    
    model_input.textChanged.connect(on_link_changed)
    
    # Connect checar button to fetch function
    def on_checar_clicked():
        site_label, model_name = normalize_site_model(site_combo, model_input)
        url = build_url(site_label, model_name)
        # Limpa painel de log e thumbnails ao clicar em checar
        if hasattr(parent, "log_widget"):
            parent.log_widget.clear()
        if hasattr(parent, "thumbnails_container"):
            parent.thumbnails_container.clear()

        if not url:
            parent.labels["status"].setText("Status: URL vazia!")
            QMessageBox.warning(parent, "URL inválida", "Por favor, insira um URL válido ou um nome de modelo.")
            model_input.setFocus()
            checar_btn.setEnabled(True)
            return

        if hasattr(parent, "pause_btn"):
            parent.pause_btn.setVisible(True)
            parent.pause_btn.setEnabled(True)
            parent.pause_btn.setText("Cancelar")
        
        # Log message
        add_log_message(parent.log_widget, f"🔍 Buscando informações da URL: {url}")

        # Disable checar button during fetch
        checar_btn.setEnabled(False)
        parent.labels["status"].setText("Status: Buscando...")

        picazor_threads_input = getattr(parent, "picazor_threads_input", None)
        picazor_batch_input = getattr(parent, "picazor_batch_input", None)
        picazor_delay_input = getattr(parent, "picazor_delay_input", None)

        picazor_threads = FIXED_PICAZOR_THREADS
        picazor_batch = picazor_batch_input.value() if picazor_batch_input else PICAZOR_CHECK_BATCH_DEFAULT
        picazor_delay = FIXED_PICAZOR_DELAY

        # Create worker thread
        worker = FetchWorker(url, picazor_threads, picazor_batch, picazor_delay)
        worker.progress.connect(lambda count: on_fetch_progress(parent, count))
        worker.finished.connect(lambda data: on_fetch_complete(parent, data, checar_btn, download_btn))
        worker.error.connect(lambda err: on_fetch_error(parent, err, checar_btn))
        # (Removido: label de arquivos)
        worker.start()
        parent.fetch_worker = worker  # Store reference to prevent garbage collection
    
    checar_btn.clicked.connect(on_checar_clicked)
    
    # Connect download button to download function
    def on_download_clicked():
        parent._download_started = True
        site_label, model_name = normalize_site_model(site_combo, model_input)
        url = build_url(site_label, model_name)
        if not url:
            parent.labels["status"].setText("Status: URL vazia!")
            return


        # Get checkbox states
        download_images = parent.checkboxes["imagens"].isChecked()
        download_videos = parent.checkboxes["videos"].isChecked()

        if not download_images and not download_videos:
            parent.labels["status"].setText("Status: Selecione imagens ou vídeos!")
            return

        # Define a pasta de destino (perguntar opcionalmente)
        pictures_dir = Path(os.path.expanduser(r"~")) / "Pictures"
        if not pictures_dir.exists():
            pictures_dir = Path.home()
        base_dir = getattr(parent, "download_root", pictures_dir)
        parts = [p for p in url.split("/") if p]
        model_name = parts[-1] if parts else ""
        suggested_dir = base_dir / site_label
        if model_name:
            suggested_dir = suggested_dir / model_name

        choose_folder = parent.checkboxes.get("escolher_pasta")
        if choose_folder is not None and choose_folder.isChecked():
            last_chosen = getattr(parent, "last_chosen_folder", "")
            if last_chosen and Path(last_chosen).exists():
                suggested_dir = Path(last_chosen)
            folder = QFileDialog.getExistingDirectory(
                parent,
                "Escolha a pasta para salvar o download",
                str(suggested_dir),
            )
            if not folder:
                parent.labels["status"].setText("Status: Download cancelado pelo usuário.")
                checar_btn.setEnabled(True)
                download_btn.setEnabled(True)
                return
            base_dir = Path(folder)
            parent.last_chosen_folder = str(base_dir)
            if hasattr(parent, "labels") and "destino" in parent.labels:
                parent.labels["destino"].setText(f"Destino: {base_dir}")
                parent.labels["destino"].setVisible(True)

        # Cria subpasta com nome da modelo
        parts = [p for p in url.split("/") if p]
        model_name = parts[-1] if parts else "modelo"
        target_dir = base_dir / site_label / model_name
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            test_file = target_dir / "__fapello_test_perm.txt"
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink()
        except Exception as e:
            QMessageBox.critical(parent, "Permissão negada", f"Não foi possível salvar arquivos na pasta selecionada.\n\nErro: {e}\n\nEscolha uma pasta diferente.")
            parent.labels["status"].setText("Status: Sem permissão na pasta escolhida.")
            checar_btn.setEnabled(True)
            download_btn.setEnabled(True)
            return
        target_dir = target_dir.resolve()
        parent.current_download_dir = target_dir
        parent.last_download_dir = target_dir
        if hasattr(parent, "labels") and "destino" in parent.labels:
            parent.labels["destino"].setText(f"Destino: {target_dir}")
            parent.labels["destino"].setVisible(True)
        add_log_message(parent.log_widget, f"Destino escolhido: {target_dir}")
        
        # Get total files from label
        total_text = parent.labels["total"].text()
        try:
            total_files = int(total_text.split(": ")[1])
        except:
            total_files = 0
        
        # Check if this is Picazor (total is number of indices/pages, not real files)
        url = build_url(site_combo.currentText(), model_input.text().strip())
        is_picazor = "picazor.com" in url
        
        # For Picazor, total_files is indices/pages; real file count is unknown until download starts
        if is_picazor:
            total_files_for_progress = None  # Mark as unknown
        else:
            total_files_for_progress = total_files
        
        # Log message
        
        # Mostrar barra de progresso durante download
        if hasattr(parent, "progress_bar"):
            parent.progress_bar.setVisible(True)
        if hasattr(parent, "file_progress_bar"):
            parent.file_progress_bar.setVisible(True)
        if hasattr(parent, "pause_btn"):
            parent.pause_btn.setVisible(True)
            parent.pause_btn.setEnabled(True)
            parent.pause_btn.setText("Pausar")
        if hasattr(parent, "cancel_btn"):
            parent.cancel_btn.setVisible(False)
            parent.cancel_btn.setEnabled(False)
        download_types = []
        if download_images:
            download_types.append("imagens")
        if download_videos:
            download_types.append("vídeos")
        
        if is_picazor:
            add_log_message(parent.log_widget, f"⬇️  Iniciando download de {', '.join(download_types)} ({total_files} índice(s))")
        else:
            add_log_message(parent.log_widget, f"⬇️  Iniciando download de {', '.join(download_types)} ({total_files} arquivo(s))")
        add_log_message(parent.log_widget, f"Destino: {target_dir}")
        
        # Limpar thumbnails anteriores
        parent.thumbnails_container.clear()
        
        # Hide download button during download
        download_btn.setEnabled(False)
        download_btn.setVisible(False)
        checar_btn.setEnabled(False)
        if hasattr(parent, "cancel_btn"):
            parent.cancel_btn.setVisible(False)
            parent.cancel_btn.setEnabled(False)
        parent._download_complete_called = False
        parent.labels["status"].setText("Status: Baixando...")
        parent._download_canceled = False
        
        # Reset progress bar com total esperado
        if is_picazor:
            # Para Picazor, o total real de arquivos é desconhecido no início
            # Use um placeholder máximo que será atualizado quando o summary chegar
            parent.progress_bar.setMaximum(1000)
            parent.progress_bar.setValue(0)
            parent.progress_bar.setRange(0, 0)
            parent._picazor_real_total_unknown = True
        else:
            # Para outros sites, total_files é o número real de arquivos
            total_for_progress = total_files_for_progress if total_files_for_progress and total_files_for_progress > 0 else 100
            parent.progress_bar.setRange(0, total_for_progress)
            parent.progress_bar.setValue(0)
            parent._picazor_real_total_unknown = False
        
        # Reset failed files list for manual analysis
        parent.failed_files_for_analysis = []
        # Recupera a lista de índices válidos do FetchWorker (se Picazor)
        valid_indices = None
        if hasattr(parent, "fetch_worker") and hasattr(parent.fetch_worker, "valid_indices"):
            valid_indices = parent.fetch_worker.valid_indices
        picazor_threads_input = getattr(parent, "picazor_threads_input", None)
        picazor_batch_input = getattr(parent, "picazor_batch_input", None)
        picazor_delay_input = getattr(parent, "picazor_delay_input", None)

        picazor_threads = FIXED_PICAZOR_THREADS
        picazor_batch = picazor_batch_input.value() if picazor_batch_input else PICAZOR_CHECK_BATCH_DEFAULT
        picazor_delay = FIXED_PICAZOR_DELAY

        # Create download worker thread
        # For Picazor, pass total_files (indices count) even though real file count is unknown
        download_worker = DownloadWorker(
            url,
            download_images,
            download_videos,
            total_files,
            target_dir,
            valid_indices=valid_indices,
            picazor_threads=picazor_threads,
            picazor_batch=picazor_batch,
            picazor_delay=picazor_delay,
        )
        download_worker.progress_update.connect(lambda data: on_download_progress_update(parent, data))
        download_worker.finished.connect(lambda: on_download_complete(parent, checar_btn, download_btn))
        download_worker.error.connect(lambda err: on_download_error(parent, err, checar_btn, download_btn))
        download_worker.start()
        parent.download_worker = download_worker  # Store reference
    
    download_btn.clicked.connect(on_download_clicked)

    def on_choose_folder_clicked():
        base_dir = getattr(parent, "download_root", Path("catalog") / "models")
        folder = QFileDialog.getExistingDirectory(parent, "Escolher pasta de download", str(base_dir))
        if folder:
            parent.download_root = Path(folder)
            if hasattr(parent, "labels") and "destino" in parent.labels:
                site_label = parent.site_combo.currentText() if hasattr(parent, "site_combo") else ""
                model_text = parent.model_input.text().strip() if hasattr(parent, "model_input") else ""
                if site_label and model_text:
                    destino = Path(folder) / site_label / model_text
                elif site_label:
                    destino = Path(folder) / site_label
                else:
                    destino = Path(folder)
                parent.labels["destino"].setText(f"Destino: {destino}")
            add_log_message(parent.log_widget, f"Pasta de download selecionada: {folder}")

    # (Removido: botão de escolher pasta)

    # Connect pause button to pause/resume function
    def on_pause_clicked():
        download_worker = getattr(parent, "download_worker", None)
        fetch_worker = getattr(parent, "fetch_worker", None)
        
        # Handle pause/resume for download only
        if download_worker and pause_btn.text() in ("Pausar", "Retomar"):
            if pause_btn.text() == "Pausar":
                download_worker.pause()
                pause_btn.setText("Retomar")
                add_log_message(parent.log_widget, "Download pausado.", warning=True)
                if hasattr(parent, "cancel_btn"):
                    parent.cancel_btn.setVisible(True)
                    parent.cancel_btn.setEnabled(True)
            elif pause_btn.text() == "Retomar":
                download_worker.resume()
                pause_btn.setText("Pausar")
                add_log_message(parent.log_widget, "Download retomado.")
                if hasattr(parent, "cancel_btn"):
                    parent.cancel_btn.setVisible(False)
                    parent.cancel_btn.setEnabled(False)
        # Handle stop for fetch (no pause/resume support for fetch)
        elif fetch_worker and pause_btn.text() == "Cancelar":
            fetch_worker.stop()
            pause_btn.setText("Pausar")
            add_log_message(parent.log_widget, "Análise cancelada.", warning=True)
    
    pause_btn.clicked.connect(on_pause_clicked)

    def on_cancel_clicked():
        download_worker = getattr(parent, "download_worker", None)
        if download_worker:
            parent._download_canceled = True
            download_worker.stop()
            parent.labels["status"].setText("Status: Cancelado")
            add_log_message(parent.log_widget, "Download cancelado.", warning=True)
        if hasattr(parent, "cancel_btn"):
            parent.cancel_btn.setVisible(False)
            parent.cancel_btn.setEnabled(False)
        if hasattr(parent, "pause_btn"):
            parent.pause_btn.setVisible(False)
            parent.pause_btn.setEnabled(False)

    cancel_btn.clicked.connect(on_cancel_clicked)
    
    return top_widget, site_combo, model_input, site_label, model_label


def on_fetch_complete(parent, data, checar_btn, download_btn):
    """Handle successful fetch."""

    parent.labels["total"].setText(f"Total: {data['total']}")
    parent.labels["pasta"].setText(f"Pasta: {data['pasta']}")
    parent.labels["status"].setText("Status: Pronto")
    
    # Atualiza label arquivos para Picazor
    url = ""
    if hasattr(parent, 'site_combo') and hasattr(parent, 'model_input'):
        url = build_url(parent.site_combo.currentText(), parent.model_input.text().strip())
    if "picazor.com" in url:
        # Para Picazor, data['total'] é o número de índices/páginas, não de arquivos reais
        # O total real será recebido no 'summary' durante o download
        # (Removido: label de arquivos)
        # Define barra indeterminada; será atualizada quando o summary chegar
        parent.progress_bar.setRange(0, 0)
        # Marca que o total real é desconhecido para Picazor
        parent._picazor_real_total_unknown = True
    else:
        # Para Fapello, data['total'] é o número real de arquivos
        # (Removido: label de arquivos)
        total = data.get('total', 0)
        total = total if total > 0 else 100
        parent.progress_bar.setRange(0, total)
        parent.progress_bar.setValue(0)
        parent._picazor_real_total_unknown = False

    if data['total'] == 0:
        QMessageBox.warning(parent, "Link inválido ou não validado", "O link informado não é válido ou não pôde ser validado. Por favor, insira um link válido.")
        checar_btn.setEnabled(True)
        return

    # Log message
    add_log_message(parent.log_widget, f"✓ Busca concluída: {data['total']} item(ns) processado(s)")
    add_log_message(parent.log_widget, f"Pasta definida: {data['pasta']}")
    base_dir = getattr(parent, "download_root", Path("catalog") / "models")
    add_log_message(parent.log_widget, f"Destino: {base_dir}")

    # Enable download button and show it
    download_btn.setVisible(True)
    download_btn.setEnabled(True)

    # Perguntar se deseja iniciar o download imediatamente
    reply = QMessageBox.question(
        parent,
        "Iniciar download",
        "Checagem concluida. Deseja iniciar o download agora?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    if reply == QMessageBox.Yes:
        download_btn.click()
    # Keep checar button disabled until link changes
    
    # Ocultar botão de pausa ao terminar a análise
    if hasattr(parent, "pause_btn") and not getattr(parent, "_download_started", False):
        parent.pause_btn.setVisible(False)
        parent.pause_btn.setEnabled(False)
    if hasattr(parent, "cancel_btn") and not getattr(parent, "_download_started", False):
        parent.cancel_btn.setVisible(False)
        parent.cancel_btn.setEnabled(False)
    if hasattr(parent, "cancel_btn"):
        parent.cancel_btn.setVisible(False)
        parent.cancel_btn.setEnabled(False)


def on_fetch_progress(parent, count: int):
    if not hasattr(parent, "labels") or "total" not in parent.labels:
        return
    parent.labels["total"].setText(f"Total: {count}")


def on_fetch_error(parent, error, checar_btn):
    """Handle fetch error and re-enable checar button."""
    parent.labels["status"].setText(f"Status: Erro")
    
    # Log message
    add_log_message(parent.log_widget, f"✗ Erro na busca: {error}", error=True)
    
    # Re-enable checar button to allow retry
    checar_btn.setEnabled(True)
    
    # Ocultar botão de pausa ao falhar a análise
    if hasattr(parent, "pause_btn"):
        parent.pause_btn.setVisible(False)
        parent.pause_btn.setEnabled(False)


def on_download_progress_update(parent, data):
    """Handle detailed download progress updates."""
    def _throttled_update(key: str, interval_ms: int = 100) -> bool:
        now = time.monotonic()
        last = getattr(parent, key, 0.0)
        if (now - last) * 1000.0 < interval_ms:
            return False
        setattr(parent, key, now)
        return True
    # (Removido: salvar summary para análise manual)
    if data["type"] == "file_start":
        # Arquivo iniciou o download
        filename = data['filename']
        index = data['index']
        parent.labels["arquivo"].setText(f"Arquivo: {filename}")
        parent._current_file_index = index
        if hasattr(parent, "file_progress_bar"):
            parent.file_progress_bar.setVisible(True)
            parent.file_progress_bar.setRange(0, 100)
            parent.file_progress_bar.setValue(0)
            parent.file_progress_bar.setFormat("%p%")
        # Mantem o status visual, mas nao registra no log.
    
    elif data["type"] == "file_progress":
        index = data.get("index")
        if getattr(parent, "_current_file_index", None) != index:
            return
        if not _throttled_update("_last_file_progress_ts", 120):
            return
        bytes_downloaded = data.get("bytes_downloaded", 0)
        total_bytes = data.get("total_bytes")
        if hasattr(parent, "file_progress_bar"):
            if total_bytes and total_bytes > 0:
                percent = int((bytes_downloaded / total_bytes) * 100)
                parent.file_progress_bar.setRange(0, 100)
                parent.file_progress_bar.setValue(percent)
                parent.file_progress_bar.setFormat("%p%")
            else:
                parent.file_progress_bar.setRange(0, 0)
                parent.file_progress_bar.setFormat("Baixando...")

    elif data["type"] == "file_complete":
        # Arquivo foi baixado com sucesso
        count = data.get("count", 0)
        total = data.get("total", 0)
        if total == 0:
            total = parent.progress_bar.maximum()
        percent = data.get("percent", 0)
        processed = data.get("processed", 0)
        filename = data['filename']
        
        # Atualizar progress bar usando processed_count para consistência
        parent.progress_bar.setValue(processed)

        # Atualizar label de progresso
        if parent.progress_bar.maximum() > 0:
            parent.progress_bar.setValue(processed)
        
        # Atualizar label de arquivo
        parent.labels["arquivo"].setText(f"Arquivo: {filename}")
        if getattr(parent, "_current_file_index", None) == data.get("index"):
            if hasattr(parent, "file_progress_bar"):
                parent.file_progress_bar.setRange(0, 100)
                parent.file_progress_bar.setValue(100)
                parent.file_progress_bar.setFormat("%p%")
        # Log message - sempre aparecer no log
        add_log_message(parent.log_widget, f"✓ Concluído {filename}")
        
        # Tentar adicionar thumbnail
        # Usar o caminho completo do arquivo se fornecido, caso contrário construir
        model_path = getattr(parent, "current_download_dir", None)
        if model_path:
            file_path = Path(model_path) / filename
            if file_path.exists():
                add_thumbnail(parent, str(file_path))
            else:
                # Tentar apenas no primeiro nível do diretório (sem recursão custosa)
                found = False
                try:
                    if Path(model_path).exists():
                        for p in Path(model_path).iterdir():
                            if p.is_file() and p.name == filename:
                                add_thumbnail(parent, str(p))
                                found = True
                                break
                except Exception:
                    pass
    
    elif data["type"] == "file_skipped":
        # Arquivo não estava disponível ou já existe
        index = data['index']
        reason = data.get('reason', 'indisponível')
        filename = data.get('filename', '')
        # Log apenas se arquivo já existe
        if reason == "Arquivo ja existe" and filename:
            add_log_message(parent.log_widget, f"⊘ Pulado [{index}] {filename} - {reason}", warning=True)
        # Atualizar progress bar e label com base em arquivos processados do worker
        processed = data.get("processed", 0)
        percent = data.get("percent", 0)
        total = data.get("total", 0)
        if total == 0:
            total = parent.progress_bar.maximum()
        parent.progress_bar.setValue(processed)
        if parent.progress_bar.maximum() > 0:
            parent.progress_bar.setValue(processed)
        if getattr(parent, "_current_file_index", None) == data.get("index"):
            if hasattr(parent, "file_progress_bar"):
                parent.file_progress_bar.setRange(0, 100)
                parent.file_progress_bar.setValue(100)
                parent.file_progress_bar.setFormat("%p%")
    elif data["type"] == "file_error":
        # Erro ao baixar arquivo
        filename = data['filename']
        error = data.get('error', 'erro desconhecido')
        # Atualizar progress bar e label com base em arquivos processados do worker
        processed = data.get("processed", 0)
        percent = data.get("percent", 0)
        total = data.get("total", 0)
        if total == 0:
            total = parent.progress_bar.maximum()
        parent.progress_bar.setValue(processed)
        if parent.progress_bar.maximum() > 0:
            parent.progress_bar.setValue(processed)
        if getattr(parent, "_current_file_index", None) == data.get("index"):
            if hasattr(parent, "file_progress_bar"):
                parent.file_progress_bar.setRange(0, 100)
                parent.file_progress_bar.setValue(100)
                parent.file_progress_bar.setFormat("%p%")
        # (Removido: guardar arquivo com erro para análise manual)
        parent.labels["status"].setText(f"Status: Erro ao baixar {filename}")
        add_log_message(parent.log_widget, f"✗ Erro em {filename}: {error}", error=True)
    
    elif data["type"] == "summary":
        total = data.get("total_expected", 0)
        success = data.get("success", 0)
        failed = data.get("failed", 0)
        skipped = data.get("skipped", 0)
        # Manter um único significado para a barra: arquivos processados (baixados, falhados ou pulados)
        processed = data.get("processed")
        if processed is None:
            processed = success + failed + skipped
        if total > 0:
            processed = min(processed, total)
        
        # Se Picazor e o total real era desconhecido, atualizar o máximo da barra agora
        if getattr(parent, "_picazor_real_total_unknown", False) and total > 0:
            parent.progress_bar.setRange(0, total)
            parent._picazor_real_total_unknown = False
        
        parent.progress_bar.setValue(processed)
        
        if total > 0 and parent.progress_bar.maximum() != total:
            parent.progress_bar.setRange(0, total)
            parent.progress_bar.setValue(processed)
        
        # (Removido: log de resumo no final do download)
    
    elif data["type"] == "status":
        # Atualizar status
        status = data["status"]
        parent.labels["status"].setText(f"Status: {status}")
        add_log_message(parent.log_widget, f"• Status: {status}")


def on_download_complete(parent, checar_btn, download_btn):
    """Handle successful download completion."""
    if getattr(parent, "_download_complete_called", False):
        return

    parent._download_started = False

    if getattr(parent, "_download_canceled", False):
        parent._download_canceled = False
        parent.labels["status"].setText("Status: Cancelado")
        checar_btn.setEnabled(True)
        download_btn.setEnabled(True)
        download_btn.setVisible(True)
        if hasattr(parent, "pause_btn"):
            parent.pause_btn.setVisible(False)
            parent.pause_btn.setEnabled(False)
        if hasattr(parent, "cancel_btn"):
            parent.cancel_btn.setVisible(False)
            parent.cancel_btn.setEnabled(False)
        if hasattr(parent, "progress_bar"):
            parent.progress_bar.setVisible(False)
        if hasattr(parent, "file_progress_bar"):
            parent.file_progress_bar.setVisible(False)
        return

    # Mensagem de confirmação com quantidade de arquivos baixados:
    # usar, quando disponível, a contagem de sucessos (ex.: armazenada em parent.download_success_count)
    arquivos = getattr(parent, "download_success_count", parent.progress_bar.value())
    parent._download_complete_called = True
    # Handle successful download completion.

    msg = f"✓ DOWNLOAD CONCLUÍDO! Arquivos baixados: {arquivos}"
    parent.labels["status"].setText("Status: Download concluído!")
    # (Removido: log de conclusão no final do download)
    # Desabilitar botão de download ao concluir
    if hasattr(parent, 'download_btn'):
        parent.download_btn.setEnabled(False)
    # Exibir mensagem modal de confirmação (não modal para evitar congelamento)
    dlg = QMessageBox(parent)
    dlg.setWindowTitle("Download Concluído")
    dlg.setText(msg)
    dlg.setIcon(QMessageBox.Information)
    dlg.setStandardButtons(QMessageBox.Ok)
    dlg.setModal(False)
    # Manter uma referência persistente para evitar coleta de lixo prematura
    parent._download_complete_msgbox = dlg
    dlg.finished.connect(lambda _: setattr(parent, '_download_complete_msgbox', None))
    dlg.show()
    # (Removido: lógica de análise manual ao concluir download)

    # Desabilitar botão de download após conclusão
    download_btn.setEnabled(False)
    download_btn.setVisible(True)
    checar_btn.setEnabled(True)
    
    # Ocultar botão de pausa ao terminar o download
    if hasattr(parent, "pause_btn"):
        parent.pause_btn.setVisible(False)
        parent.pause_btn.setEnabled(False)
    if hasattr(parent, "cancel_btn"):
        parent.cancel_btn.setVisible(False)
        parent.cancel_btn.setEnabled(False)
    
    # Ocultar barra de progresso e label ao terminar
    if hasattr(parent, "progress_bar"):
        parent.progress_bar.setVisible(False)
    if hasattr(parent, "file_progress_bar"):
        parent.file_progress_bar.setVisible(False)

    # Atualizar lista de modelos baixados
    refresh_downloaded_models_list(parent)


def on_download_error(parent, error, checar_btn, download_btn):
    """Handle download errors and re-enable buttons."""
    parent._download_started = False
    parent.labels["status"].setText(f"Status: Erro - {error}")
    add_log_message(parent.log_widget, f"✗ ERRO: {error}", error=True)
    download_btn.setEnabled(False)
    download_btn.setVisible(True)
    checar_btn.setEnabled(True)
    
    # Ocultar botão de pausa ao falhar o download
    if hasattr(parent, "pause_btn"):
        parent.pause_btn.setVisible(False)
        parent.pause_btn.setEnabled(False)
    if hasattr(parent, "cancel_btn"):
        parent.cancel_btn.setVisible(False)
        parent.cancel_btn.setEnabled(False)
    
    # Ocultar barra de progresso e label ao falhar
    if hasattr(parent, "progress_bar"):
        parent.progress_bar.setVisible(False)
    if hasattr(parent, "file_progress_bar"):
        parent.file_progress_bar.setVisible(False)


def get_downloaded_models(base_path=None):
    """Get list of downloaded models from catalog/models directory."""
    catalog_path = Path(base_path) if base_path else (Path("catalog") / "models")
    if not catalog_path.exists():
        return []
    
    try:
        models = [d.name for d in catalog_path.iterdir() if d.is_dir()]
        return sorted(models)
    except:
        return []


def refresh_downloaded_models_list(parent):
    pass  # painel removido


def add_thumbnail(parent, file_path):
    """Add a thumbnail to the thumbnails container."""
    # Adiciona thumbnail no QListWidget igual ao gui.py
    thumb_list = parent.thumb_list if hasattr(parent, 'thumb_list') else parent.thumbnails_container
    thumb_size = 220
    ext = os.path.splitext(file_path)[1].lower()
    
    item = QListWidgetItem()
    item.setSizeHint(QSize(thumb_size, thumb_size))
    item.setData(Qt.UserRole, file_path)
    
    if ext in ['.mp4', '.avi', '.mov', '.mkv']:
        # Insert a placeholder widget immediately, then update it asynchronously.
        placeholder = _create_video_placeholder(thumb_size)
        widget = _create_thumbnail_widget(placeholder, thumb_size)
        thumb_list.insertItem(0, item)
        thumb_list.setItemWidget(item, widget)
        _fade_in_widget(widget)
        _prune_thumbnails(thumb_list, getattr(parent, "thumbnails_limit", 0))

        # Create and configure worker before connecting signals
        thumbnail_worker = ThumbnailWorker(file_path, thumb_size)
        
        # Connect signals
        thumbnail_worker.thumbnail_ready.connect(
            lambda fp, icon: _update_thumbnail_icon(thumb_list, fp, icon)
        )

        def _cleanup_thumbnail_worker(worker=thumbnail_worker):
            # Remove worker reference and schedule deletion to free resources.
            try:
                if hasattr(parent, '_thumbnail_workers') and worker in parent._thumbnail_workers:
                    parent._thumbnail_workers.remove(worker)
            except ValueError:
                # Worker already removed; ignore.
                pass
            worker.deleteLater()

        thumbnail_worker.finished.connect(_cleanup_thumbnail_worker)

        if not hasattr(parent, '_thumbnail_workers'):
            parent._thumbnail_workers = []
        parent._thumbnail_workers.append(thumbnail_worker)
        thumbnail_worker.start()
    else:
        # Image: load directly
        pix = QPixmap(file_path)
        if pix.isNull():
            pix = QPixmap(thumb_size, thumb_size)
            pix.fill(Qt.darkGray)

        side = min(pix.width(), pix.height())
        x = (pix.width() - side) // 2
        y = (pix.height() - side) // 2
        pix = pix.copy(x, y, side, side)
        pix = pix.scaled(thumb_size, thumb_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        widget = _create_thumbnail_widget(pix, thumb_size)
        thumb_list.insertItem(0, item)
        thumb_list.setItemWidget(item, widget)
        _fade_in_widget(widget)
        _prune_thumbnails(thumb_list, getattr(parent, "thumbnails_limit", 0))


def _create_video_placeholder(thumb_size: int):
    """Create a placeholder pixmap for videos."""
    pix = QPixmap(thumb_size, thumb_size)
    pix.fill(QColor("#1a1a1a"))
    painter = QPainter(pix)
    painter.setPen(QColor("#666666"))
    painter.setFont(QFont("Arial", 14))
    painter.drawText(pix.rect(), Qt.AlignCenter, "▶\nVIDEO")
    painter.end()
    return pix


def _create_thumbnail_widget(pixmap: QPixmap, thumb_size: int) -> QLabel:
    label = QLabel()
    label.setFixedSize(thumb_size, thumb_size)
    label.setAlignment(Qt.AlignCenter)
    label.setPixmap(pixmap)
    return label


def _fade_in_widget(widget: QWidget, duration_ms: int = 220):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration_ms)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    widget._fade_anim = anim
    anim.start()


def _prune_thumbnails(thumb_list: QListWidget, limit: int):
    if not limit or limit <= 0:
        return
    while thumb_list.count() > limit:
        item = thumb_list.takeItem(thumb_list.count() - 1)
        if item is None:
            break
        widget = thumb_list.itemWidget(item)
        if widget is not None:
            widget.deleteLater()


def _update_thumbnail_icon(thumb_list, file_path, icon):
    """Update thumbnail icon once it's ready."""
    for i in range(thumb_list.count()):
        item = thumb_list.item(i)
        if item.data(Qt.UserRole) == file_path:
            widget = thumb_list.itemWidget(item)
            if isinstance(widget, QLabel):
                pix = icon.pixmap(widget.width(), widget.height())
                widget.setPixmap(pix)
            else:
                item.setIcon(icon)
            break



def add_log_message(log_widget, message, error=False, warning=False):
    """Adiciona mensagem ao log de atividades com tags e cor de linha para tipo de conteúdo."""
    # Detecta imagem/video
    is_img = "imagem" in message or "jpg" in message or "[IMG]" in message or (message.startswith("✓ Concluído ") and ".jpg" in message)
    is_video = "video" in message or "mp4" in message or "[VIDEO]" in message or (message.startswith("✓ Concluído ") and ".mp4" in message)
    is_thumb = message.startswith("Thumbnail:")

    if is_thumb:
        tag = "[THUMB]"
        color = "#B10DC9"  # roxo
    elif is_img:
        tag = "[IMG]"
        color = "#0074D9"  # azul
    elif is_video:
        tag = "[VIDEO]"
        color = "#2ECC40"  # verde
    elif error:
        tag = "[ERRO]"
        color = "#FF4136"  # vermelho
    elif warning:
        tag = "[AVISO]"
        color = "#FFDC00"  # amarelo
    else:
        tag = "[INFO]"
        color = "#AAAAAA"  # cinza

    # Escape HTML content to prevent markup injection
    escaped_message = html.escape(message)

    # Apenas a tag recebe cor; o texto permanece com a cor padrao
    html_line = f"<span style='color:{color};'><b>{tag}</b></span> {escaped_message}"

    if hasattr(log_widget, "_log_buffer") and hasattr(log_widget, "_log_timer"):
        log_widget._log_buffer.append(html_line)
        if not log_widget._log_timer.isActive():
            log_widget._log_timer.start()
    else:
        log_widget.append(html_line)
        scrollbar = log_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

def create_left_panel():
    """Create the left panel with checkboxes and info."""
    left_widget = QFrame()
    left_widget.setStyleSheet("background-color: #1e1e1e; border-right: 1px solid #333;")
    layout = QVBoxLayout(left_widget)
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(10)
    
    # Checkboxes
    checkbox_style = """
        QCheckBox {
            color: #ffffff;
            font-size: 11px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
    """

    baixar_imagens = QCheckBox("Baixar imagens")
    baixar_imagens.setChecked(True)
    baixar_imagens.setStyleSheet(checkbox_style)
    layout.addWidget(baixar_imagens)

    baixar_videos = QCheckBox("Baixar vídeos")
    baixar_videos.setStyleSheet(checkbox_style)
    layout.addWidget(baixar_videos)

    escolher_pasta = QCheckBox("Escolher pasta")
    escolher_pasta.setChecked(False)
    escolher_pasta.setStyleSheet(checkbox_style)
    escolher_pasta.setToolTip("Se marcado, pergunta a pasta de destino antes do download")
    layout.addWidget(escolher_pasta)

    # Container para Picazor settings (será mostrado/escondido conforme site selecionado)
    picazor_container = QWidget()
    picazor_layout = QVBoxLayout(picazor_container)
    picazor_layout.setContentsMargins(0, 0, 0, 0)
    picazor_layout.setSpacing(10)

    # Picazor settings
    info_style = "color: #ffffff; font-size: 11px;"
    spin_style = """
        QSpinBox, QDoubleSpinBox {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #555;
            padding: 2px 4px;
            border-radius: 3px;
        }
    """

    picazor_title = QLabel("Picazor (checagem)")
    picazor_title.setStyleSheet(info_style)
    picazor_title.setToolTip("Ajustes usados apenas na checagem de links do Picazor")
    picazor_layout.addWidget(picazor_title)

    threads_layout = QHBoxLayout()
    threads_label = QLabel("Threads:")
    threads_label.setStyleSheet(info_style)
    picazor_threads_input = QSpinBox()
    picazor_threads_input.setRange(1, 32)
    picazor_threads_input.setValue(FIXED_PICAZOR_THREADS)
    picazor_threads_input.setStyleSheet(spin_style)
    picazor_threads_input.setToolTip("Número de threads na checagem de links do Picazor (fixo)")
    picazor_threads_input.setEnabled(False)
    picazor_threads_input.setReadOnly(True)
    picazor_threads_input.setButtonSymbols(QAbstractSpinBox.NoButtons)
    picazor_threads_input.setFocusPolicy(Qt.NoFocus)
    threads_label.setVisible(False)
    picazor_threads_input.setVisible(False)
    threads_layout.addWidget(threads_label)
    threads_layout.addWidget(picazor_threads_input)
    picazor_layout.addLayout(threads_layout)

    batch_layout = QHBoxLayout()
    batch_label = QLabel("Lote:")
    batch_label.setStyleSheet(info_style)
    picazor_batch_input = QSpinBox()
    picazor_batch_input.setRange(5, 200)
    picazor_batch_input.setValue(PICAZOR_CHECK_BATCH_DEFAULT)
    picazor_batch_input.setStyleSheet(spin_style)
    picazor_batch_input.setToolTip("Quantidade de índices por rodada de checagem")
    batch_layout.addWidget(batch_label)
    batch_layout.addWidget(picazor_batch_input)
    picazor_layout.addLayout(batch_layout)

    delay_layout = QHBoxLayout()
    delay_label = QLabel("Delay (s):")
    delay_label.setStyleSheet(info_style)
    picazor_delay_input = QDoubleSpinBox()
    picazor_delay_input.setRange(0.0, 5.0)
    picazor_delay_input.setSingleStep(0.1)
    picazor_delay_input.setDecimals(2)
    picazor_delay_input.setValue(FIXED_PICAZOR_DELAY)
    picazor_delay_input.setStyleSheet(spin_style)
    picazor_delay_input.setToolTip("Delay entre rodadas de checagem (segundos) (fixo)")
    picazor_delay_input.setEnabled(False)
    picazor_delay_input.setReadOnly(True)
    picazor_delay_input.setButtonSymbols(QAbstractSpinBox.NoButtons)
    picazor_delay_input.setFocusPolicy(Qt.NoFocus)
    delay_label.setVisible(False)
    picazor_delay_input.setVisible(False)
    delay_layout.addWidget(delay_label)
    delay_layout.addWidget(picazor_delay_input)
    picazor_layout.addLayout(delay_layout)

    # Inicialmente escondido
    picazor_container.setVisible(False)
    layout.addWidget(picazor_container)

    # Info labels
    
    total_label = QLabel("Total: 0")
    total_label.setStyleSheet(info_style)
    layout.addWidget(total_label)
    
    pasta_label = QLabel("Pasta: -")
    pasta_label.setStyleSheet(info_style)
    layout.addWidget(pasta_label)

    destino_label = QLabel("Destino: -")
    destino_label.setStyleSheet(info_style)
    destino_label.setVisible(False)
    layout.addWidget(destino_label)
    

    status_label = QLabel("Status: Pronto")
    status_label.setStyleSheet(info_style + " color: #90EE90;")
    layout.addWidget(status_label)

    arquivo_label = QLabel("Arquivo: -")
    arquivo_label.setStyleSheet(info_style)
    layout.addWidget(arquivo_label)
    
    # Separator
    separator = QFrame()
    separator.setStyleSheet("background-color: #444;")
    separator.setMinimumHeight(1)
    layout.addWidget(separator)
    
    # Add stretch to push everything to top
    layout.addStretch()
    
    # Create labels dictionary for external access
    labels_dict = {
        "total": total_label,
        "pasta": pasta_label,
        "destino": destino_label,
        "status": status_label,
        "arquivo": arquivo_label
    }
    
    # Create checkboxes dictionary for external access (sem análise manual)
    checkboxes_dict = {
        "imagens": baixar_imagens,
        "videos": baixar_videos,
        "escolher_pasta": escolher_pasta,
    }
    left_widget.picazor_threads_input = picazor_threads_input
    left_widget.picazor_batch_input = picazor_batch_input
    left_widget.picazor_delay_input = picazor_delay_input
    left_widget.picazor_container = picazor_container
    left_widget.picazor_title = picazor_title
    left_widget.threads_label = threads_label
    left_widget.batch_label = batch_label
    left_widget.delay_label = delay_label
    left_widget.separator = separator
    return left_widget, labels_dict, checkboxes_dict



