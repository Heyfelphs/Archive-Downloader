// Função para mostrar toast
function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast ${type}`;
  
  // Mostrar toast
  setTimeout(() => toast.classList.add('show'), 10);
  
  // Esconder após 3 segundos
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

fetch("api/sites")
  .then(res => res.json())
  .then(data => {
    const grid = document.getElementById("catalog");
    if (!grid) return;

    const sites = Array.isArray(data.sites) ? data.sites : [];
    if (sites.length === 0) {
      grid.innerHTML = "<p class=\"empty\">Nenhuma pasta de site encontrada.</p>";
      return;
    }

    // Usar DocumentFragment para melhor performance
    const fragment = document.createDocumentFragment();

    sites.forEach(site => {
      const card = document.createElement("div");
      card.className = "card clickable";

      const displayName = site.name.replace(/-/g, " ");
      const modelsCount = Number(site.models || 0);

      card.innerHTML = `
        <div class="site-icon">🗂️</div>
        <h2>${displayName}</h2>
        <div class="meta">Modelos: ${modelsCount}</div>
        <div class="footer">/${site.name}</div>
      `;

      card.onclick = () => {
        window.location.href = `site.html?site=${encodeURIComponent(site.name)}`;
      };

      fragment.appendChild(card);
    });
    
    grid.appendChild(fragment);
  })
  .catch(err => {
    console.error("Erro ao carregar a lista de sites", err);
  });

// Funções para verificação de duplicatas
let progressInterval = null;

function scanDuplicates() {
  const modal = document.getElementById("duplicatesModal");
  const body = document.getElementById("duplicatesBody");
  
  modal.style.display = "flex";
  body.innerHTML = '<div class="loading">🔍 Verificando arquivos...<br><div id="progressText" class="progress-text">Iniciando...</div></div>';
  
  // Iniciar o scan
  fetch("/api/scan_duplicates")
    .then(res => res.json())
    .then(data => {
      console.log("Scan started:", data); // Debug
      if (data.error) {
        stopProgressPolling();
        body.innerHTML = `<div class="error">❌ Erro: ${data.error}</div>`;
        return;
      }
      
      // Scan iniciado, começar polling
      startProgressPolling(body);
    })
    .catch(err => {
      stopProgressPolling();
      body.innerHTML = '<div class="error">❌ Erro ao verificar duplicatas</div>';
      console.error("Erro:", err);
    });
}

function startProgressPolling(body) {
  progressInterval = setInterval(() => {
    fetch("/api/scan_progress")
      .then(res => res.json())
      .then(data => {
        console.log("Progress data:", data); // Debug
        const progressText = document.getElementById("progressText");
        
        // Atualizar progresso se ainda está escaneando
        if (progressText) {
          if (data.is_scanning) {
            const percent = data.total > 0 ? Math.round((data.current / data.total) * 100) : 0;
            progressText.innerHTML = `${data.current} / ${data.total} arquivos (${percent}%)`;
          } else if (data.completed) {
            progressText.innerHTML = 'Finalizando...';
          }
        }
        
        // Se o scan terminou, exibir resultados
        if (data.completed && data.results) {
          stopProgressPolling();
          displayDuplicates(data.results);
        }
      })
      .catch(err => console.error("Erro ao obter progresso:", err));
  }, 500); // Atualiza a cada 500ms
}

function stopProgressPolling() {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
}

function displayDuplicates(data) {
  const body = document.getElementById("duplicatesBody");
  
  if (data.error) {
    body.innerHTML = `<div class="error">❌ Erro: ${data.error}</div>`;
    return;
  }
  
  const totalFiles = data.total_files || 0;
  const groupCount = data.duplicate_groups || 0;
  const totalWaste = data.total_waste_bytes || 0;
  const duplicates = data.duplicates || [];
  
  let html = `
    <div class="duplicates-summary">
      <div class="summary-item">
        <div class="summary-label">📁 Arquivos Verificados</div>
        <div class="summary-value">${totalFiles}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">🔄 Grupos de Duplicatas</div>
        <div class="summary-value">${groupCount}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">💾 Espaço Desperdiçado</div>
        <div class="summary-value">${formatBytes(totalWaste)}</div>
      </div>
  `;
  
  // Adicionar estatísticas de cache se disponíveis
  if (data.cache_stats) {
    const cacheStats = data.cache_stats;
    html += `
      <div class="summary-item cache-stat">
        <div class="summary-label">⚡ Cache Hit Rate</div>
        <div class="summary-value cache-value">${cacheStats.hit_rate}%</div>
        <div class="cache-detail">${cacheStats.hits} hits / ${cacheStats.misses} misses</div>
      </div>
    `;
  }
  
  html += `
    </div>
  `;
  
  if (duplicates.length === 0) {
    html += '<div class="no-duplicates">✅ Nenhuma duplicata encontrada!</div>';
  } else {
    html += '<div class="duplicates-list">';
    duplicates.forEach((dup, idx) => {
      const groupId = `group-${idx}`;
      html += `
        <div class="duplicate-group" id="${groupId}" data-files='${JSON.stringify(dup.files)}'>
          <div class="duplicate-header">
            <div>
              <strong>Grupo ${idx + 1}</strong> - ${dup.count} cópias - ${formatBytes(dup.size)} cada
              <span class="waste-badge">-${formatBytes(dup.waste)}</span>
            </div>
            <button class="btn-keep-one" data-group-id="${groupId}">
              🗑️ Manter apenas 1
            </button>
          </div>
          <div class="duplicate-files">
            ${dup.files.map((f, fileIdx) => {
              const mediaUrl = `/media/${f.replace(/\\/g, '/')}`;
              const isVideo = /\.(mp4|avi|mov|mkv|flv|wmv|m4v)$/i.test(f);
              const fileId = `file-${idx}-${fileIdx}`;
              return `
                <div class="file-item" id="${fileId}" data-file-path="${f}">
                  <div class="file-thumbnail">
                    ${isVideo ? 
                      `<video src="${mediaUrl}" class="dup-thumb"></video>` :
                      `<img src="${mediaUrl}" class="dup-thumb" loading="lazy">`
                    }
                  </div>
                  <div class="file-info">
                    <div class="file-path">📄 ${f}</div>
                    <button class="btn-delete-file" data-file-id="${fileId}">
                      ❌ Deletar
                    </button>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    });
    html += '</div>';
  }
  
  body.innerHTML = html;
  
  // Adicionar event listeners para os botões de delete individual
  document.querySelectorAll('.btn-delete-file').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      const fileId = this.getAttribute('data-file-id');
      const fileElement = document.getElementById(fileId);
      const filePath = fileElement ? fileElement.getAttribute('data-file-path') : '';
      
      if (fileId && filePath) {
        // Se não está em modo de confirmação, ativar modo
        if (!this.classList.contains('confirm-mode')) {
          this.classList.add('confirm-mode');
          this.textContent = '✓ Confirmar?';
          
          // Remover outros botões de confirmação
          document.querySelectorAll('.btn-delete-file.confirm-mode').forEach(other => {
            if (other !== this) {
              other.classList.remove('confirm-mode');
              other.textContent = '❌ Deletar';
            }
          });
          
          // Auto-cancelar após 3 segundos
          setTimeout(() => {
            if (this.classList.contains('confirm-mode')) {
              this.classList.remove('confirm-mode');
              this.textContent = '❌ Deletar';
            }
          }, 3000);
        } else {
          // Executar delete
          deleteDuplicateFile(fileId, filePath, this);
        }
      }
    });
  });
  
  // Adicionar event listeners para os botões "Manter apenas 1"
  document.querySelectorAll('.btn-keep-one').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      const groupId = this.getAttribute('data-group-id');
      const groupElement = document.getElementById(groupId);
      const filesJson = groupElement ? groupElement.getAttribute('data-files') : '[]';
      
      try {
        const files = JSON.parse(filesJson);
        if (groupId && files.length > 0) {
          // Se não está em modo de confirmação, ativar modo
          if (!this.classList.contains('confirm-mode')) {
            const count = files.length - 1;
            this.classList.add('confirm-mode');
            this.textContent = `✓ Deletar ${count}?`;
            
            // Remover outros botões de confirmação
            document.querySelectorAll('.btn-keep-one.confirm-mode').forEach(other => {
              if (other !== this) {
                other.classList.remove('confirm-mode');
                other.textContent = '🗑️ Manter apenas 1';
              }
            });
            
            // Auto-cancelar após 4 segundos
            setTimeout(() => {
              if (this.classList.contains('confirm-mode')) {
                this.classList.remove('confirm-mode');
                this.textContent = '🗑️ Manter apenas 1';
              }
            }, 4000);
          } else {
            // Executar delete
            keepOnlyOne(groupId, files, this);
          }
        }
      } catch (e) {
        console.error('Erro ao parsear arquivos do grupo:', e);
      }
    });
  });
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function closeDuplicatesModal() {
  document.getElementById("duplicatesModal").style.display = "none";
}

// Deletar arquivo duplicado individual
function deleteDuplicateFile(fileId, filePath, btn) {
  console.log("Deleting file:", filePath); // Debug
  btn.disabled = true;
  btn.textContent = '⏳ Deletando...';
  btn.classList.add('deleting');
  
  fetch("/api/delete_duplicate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: filePath })
  })
  .then(res => {
    console.log("Delete response status:", res.status); // Debug
    return res.json();
  })
  .then(data => {
    console.log("Delete response data:", data); // Debug
    if (data.status === "deleted") {
      // Remover o elemento da UI
      const fileElement = document.getElementById(fileId);
      if (fileElement) {
        // Pegar referência ao grupo antes de remover o elemento
        const groupElement = fileElement.closest('.duplicate-group');
        
        // Verificar quantos arquivos vão restar ANTES de remover
        if (groupElement) {
          const currentFiles = groupElement.querySelectorAll('.file-item');
          const willRemainAfterDelete = currentFiles.length - 1;
          
          // Aplicar animação de saída
          fileElement.style.opacity = "0";
          fileElement.style.transform = "translateX(-20px)";
          fileElement.style.transition = "all 0.3s ease";
          
          setTimeout(() => {
            fileElement.remove();
            
            // Se ficou com 1 ou menos arquivos, remover o grupo inteiro
            if (willRemainAfterDelete <= 1) {
              groupElement.style.opacity = "0";
              groupElement.style.transform = "scale(0.95)";
              groupElement.style.transition = "all 0.3s ease";
              setTimeout(() => {
                groupElement.remove();
                showToast("✅ Arquivo deletado! Grupo removido (sem duplicatas)", "success");
              }, 300);
            } else {
              showToast("✅ Arquivo deletado com sucesso!", "success");
            }
          }, 300);
        } else {
          // Se não encontrou o grupo, só remove o elemento
          fileElement.style.opacity = "0";
          setTimeout(() => {
            fileElement.remove();
            showToast("✅ Arquivo deletado com sucesso!", "success");
          }, 300);
        }
      } else {
        showToast("✅ Arquivo deletado com sucesso!", "success");
      }
    } else {
      btn.disabled = false;
      btn.classList.remove('confirm-mode', 'deleting');
      btn.textContent = '❌ Deletar';
      showToast("❌ Erro ao deletar arquivo: " + (data.error || "desconhecido"), "error");
    }
  })
  .catch(err => {
    console.error("Erro:", err);
    btn.disabled = false;
    btn.classList.remove('confirm-mode', 'deleting');
    btn.textContent = '❌ Deletar';
    showToast("❌ Erro ao deletar arquivo", "error");
  });
}

// Manter apenas 1 arquivo do grupo (deletar todos os outros)
function keepOnlyOne(groupId, files, btn) {
  console.log("Keeping only one, deleting:", files.slice(1)); // Debug
  btn.disabled = true;
  btn.textContent = '⏳ Deletando...';
  btn.classList.add('deleting');
  
  // Deletar todos exceto o primeiro
  const filesToDelete = files.slice(1);
  let deletedCount = 0;
  let failedCount = 0;
  
  const deletePromises = filesToDelete.map(filePath => 
    fetch("/api/delete_duplicate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: filePath })
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === "deleted") {
        deletedCount++;
      } else {
        failedCount++;
      }
    })
    .catch(() => {
      failedCount++;
    })
  );
  
  Promise.all(deletePromises).then(() => {
    if (deletedCount > 0) {
      // Remover o grupo da UI
      const groupElement = document.getElementById(groupId);
      if (groupElement) {
        groupElement.style.opacity = "0";
        groupElement.style.transform = "scale(0.95)";
        groupElement.style.transition = "all 0.4s ease";
        setTimeout(() => {
          groupElement.remove();
          showToast(`✅ ${deletedCount} arquivo${deletedCount > 1 ? 's' : ''} deletado${deletedCount > 1 ? 's' : ''}${failedCount > 0 ? `, ${failedCount} falha${failedCount > 1 ? 's' : ''}` : ''}`, failedCount > 0 ? "error" : "success");
        }, 400);
      } else {
        showToast(`✅ ${deletedCount} arquivo${deletedCount > 1 ? 's' : ''} deletado${deletedCount > 1 ? 's' : ''}${failedCount > 0 ? `, ${failedCount} falha${failedCount > 1 ? 's' : ''}` : ''}`, failedCount > 0 ? "error" : "success");
      }
    } else {
      btn.disabled = false;
      btn.classList.remove('confirm-mode', 'deleting');
      btn.textContent = '🗑️ Manter apenas 1';
      showToast(`❌ Falha ao deletar arquivos: ${failedCount} falha${failedCount > 1 ? 's' : ''}`, "error");
    }
  });
}

// Limpar cache de hashes
let clearCacheConfirm = false;
function clearCache() {
  const btn = event.target;
  
  if (!clearCacheConfirm) {
    btn.textContent = '✓ Confirmar limpeza?';
    btn.style.background = '#ff6b6b';
    clearCacheConfirm = true;
    
    setTimeout(() => {
      if (clearCacheConfirm) {
        btn.textContent = '🗑️ Limpar Cache';
        btn.style.background = '';
        clearCacheConfirm = false;
      }
    }, 3000);
    return;
  }
  
  btn.disabled = true;
  btn.textContent = '⏳ Limpando...';
  clearCacheConfirm = false;
  
  fetch("api/clear_cache")
    .then(res => res.json())
    .then(data => {
      if (data.status === "cleared" || data.status === "empty") {
        showToast(`✅ ${data.message}`, "success");
      } else {
        showToast(`❌ Erro: ${data.error || data.message}`, "error");
      }
    })
    .catch(err => {
      console.error("Erro:", err);
      showToast("❌ Erro ao limpar cache", "error");
    });
}

// Fechar modal ao clicar fora
window.onclick = function(event) {
  const modal = document.getElementById("duplicatesModal");
  if (event.target === modal) {
    closeDuplicatesModal();
  }
  
  // Cancelar botões em modo confirmação ao clicar fora
  if (!event.target.closest('.btn-delete-file') && !event.target.closest('.btn-keep-one')) {
    document.querySelectorAll('.btn-delete-file.confirm-mode').forEach(btn => {
      btn.classList.remove('confirm-mode');
      btn.textContent = '❌ Deletar';
    });
    document.querySelectorAll('.btn-keep-one.confirm-mode').forEach(btn => {
      btn.classList.remove('confirm-mode');
      btn.textContent = '🗑️ Manter apenas 1';
    });
  }
}
