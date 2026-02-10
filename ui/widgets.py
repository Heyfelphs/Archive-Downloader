from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QListWidgetItem, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import QSize
# Janela para análise manual de imagens
class ManualReviewDialog(QDialog):
    def __init__(self, parent, url_list):
        super().__init__(parent)
        self.setWindowTitle("Análise Manual de Arquivos Falhados")
        self.setMinimumSize(700, 400)
        layout = QVBoxLayout(self)
        label = QLabel("Selecione as URLs das imagens que deseja baixar manualmente:")
        layout.addWidget(label)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        for url in url_list:
            item = QListWidgetItem(url)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    def get_selected(self):
        return [item.text() for item in self.list_widget.selectedItems()]
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QCheckBox, QPushButton, QListWidget, QListWidgetItem, 
    QFrame, QProgressBar, QScrollArea, QTextEdit, QGridLayout, QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFont, QPixmap, QIcon, QDesktopServices
from datetime import datetime
from config import APP_NAME, VERSION, APP_NAME_COLOR
from core.fapello_client import get_total_files
from core.downloader_progress import download_orchestrator_with_progress
from multiprocessing import Queue
import os
from pathlib import Path


class FetchWorker(QThread):
    """Worker thread para buscar informações sem bloquear a UI."""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            if not self.url.strip():
                self.error.emit("URL vazia!")
                return
            
            total_files = get_total_files(self.url)
            # Extract model name robustly (handle trailing slash)
            parts = [p for p in self.url.split("/") if p]
            pasta = parts[-1] if parts else ""
            
            self.finished.emit({
                "total": total_files,
                "pasta": pasta
            })
        except Exception as e:
            self.error.emit(f"Erro ao buscar: {str(e)}")


class DownloadWorker(QThread):
    """Worker thread para baixar arquivos sem bloquear a UI."""
    progress_update = Signal(dict)  # Emite atualizações de progresso
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, url: str, download_images: bool, download_videos: bool, total_files: int, target_dir: Path):
        super().__init__()
        self.url = url
        self.download_images = download_images
        self.download_videos = download_videos
        self.total_files = total_files
        self.target_dir = target_dir
    
    def progress_callback(self, data):
        """Callback for progress updates from downloader."""
        if data["type"] == "file_start":
            self.progress_update.emit({
                "type": "file_start",
                "filename": data["filename"],
                "index": data["index"]
            })
        elif data["type"] == "file_complete":
            success_count = data.get("success", 0)
            # Calculate percentage based on actual downloads
            progress_percent = int((success_count / self.total_files) * 100) if self.total_files > 0 else 0
            self.progress_update.emit({
                "type": "file_complete",
                "filename": data["filename"],
                "index": data["index"],
                "count": success_count,
                "total": self.total_files,
                "percent": progress_percent
            })
        elif data["type"] == "file_skipped":
            self.progress_update.emit({
                "type": "file_skipped",
                "index": data["index"],
                "reason": data["reason"]
            })
        elif data["type"] == "file_error":
            self.progress_update.emit({
                "type": "file_error",
                "filename": data["filename"],
                "error": data.get("error", ""),
                "success": data.get("success", 0),
                "failed": data.get("failed", 0)
            })
        elif data["type"] == "summary":
            self.progress_update.emit({
                "type": "summary",
                "total_expected": data["total_expected"],
                "success": data["success"],
                "failed": data["failed"],
                "skipped": data["skipped"],
                "failed_indices": data["failed_indices"]
            })
        elif data["type"] == "status":
            self.progress_update.emit({
                "type": "status",
                "status": data["status"]
            })
    
    def run(self):
        try:
            download_orchestrator_with_progress(
                self.url, 
                workers=4,
                progress_callback=self.progress_callback,
                target_dir=self.target_dir
            )
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Erro no download: {str(e)}")





