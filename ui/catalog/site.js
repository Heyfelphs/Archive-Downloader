const params = new URLSearchParams(window.location.search);
const site = params.get("site");

const titleEl = document.getElementById("site-name");
const grid = document.getElementById("catalog");
const manageToggle = document.getElementById("manage-toggle-site");

if (!site) {
  document.body.innerHTML = "<h2>Site nao informado</h2>";
  throw new Error("site ausente");
}

const displayName = site.replace(/-/g, " ");
if (titleEl) {
  titleEl.textContent = `Modelos em ${displayName}`;
}

fetch(`api/models?site=${encodeURIComponent(site)}`)
  .then(res => res.json())
  .then(data => {
    const models = Array.isArray(data.models) ? data.models : [];
    if (models.length === 0) {
      grid.innerHTML = "<p class=\"empty\">Nenhuma modelo encontrada.</p>";
      return;
    }

    const imageObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          const src = img.dataset.src;
          if (src) {
            img.src = src;
            img.removeAttribute('data-src');
            imageObserver.unobserve(img);
          }
        }
      });
    }, { rootMargin: '50px' });

    models.forEach(model => {
      const card = document.createElement("div");
      card.className = "card clickable";

      const modelName = (model.name || "").replace(/-/g, " ");
      const thumbPath = model.thumb ? `/media/${site}/${model.name}/${model.thumb}` : "";
      const imageCount = model.image_count || 0;
      const videoCount = model.video_count || 0;
      
      const imgWrapStyle = imageCount === 0 ? ' style="display: none;"' : '';
      const videoWrapStyle = videoCount === 0 ? ' style="display: none;"' : '';
      
      card.innerHTML = `
        <div class="thumb-wrapper">
          ${thumbPath ? `<img class=\"thumb lazy\" data-src=\"${thumbPath}\">` : `<div class=\"thumb placeholder\">Sem thumbnail</div>`}
          <div class="counts">
            <span class="img-wrap"${imgWrapStyle}>📷 <span class="img-count">${imageCount}</span></span>
            <span class="video-wrap"${videoWrapStyle}>🎥 <span class="video-count">${videoCount}</span></span>
          </div>
        </div>
        <h2>${modelName || "Modelo"}</h2>
        <button class="nav-btn manage-action delete-btn" type="button">Excluir</button>
      `;

      card.onclick = () => {
        window.location.href = `model.html?site=${encodeURIComponent(site)}&model=${encodeURIComponent(model.name || "")}`;
      };

      const deleteBtn = card.querySelector(".delete-btn");
      if (deleteBtn) {
        deleteBtn.addEventListener("click", (event) => {
          event.stopPropagation();
          const confirmed = window.confirm(`Excluir a modelo "${modelName}"?`);
          if (!confirmed) return;
          fetch("/api/delete_model", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ site, model: model.name || "" }),
          })
            .then(res => res.json())
            .then(result => {
              if (result && result.status === "deleted") {
                card.remove();
              }
            })
            .catch(() => {});
        });
      }

      grid.appendChild(card);

      if (thumbPath) {
        const img = card.querySelector('img.lazy');
        if (img) imageObserver.observe(img);
      }
    });
  })
  .catch(err => {
    console.error("Erro ao carregar modelos", err);
  });

if (manageToggle) {
  const toggleContainer = manageToggle.closest(".manage-toggle");
  const checkbox = manageToggle;
  
  if (toggleContainer) {
    toggleContainer.addEventListener("click", () => {
      checkbox.checked = !checkbox.checked;
      document.body.classList.toggle("manage-mode", checkbox.checked);
    });
  }
  
  checkbox.addEventListener("change", () => {
    document.body.classList.toggle("manage-mode", checkbox.checked);
  });
}
