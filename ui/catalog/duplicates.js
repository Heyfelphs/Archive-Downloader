const list = document.getElementById("duplicatesList");
const statusText = document.getElementById("statusText");
const statTotal = document.getElementById("stat-total");
const statHashed = document.getElementById("stat-hashed");
const statCache = document.getElementById("stat-cache");
const statGroups = document.getElementById("stat-groups");
const statWaste = document.getElementById("stat-waste");
const cancelBtn = document.getElementById("btn-cancel");

let groupCount = 0;
let totalWaste = 0;
const seenGroups = new Set();
const pendingGroups = [];

function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast ${type}`;
  setTimeout(() => toast.classList.add("show"), 10);
  setTimeout(() => toast.classList.remove("show"), 3000);
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

function getFileName(filePath) {
  const parts = filePath.split(/\\|\//);
  return parts[parts.length - 1] || filePath;
}

function updateSummary(summary) {
  if (!summary) return;
  if (typeof summary.total_files === "number") statTotal.textContent = summary.total_files;
  if (typeof summary.hashed_files === "number") statHashed.textContent = summary.hashed_files;
  if (typeof summary.duplicate_groups === "number") statGroups.textContent = summary.duplicate_groups;
  if (typeof summary.total_waste_bytes === "number") statWaste.textContent = formatBytes(summary.total_waste_bytes);
}

function renderGroup(group) {
  if (!group || !group.hash || !Array.isArray(group.files)) return;
  if (seenGroups.has(group.hash)) return;
  seenGroups.add(group.hash);

  groupCount += 1;
  totalWaste += group.waste || 0;
  statGroups.textContent = groupCount;
  statWaste.textContent = formatBytes(totalWaste);

  const container = document.createElement("div");
  container.className = "duplicate-group";
  container.id = `group-${group.hash}`;
  container.dataset.files = JSON.stringify(group.files);

  const header = document.createElement("div");
  header.className = "duplicate-header";
  header.innerHTML = `
    <div>
      <strong>Grupo ${groupCount}</strong> - ${group.count} cópias - ${formatBytes(group.size)} cada
      <span class="waste-badge">-${formatBytes(group.waste)}</span>
    </div>
    <button class="btn-keep-one" data-group-id="group-${group.hash}">🗑️ Excluir Duplicatas (${group.count - 1})</button>
  `;

  // Primeira imagem (referência)
  const firstFile = group.files[0];
  console.log("Primeiro arquivo:", firstFile);
  const firstMediaUrl = `/media/${firstFile.replace(/\\/g, "/")}`;
  console.log("URL da mídia:", firstMediaUrl);
  const firstIsVideo = /\.(mp4|avi|mov|mkv|flv|wmv|m4v)$/i.test(firstFile);
  const firstFileName = getFileName(firstFile);

  const referenceWrap = document.createElement("div");
  referenceWrap.className = "reference-image";
  referenceWrap.innerHTML = `
    <div class="reference-label">📌 Imagem de Referência (será mantida)</div>
    <div class="reference-thumbnail">
      ${firstIsVideo ? `<video src="${firstMediaUrl}" class="ref-thumb" controls preload="metadata" onerror="console.error('Erro ao carregar vídeo:', this.src)"></video>` : `<img src="${firstMediaUrl}" class="ref-thumb" loading="lazy" onerror="console.error('Erro ao carregar imagem:', this.src)">`}
    </div>
    <div class="reference-name">${firstFileName}</div>
  `;

  // Duplicatas (todas exceto a primeira)
  const filesWrap = document.createElement("div");
  filesWrap.className = "duplicate-files";

  if (group.files.length > 1) {
    const duplicatesLabel = document.createElement("div");
    duplicatesLabel.className = "duplicates-label";
    duplicatesLabel.textContent = `🔄 Duplicatas (${group.files.length - 1})`;
    filesWrap.appendChild(duplicatesLabel);

    const duplicatesGrid = document.createElement("div");
    duplicatesGrid.className = "duplicates-grid";

    group.files.slice(1).forEach((filePath, index) => {
      const mediaUrl = `/media/${filePath.replace(/\\/g, "/")}`;
      const isVideo = /\.(mp4|avi|mov|mkv|flv|wmv|m4v)$/i.test(filePath);
      const fileId = `file-${group.hash}-${index + 1}`;
      const fileName = getFileName(filePath);

      const fileItem = document.createElement("div");
      fileItem.className = "file-item";
      fileItem.id = fileId;
      fileItem.dataset.filePath = filePath;

      fileItem.innerHTML = `
        <div class="file-thumbnail">
          ${isVideo ? `<video src="${mediaUrl}" class="dup-thumb" controls preload="metadata" onerror="console.error('Erro ao carregar vídeo:', this.src)"></video>` : `<img src="${mediaUrl}" class="dup-thumb" loading="lazy" onerror="console.error('Erro ao carregar imagem:', this.src)">`}
        </div>
        <div class="file-info">
          <div class="file-path">${fileName}</div>
        </div>
      `;

      duplicatesGrid.appendChild(fileItem);
    });

    filesWrap.appendChild(duplicatesGrid);
  }

  container.appendChild(header);
  container.appendChild(referenceWrap);
  if (group.files.length > 1) {
    container.appendChild(filesWrap);
  }
  list.appendChild(container);
}

async function keepOnlyOne(groupId, files, btn) {
  if (files.length < 2) return;
  
  btn.disabled = true;
  btn.textContent = "⏳ Processando...";

  // Criar managers para cada arquivo a deletar com confirmação suprimida
  const filesToDelete = files.slice(1);
  const managers = filesToDelete.map(filePath =>
    DeleteManager.createDuplicateDelete(filePath, null, {
      showNotification: false,
      suppressConfirmation: true  // Suprimir confirmação individual
    })
  );

  // Executar batch de deletions com confirmação única
  DeleteManager.executeBatchWithConfirmation(
    managers,
    `Deletar ${filesToDelete.length} arquivo(s) duplicado(s)?`,
    (deleted, total) => {
      btn.textContent = `⏳ Deletando... (${deleted}/${total})`;
    }
  ).then(result => {
    const groupElement = document.getElementById(groupId);
    
    if (result.allSuccess && groupElement) {
      // Todos deletados com sucesso - remove o grupo
      groupElement.remove();
      showToast("✅ Todas duplicatas removidas com sucesso", "success");
    } else if (result.successCount > 0) {
      // Alguns deletados - atualiza contador
      const remainingDups = filesToDelete.length - result.successCount;
      btn.textContent = `🗑️ Excluir Duplicatas (${remainingDups})`;
      showToast(
        `⚠️ ${result.successCount} deletado(s), ${result.failureCount} falha(s)`,
        "warning"
      );
    } else {
      // Nenhum deletado
      showToast(`❌ Erro ao deletar arquivos`, "error");
      btn.textContent = `🗑️ Excluir Duplicatas (${filesToDelete.length})`;
    }
    
    btn.disabled = false;
    
    if (result.failureCount > 0) {
      console.error("[BATCH_DELETE] Falhas:", result.errors);
    }
  });
}

list.addEventListener("click", (event) => {
  const keepBtn = event.target.closest(".btn-keep-one");
  if (keepBtn) {
    const groupId = keepBtn.getAttribute("data-group-id");
    const groupElement = document.getElementById(groupId);
    const filesJson = groupElement ? groupElement.dataset.files : "[]";
    try {
      const files = JSON.parse(filesJson);
      keepOnlyOne(groupId, files, keepBtn);
    } catch {
      showToast("❌ Erro ao processar grupo", "error");
    }
  }
});

if (cancelBtn) {
  cancelBtn.addEventListener("click", () => {
    fetch("/api/cancel_scan", { method: "POST" })
      .then(() => {
        statusText.textContent = "Cancelando...";
      })
      .catch(() => {});
  });
}

const startBtn = document.getElementById("btn-start-scan");
if (startBtn) {
  startBtn.addEventListener("click", () => {
    startBtn.style.display = "none";
    if (cancelBtn) cancelBtn.style.display = "block";
    startBtn.disabled = true;
    startBtn.textContent = "⏳ Iniciando...";
    resetUI();
    startStream();
  });
}

function resetUI() {
  // Limpar lista de grupos
  list.innerHTML = "";
  pendingGroups.length = 0;
  seenGroups.clear();
  groupCount = 0;
  totalWaste = 0;
  
  // Resetar estatísticas
  statTotal.textContent = "0";
  statHashed.textContent = "0";
  statCache.textContent = "0%";
  statGroups.textContent = "0";
  statWaste.textContent = "0 Bytes";
  
  // Esconder modal de confirmação se estiver visível
  const modal = document.getElementById("confirmModal");
  if (modal && !modal.classList.contains("hidden")) {
    modal.classList.add("hidden");
  }
  
  // Atualizar status
  statusText.textContent = "Coletando arquivos...";
  console.log("[INIT] UI resetado");
}



function startStream() {
  const source = new EventSource("/api/scan_stream");

  source.onmessage = (event) => {
    const data = JSON.parse(event.data || "{}") || {};

    if (data.type === "status") {
      if (data.is_scanning) {
        statusText.textContent = "Coletando arquivos...";
      }
      return;
    }

    if (data.type === "progress") {
      if (data.total > 0 || data.current > 0) {
        const percent = data.total > 0 ? Math.round((data.current / data.total) * 100) : 0;
        statusText.textContent = `${data.current} / ${data.total} arquivos (${percent}%)`;
      } else if (data.phase === "scan_done") {
        statusText.textContent = "Coletando arquivos...";
      }
      if (typeof data.files_scanned === "number" && data.files_scanned > 0) {
        statTotal.textContent = data.files_scanned;
      }
      if (typeof data.total_candidates === "number" && data.total_candidates > 0) {
        statHashed.textContent = data.total_candidates;
      }
      // Atualiza estatísticas de cache
      if (typeof data.cache_hits === "number" && typeof data.cache_misses === "number") {
        const total = data.cache_hits + data.cache_misses;
        const cachePercent = total > 0 ? Math.round((data.cache_hits / total) * 100) : 0;
        statCache.textContent = `${cachePercent}%`;
      }
      return;
    }

    if (data.type === "group") {
      pendingGroups.push(data.group);
      groupCount++;
      const waste = data.group.waste || 0;
      totalWaste += waste;
      statGroups.textContent = groupCount;
      statWaste.textContent = formatBytes(totalWaste);
      return;
    }

    if (data.type === "complete") {
      updateSummary(data.summary);
      statusText.textContent = "Concluido";
      source.close();
      // Mostrar o botão de iniciar novamente para permitir nova verificação
      if (startBtn) {
        startBtn.style.display = "block";
        startBtn.disabled = false;
        startBtn.textContent = "▶️ Nova Verificação";
      }
      if (cancelBtn) cancelBtn.style.display = "none";
      showConfirmationModal();
      return;
    }

    if (data.type === "cancelled") {
      statusText.textContent = "Cancelado";
      source.close();
      // Mostrar o botão de iniciar novamente
      if (startBtn) {
        startBtn.style.display = "block";
        startBtn.disabled = false;
        startBtn.textContent = "▶️ Iniciar Verificação";
      }
      if (cancelBtn) cancelBtn.style.display = "none";
      return;
    }

    if (data.type === "error") {
      statusText.textContent = "Erro";
      source.close();
      // Mostrar o botão de iniciar novamente em caso de erro
      if (startBtn) {
        startBtn.style.display = "block";
        startBtn.disabled = false;
        startBtn.textContent = "▶️ Tentar Novamente";
      }
      if (cancelBtn) cancelBtn.style.display = "none";
    }
  };

  source.onerror = () => {
    statusText.textContent = "Conexao instavel. Reabrindo...";
  };
}

function showConfirmationModal() {
  const modal = document.getElementById("confirmModal");
  const modalGroups = document.getElementById("modal-groups");
  const modalWaste = document.getElementById("modal-waste");
  const modalMessage = document.getElementById("modalMessage");
  const confirmBtn = document.getElementById("confirmShowBtn");

  if (pendingGroups.length === 0) {
    modalMessage.textContent = "Nenhuma duplicata encontrada.";
    confirmBtn.textContent = "✅ OK";
  } else {
    modalMessage.textContent = `Foram encontrados ${pendingGroups.length} grupo(s) de arquivos duplicados.`;
    confirmBtn.textContent = "📋 Ver Duplicatas";
  }

  modalGroups.textContent = pendingGroups.length;
  modalWaste.textContent = formatBytes(totalWaste);

  modal.classList.remove("hidden");

  confirmBtn.onclick = () => {
    modal.classList.add("hidden");
    renderAllGroups();
  };
}

function renderAllGroups() {
  if (pendingGroups.length === 0) {
    list.innerHTML = '<div class="empty">✨ Nenhuma duplicata encontrada</div>';
    return;
  }
  pendingGroups.forEach(group => renderGroup(group));
  showToast(`✅ ${pendingGroups.length} grupo(s) carregado(s)`, "success");
}

async function deleteGroupDuplicates(groupIndex) {
    const group = window.allGroups[groupIndex];
    if (!group || !group.files || group.files.length < 2) {
        console.error('Grupo inválido ou sem duplicatas');
        return;
    }

    // Confirmar antes de deletar
    const dupsCount = group.files.length - 1;
    if (!confirm(`⚠️ Deletar ${dupsCount} arquivo(s) duplicado(s)?\n\nEsta ação não pode ser desfeita!`)) {
        return;
    }

    const duplicatesToDelete = group.files.slice(1); // Todos exceto o primeiro (referência)
    let successCount = 0;
    let errorCount = 0;

    console.log(`[DELETE] Iniciando exclusão de ${duplicatesToDelete.length} arquivo(s)`);

    for (const filePath of duplicatesToDelete) {
        try {
            console.log(`[DELETE] Enviando requisição para: ${filePath}`);
            
            const response = await fetch('/api/delete_duplicate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });

            console.log(`[DELETE] Status da resposta: ${response.status}`);
            const result = await response.json();
            console.log(`[DELETE] Resposta do servidor:`, result);

            if (!response.ok) {
                console.error(`[DELETE] Erro ao deletar ${filePath}:`, result);
                errorCount++;
                continue;
            }

            console.log(`[DELETE] ✅ ${filePath} deletado com sucesso`);
            successCount++;

        } catch (error) {
            console.error(`[DELETE] Erro ao processar ${filePath}:`, error);
            errorCount++;
        }
    }

    // Feedback final
    if (successCount > 0) {
        alert(`✅ ${successCount} arquivo(s) deletado(s) com sucesso!`);
        
        if (errorCount === 0) {
            // Remover grupo da lista se todos foram deletados
            window.allGroups.splice(groupIndex, 1);
            renderAllGroups();
        } else {
            alert(`⚠️ ${errorCount} arquivo(s) falharam ao deletar`);
        }
    } else {
        alert(`❌ Nenhum arquivo foi deletado. ${errorCount} erro(s).`);
    }
}