def build_ui(parent):
    """Build and configure the UI elements for the application window."""
    
    # Central widget
    central_widget = QWidget()
    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    
    # Top section with link input and buttons
    top_section, link_input = create_top_section(central_widget)
    main_layout.addWidget(top_section)
    
    # Middle section with left panel and right models list
    middle_section, labels_dict, checkboxes_dict, models_list = create_middle_section()
    main_layout.addWidget(middle_section, 1)
    
    # Bottom section with progress and log areas
    bottom_section, progress_bar, progress_label, log_widget, thumbnails_container = create_bottom_section()
    main_layout.addWidget(bottom_section, 1)
    
    # Store references for later access
    central_widget.link_input = link_input
    central_widget.labels = labels_dict
    central_widget.checkboxes = checkboxes_dict
    central_widget.progress_bar = progress_bar
    central_widget.progress_label = progress_label
    central_widget.log_widget = log_widget
    central_widget.models_list = models_list
    central_widget.thumbnails_container = thumbnails_container
    central_widget.thumb_list = thumbnails_container
    # default number of columns for thumbnails grid (fixo em 4)
    central_widget.thumbnails_columns = 4
    # limit how many thumbnails are kept in the grid
    central_widget.thumbnails_limit = 5
    # Default download root
    central_widget.download_root = Path("catalog") / "models"
    if "destino" in labels_dict:
        labels_dict["destino"].setText(f"Destino: {central_widget.download_root}")
    
    # Carregar modelos já baixados
    # (A linha abaixo foi corrigida para não ter indentação errada)
    # central_widget.thumbnails_columns = 4  # já definido acima
    return central_widget


