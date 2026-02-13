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

// Limpar cache
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