def create_top_section(parent):
    """Create the top section with link input and buttons."""
    top_widget = QFrame()
    top_widget.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #333;")
    layout = QHBoxLayout(top_widget)
    layout.setContentsMargins(15, 10, 15, 10)
    layout.setSpacing(10)
    
    # Link label
    link_label = QLabel("Link:")
    link_label.setStyleSheet("color: #ffffff; font-weight: bold;")
    layout.addWidget(link_label)
    
    # Link input
    link_input = QLineEdit()
    link_input.setPlaceholderText("https://fapello.com/...")
    link_input.setStyleSheet("""
        QLineEdit {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444;
            padding: 5px;
            border-radius: 3px;
        }
    """)
    link_input.setMinimumHeight(32)
    layout.addWidget(link_input, 1)
    
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
    checar_btn.link_input = link_input
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

    
    # Abrir pasta button
    open_folder_btn = QPushButton("Abrir pasta")
    open_folder_btn.setMinimumWidth(90)
    open_folder_btn.setMinimumHeight(32)
    open_folder_btn.setEnabled(False)
    open_folder_btn.setStyleSheet("""
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
    layout.addWidget(open_folder_btn)
    
    # Store buttons in parent for external access
    parent.checar_btn = checar_btn
    parent.download_btn = download_btn
    parent.open_folder_btn = open_folder_btn
    
    # Connect link input to enable/disable checar button
    def on_link_changed():
        has_text = len(link_input.text().strip()) > 0
        checar_btn.setEnabled(has_text)
        # Reset download button when link changes
        if has_text:
            download_btn.setVisible(True)
            download_btn.setEnabled(False)
        if hasattr(parent, "open_folder_btn"):
            parent.open_folder_btn.setEnabled(False)
        parent._download_complete_called = False
    
    link_input.textChanged.connect(on_link_changed)
    
    # Connect checar button to fetch function
    def on_checar_clicked():
        url = link_input.text().strip()
        parent.thumbnails_container.columns = 4
        if not url:
            parent.labels["status"].setText("Status: URL vazia!")
            return
        
        # Log message
        add_log_message(parent.log_widget, f"🔍 Buscando informações da URL: {url}")
        
        # Disable checar button during fetch
        checar_btn.setEnabled(False)
        parent.labels["status"].setText("Status: Buscando...")
        
        # Create worker thread
        worker = FetchWorker(url)
        worker.finished.connect(lambda data: on_fetch_complete(parent, data, checar_btn, download_btn))
        worker.error.connect(lambda err: on_fetch_error(parent, err, checar_btn))
        worker.start()
        parent.fetch_worker = worker  # Store reference to prevent garbage collection
    
    checar_btn.clicked.connect(on_checar_clicked)
    
    # Connect download button to download function
    def on_download_clicked():
        url = link_input.text().strip()
        if not url:
            parent.labels["status"].setText("Status: URL vazia!")
            return
        
        # Get checkbox states
        download_images = parent.checkboxes["imagens"].isChecked()
        download_videos = parent.checkboxes["videos"].isChecked()
        
        if not download_images and not download_videos:
            parent.labels["status"].setText("Status: Selecione imagens ou vídeos!")
            return

        # Pergunta a pasta de destino antes de iniciar o download
        base_dir = getattr(parent, "download_root", Path("catalog") / "models")
        parts = [p for p in url.split("/") if p]
        model_name = parts[-1] if parts else ""
        suggested_dir = base_dir / model_name if model_name else base_dir
        folder = QFileDialog.getExistingDirectory(parent, "Escolha a pasta para salvar o download", str(suggested_dir))
        if not folder:
            parent.labels["status"].setText("Status: Download cancelado pelo usuário.")
            checar_btn.setEnabled(True)
            download_btn.setEnabled(True)
            return
        # Cria subpasta com nome da modelo
        parts = [p for p in url.split("/") if p]
        model_name = parts[-1] if parts else "modelo"
        target_dir = Path(folder) / model_name
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
        parent.current_download_dir = target_dir
        parent.last_download_dir = target_dir
        if hasattr(parent, "labels") and "destino" in parent.labels:
            parent.labels["destino"].setText(f"Destino: {target_dir}")
        add_log_message(parent.log_widget, f"Destino escolhido: {target_dir}")
        
        # Get total files from label
        total_text = parent.labels["total"].text()
        try:
            total_files = int(total_text.split(": ")[1])
        except:
            total_files = 0
        
        # Log message
        download_types = []
        if download_images:
            download_types.append("imagens")
        if download_videos:
            download_types.append("vídeos")
        add_log_message(parent.log_widget, f"⬇️  Iniciando download de {', '.join(download_types)} ({total_files} arquivo(s))")
        add_log_message(parent.log_widget, f"Destino: {target_dir}")
        
        # Limpar thumbnails anteriores
        flow_widget = parent.thumbnails_container
        flow_layout = flow_widget.layout()
        if flow_layout:
            # Remove all widgets except the stretch
            while flow_layout.count() > 0:
                item = flow_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
        # Disable download button during download
        download_btn.setEnabled(False)
        checar_btn.setEnabled(False)
        if hasattr(parent, "open_folder_btn"):
            parent.open_folder_btn.setEnabled(False)
        parent._download_complete_called = False
        parent.labels["status"].setText("Status: Baixando...")
        parent.progress_bar.setValue(0)
        
        # Reset failed files list for manual analysis
        parent.failed_files_for_analysis = []
        # Create download worker thread
        download_worker = DownloadWorker(url, download_images, download_videos, total_files, target_dir)
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
                parent.labels["destino"].setText(f"Destino: {folder}")
            add_log_message(parent.log_widget, f"Pasta de download selecionada: {folder}")

    # (Removido: botão de escolher pasta)

    def on_open_folder_clicked():
        target_dir = getattr(parent, "last_download_dir", None)
        if not target_dir:
            add_log_message(parent.log_widget, "Nenhuma pasta para abrir ainda.", warning=True)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir)))

    open_folder_btn.clicked.connect(on_open_folder_clicked)
    
    return top_widget, link_input


def on_fetch_complete(parent, data, checar_btn, download_btn):
    """Handle successful fetch."""
    parent.labels["total"].setText(f"Total: {data['total']}")
    parent.labels["pasta"].setText(f"Pasta: {data['pasta']}")
    parent.labels["status"].setText("Status: Pronto")
    parent.progress_bar.setMaximum(data['total'])
    parent.progress_label.setText(f"0 / {data['total']} arquivos (0%)")
    
    # Log message
    add_log_message(parent.log_widget, f"✓ Busca concluída: {data['total']} arquivo(s) encontrado(s)")
    add_log_message(parent.log_widget, f"Pasta definida: {data['pasta']}")
    base_dir = getattr(parent, "download_root", Path("catalog") / "models")
    add_log_message(parent.log_widget, f"Destino: {base_dir}")
    
    # Enable download button and show it
    download_btn.setVisible(True)
    download_btn.setEnabled(True)
    
    # Keep checar button disabled until link changes


def on_fetch_error(parent, error, checar_btn):
    """Handle fetch error and re-enable checar button."""
    parent.labels["status"].setText(f"Status: Erro")
    
    # Log message
    add_log_message(parent.log_widget, f"✗ Erro na busca: {error}", error=True)
    
    # Re-enable checar button to allow retry
    checar_btn.setEnabled(True)


def on_download_progress_update(parent, data):
    # (Removido: salvar summary para análise manual)
    """Handle detailed download progress updates."""
    if data["type"] == "file_start":
        # Arquivo iniciou o download
        filename = data['filename']
        index = data['index']
        parent.labels["arquivo"].setText(f"Arquivo: {filename}")
        add_log_message(parent.log_widget, f"→ Baixando [{index}] {filename}...")
    
    elif data["type"] == "file_complete":
        # Arquivo foi baixado com sucesso
        count = data.get("count", 0)
        total = data.get("total", 0)
        percent = data.get("percent", 0)
        filename = data['filename']
        
        # Atualizar progress bar
        parent.progress_bar.setValue(count)
        
        # Atualizar label de progresso
        parent.progress_label.setText(f"{count} / {total} arquivos ({percent}%)")
        
        # Atualizar label de arquivo
        parent.labels["arquivo"].setText(f"Arquivo: {filename}")
        
        # Log message
        add_log_message(parent.log_widget, f"✓ Concluído [{count}/{total}] {filename}")
        
        # Tentar adicionar thumbnail
        # Construir caminho do arquivo baseado no padrão catalog/models/[model_name]/[filename]
        model_path = getattr(parent, "current_download_dir", None)
        if model_path:
            file_path = Path(model_path) / filename
            add_log_message(parent.log_widget, f"Tentando thumbnail: {file_path}")
            if file_path.exists():
                add_log_message(parent.log_widget, f"Thumbnail encontrado: {file_path}")
                add_thumbnail(parent, str(file_path))
            else:
                add_log_message(parent.log_widget, f"Thumbnail não encontrado no caminho exato: {file_path}", warning=True)
                # procura por arquivos com mesma extensão no diretório do modelo
                try:
                    if Path(model_path).exists():
                        found = False
                        for p in Path(model_path).rglob(f"*{Path(filename).suffix}"):
                            add_log_message(parent.log_widget, f"Procurando alternativa: {p}")
                            if filename.split("_")[-1] in p.name or str(filename) == p.name:
                                add_log_message(parent.log_widget, f"Alternativa encontrada: {p}")
                                add_thumbnail(parent, str(p))
                                found = True
                                break
                        if not found:
                            add_log_message(parent.log_widget, "Nenhuma thumbnail encontrada no diretório do modelo.", warning=True)
                except Exception as e:
                    add_log_message(parent.log_widget, f"Erro ao procurar thumbnail: {e}", error=True)
    
    elif data["type"] == "file_skipped":
        # Arquivo não estava disponível
        index = data['index']
        reason = data.get('reason', 'indisponível')
        add_log_message(parent.log_widget, f"⊘ Pulado [{index}] {reason}", warning=True)
        # (Removido: guardar arquivo pulado para análise manual)
    
    elif data["type"] == "file_error":
        # Erro ao baixar arquivo
        filename = data['filename']
        error = data.get('error', 'erro desconhecido')
        # Increment progress bar and label even on error
        current = parent.progress_bar.value() + 1
        parent.progress_bar.setValue(current)
        # Try to get total from label or progress bar
        total = parent.progress_bar.maximum()
        percent = int((current / total) * 100) if total else 0
        parent.progress_label.setText(f"{current} / {total} arquivos ({percent}%)")
        # (Removido: guardar arquivo com erro para análise manual)
        parent.labels["status"].setText(f"Status: Erro ao baixar {filename}")
        add_log_message(parent.log_widget, f"✗ Erro em {filename}: {error}", error=True)
    
    elif data["type"] == "summary":
        # Resumo final do download
        total = data.get("total_expected", 0)
        success = data.get("success", 0)
        failed = data.get("failed", 0)
        skipped = data.get("skipped", 0)
        
        # Atualizar labels com resumo
        parent.progress_bar.setValue(success)
        
        summary_msg = f"{success} / {total} arquivos baixados com sucesso"
        if failed > 0:
            summary_msg += f" ({failed} falharam"
            if skipped > 0:
                summary_msg += f", {skipped} indisponíveis"
            summary_msg += ")"
        elif skipped > 0:
            summary_msg += f" ({skipped} indisponíveis)"
        
        parent.progress_label.setText(summary_msg)
        
        # Log message with summary
        add_log_message(parent.log_widget, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        add_log_message(parent.log_widget, f"✓ RESUMO: {success} sucesso(s) | {failed} falha(s) | {skipped} indisponível(is)")
        add_log_message(parent.log_widget, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    elif data["type"] == "status":
        # Atualizar status
        status = data["status"]
        parent.labels["status"].setText(f"Status: {status}")
        add_log_message(parent.log_widget, f"• Status: {status}")



def on_download_complete(parent, checar_btn, download_btn):
    # Evitar execução duplicada
    if getattr(parent, '_download_complete_called', False):
        return
    parent._download_complete_called = True
    """Handle successful download completion."""
    # Mensagem de confirmação com quantidade de arquivos baixados (usa valor da barra de progresso)
    arquivos = parent.progress_bar.value()
    msg = f"✓ DOWNLOAD CONCLUÍDO! Arquivos baixados: {arquivos}"
    parent.labels["status"].setText("Status: Download concluído!")
    add_log_message(parent.log_widget, msg)
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
    dlg.show()
    # (Removido: lógica de análise manual ao concluir download)

    # Desabilitar botão de download após conclusão
    download_btn.setEnabled(False)
    checar_btn.setEnabled(True)
    if hasattr(parent, "open_folder_btn"):
        parent.open_folder_btn.setEnabled(True)

    # Atualizar lista de modelos baixados
    refresh_downloaded_models_list(parent)


def on_download_error(parent, error, checar_btn, download_btn):
    """Handle download errors and re-enable buttons."""
    parent.labels["status"].setText(f"Status: Erro - {error}")
    add_log_message(parent.log_widget, f"✗ ERRO: {error}", error=True)
    download_btn.setEnabled(False)
    checar_btn.setEnabled(True)
    if hasattr(parent, "open_folder_btn"):
        parent.open_folder_btn.setEnabled(False)


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
    """Refresh the downloaded models list widget."""
    if hasattr(parent, 'models_list'):
        parent.models_list.clear()
        base_dir = getattr(parent, "download_root", None)
        models = get_downloaded_models(base_dir)
        for model in models:
            item = QListWidgetItem(f"✓ {model}")
            parent.models_list.addItem(item)


def add_thumbnail(parent, file_path):
    """Add a thumbnail to the thumbnails container."""
    # Adiciona thumbnail no QListWidget igual ao gui.py
    thumb_list = parent.thumb_list if hasattr(parent, 'thumb_list') else parent.thumbnails_container
    thumb_size = 120
    pix = QPixmap(file_path)
    if pix.isNull():
        return
    item = QListWidgetItem()
    item.setSizeHint(QSize(thumb_size + 20, thumb_size + 35))
    side = min(pix.width(), pix.height())
    x = (pix.width() - side) // 2
    y = (pix.height() - side) // 2
    pix = pix.copy(x, y, side, side)
    pix = pix.scaled(thumb_size, thumb_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    item.setIcon(QIcon(pix))
    item.setData(Qt.UserRole, file_path)
    thumb_list.insertItem(0, item)



def reflow_thumbnails(parent):
    """Reflow existing thumbnails according to current `thumbnails_columns`."""
    # Não é mais necessário com QListWidget responsivo
    pass


def add_log_message(log_widget, message, error=False, warning=False):
    """Adiciona mensagem ao log de atividades sem horário e sem informações de thumbnail."""
    # Tag customizada para imagens baixadas e início de download
    if message.startswith("✓ Concluído "):
        tag = "<span style='color: #00bfff;'>[IMG]</span>"
    elif message.startswith("→ Baixando "):
        tag = "<span style='color: #ffd93d;'>[AVISO]</span>"
    elif error:
        tag = "<span style='color: #ff4d4d;'>[ERRO]</span>"
    elif warning:
        tag = "<span style='color: #ffd93d;'>[AVISO]</span>"
    else:
        tag = "<span style='color: #90EE90;'>[INFO]</span>"
    # Remove mensagens de thumbnail
    if (
        message.startswith("Thumbnail encontrado:") or
        message.startswith("Tentando thumbnail:") or
        message.startswith("Thumbnail não encontrado") or
        message.startswith("Procurando alternativa:") or
        message.startswith("Alternativa encontrada:")
    ):
        return
    log_widget.append(f"{tag} {message}")
    
    # Auto-scroll to bottom
    scrollbar = log_widget.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())

def create_middle_section():
    """Create the middle section with left info panel and right models list."""
    middle_widget = QWidget()
    middle_widget.setStyleSheet("background-color: #1e1e1e;")
    layout = QHBoxLayout(middle_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    
    # Left panel
    left_panel, labels_dict, checkboxes_dict = create_left_panel()
    layout.addWidget(left_panel, 1)
    
    # Right panel with models list
    right_panel, models_list = create_right_panel()
    layout.addWidget(right_panel, 1)
    
    return middle_widget, labels_dict, checkboxes_dict, models_list


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

    
    # Info labels
    info_style = "color: #ffffff; font-size: 11px;"
    
    total_label = QLabel("Total: 0")
    total_label.setStyleSheet(info_style)
    layout.addWidget(total_label)
    
    pasta_label = QLabel("Pasta: -")
    pasta_label.setStyleSheet(info_style)
    layout.addWidget(pasta_label)

    destino_label = QLabel("Destino: -")
    destino_label.setStyleSheet(info_style)
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
        "videos": baixar_videos
    }
    return left_widget, labels_dict, checkboxes_dict


def create_right_panel():
    """Create the right panel with downloaded models list."""
    right_widget = QFrame()
    right_widget.setStyleSheet("background-color: #252525;")
    layout = QVBoxLayout(right_widget)
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(8)
    
    # Title
    title_label = QLabel("Modelos Baixados")
    title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
    layout.addWidget(title_label)
    
    # Models list
    models_list = QListWidget()
    models_list.setStyleSheet("""
        QListWidget {
            background-color: #2d2d2d;
            color: #90EE90;
            border: 1px solid #444;
            border-radius: 3px;
            font-size: 10px;
        }
        QListWidget::item:hover {
            background-color: #3d3d3d;
        }
        QListWidget::item:selected {
            background-color: #90EE90;
            color: #000000;
        }
    """)
    layout.addWidget(models_list)
    
    return right_widget, models_list


def create_bottom_section():
    thumb_list = QListWidget()
    thumb_list.setViewMode(QListWidget.IconMode)
    thumb_list.setResizeMode(QListWidget.Adjust)
    thumb_list.setMovement(QListWidget.Static)
    thumb_list.setSpacing(10)
    thumb_size = 120
    thumb_list.setIconSize(QSize(thumb_size, thumb_size))
    thumb_list.setGridSize(QSize(thumb_size + 20, thumb_size + 35))
    thumb_list.setStyleSheet("background-color: #2d2d2d; border: 1px solid #444; border-radius: 3px;")

    # Função para ajustar gridSize para sempre 4 colunas
    # Como a janela é fixa e maximizada, calcula o tamanho das thumbnails uma vez
    cols = 4
    spacing = thumb_list.spacing()
    frame = thumb_list.frameWidth() * 2
    # Usa a largura do thumb_list após maximizar
    def set_fixed_thumb_grid():
        # Só executa se thumb_list ainda existir
        try:
            width = thumb_list.width() - frame
        except RuntimeError:
            return
        width = thumb_list.width() - frame
        thumb_size = int((width - (cols - 1) * spacing) / cols)
        thumb_list.setIconSize(QSize(thumb_size, thumb_size))
        thumb_list.setGridSize(QSize(thumb_size, thumb_size))
        thumb_list.setStyleSheet("QListWidget::item { margin: 0; padding: 0; }")
        thumb_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    QTimer.singleShot(100, set_fixed_thumb_grid)
    """Create the bottom section with progress bar, log area and thumbnails."""
    bottom_widget = QFrame()
    bottom_widget.setStyleSheet("background-color: #1e1e1e;")
    layout = QVBoxLayout(bottom_widget)
    layout.setContentsMargins(15, 10, 15, 15)
    layout.setSpacing(10)
    
    # Progress info
    progress_label = QLabel("0 / 0 arquivos (0%)")
    progress_label.setStyleSheet("color: #ffffff; font-size: 11px;")
    layout.addWidget(progress_label)
    
    # Progress bar
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
    layout.addWidget(progress_bar)
    
    # Log and thumbnails container
    content_container = QWidget()
    content_layout = QHBoxLayout(content_container)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(10)
    
    # Log section
    log_section = QWidget()
    log_layout = QVBoxLayout(log_section)
    log_layout.setContentsMargins(0, 0, 0, 0)
    log_layout.setSpacing(5)
    
    # Log label
    log_label = QLabel("Log de Atividades:")
    log_label.setStyleSheet("color: #ffffff; font-size: 11px;")
    log_layout.addWidget(log_label)
    
    # Log widget
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
    log_layout.addWidget(log_widget, 1)
    content_layout.addWidget(log_section, 1)

    # Thumbnails section substituído por QListWidget responsivo
    thumbnails_section = QWidget()
    thumbnails_layout = QVBoxLayout(thumbnails_section)
    thumbnails_layout.setContentsMargins(0, 0, 0, 0)
    thumbnails_layout.setSpacing(5)

    thumb_label = QLabel("Downloads:")
    thumb_label.setStyleSheet("color: #ffffff; font-size: 11px;")
    thumbnails_layout.addWidget(thumb_label)

    thumb_list = QListWidget()
    thumb_list.setViewMode(QListWidget.IconMode)
    thumb_list.setResizeMode(QListWidget.Adjust)
    thumb_list.setMovement(QListWidget.Static)
    thumb_list.setSpacing(10)
    thumb_size = 120
    thumb_list.setIconSize(QSize(thumb_size, thumb_size))
    thumb_list.setGridSize(QSize(thumb_size + 20, thumb_size + 35))
    thumb_list.setStyleSheet("background-color: #2d2d2d; border: 1px solid #444; border-radius: 3px;")
    thumbnails_layout.addWidget(thumb_list, 1)
    content_layout.addWidget(thumbnails_section, 1)
    # Para compatibilidade com o restante do código:
    thumbnails_container = thumb_list
    
    layout.addWidget(content_container, 1)
    
    return bottom_widget, progress_bar, progress_label, log_widget, thumbnails_container

