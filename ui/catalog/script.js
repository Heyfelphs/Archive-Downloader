const imageExtensions = ["jpg", "jpeg", "png", "webp", "gif"];
const videoExtensions = ["mp4", "webm", "mov", "mkv"];

function getExtension(name) {
  return name.split(".").pop().toLowerCase();
}

/* =========================
   CATÁLOGO
========================= */

fetch("models_catalog.json")
  .then(res => res.json())
  .then(data => {
    const grid = document.getElementById("catalog");
    if (!grid) return;

    // 🔤 ordenação segura (fallback para modelos antigos)
    const modelsSorted = Object.entries(data.models).sort(
      ([keyA, a], [keyB, b]) => {
        const nameA = a.display_name || keyA.replace(/-/g, " ");
        const nameB = b.display_name || keyB.replace(/-/g, " ");
        return nameA.localeCompare(nameB, "pt-BR");
      }
    );

    modelsSorted.forEach(([modelId, model]) => {
      const card = document.createElement("div");
      card.className = "card";

      card.innerHTML = `
        <div class="thumb-wrapper">
          <img class="thumb">
          <div class="counts">
            <span class="img-wrap">📷 <span class="img-count">0</span></span>
            <span class="video-wrap">🎥 <span class="video-count">0</span></span>
          </div>
        </div>
        <h2>${model.display_name || modelId.replace(/-/g, " ")}</h2>
      `;

      const thumb = card.querySelector(".thumb");
      const imgCountEl = card.querySelector(".img-count");
      const videoCountEl = card.querySelector(".video-count");
      const imgWrap = card.querySelector(".img-wrap");
      const videoWrap = card.querySelector(".video-wrap");

      let imgCount = 0;
      let videoCount = 0;

      fetch(`${model.folder}/files.json`)
        .then(res => res.json())
        .then(payload => {
          const files = payload.files || [];

          files.forEach(file => {
            const ext = getExtension(file.name);
            if (imageExtensions.includes(ext)) imgCount++;
            if (videoExtensions.includes(ext)) videoCount++;
          });

          imgCountEl.textContent = imgCount;
          videoCountEl.textContent = videoCount;

          if (imgCount === 0) imgWrap.style.display = "none";
          if (videoCount === 0) videoWrap.style.display = "none";

          const firstImage = files.find(f =>
            imageExtensions.includes(getExtension(f.name))
          );

          if (firstImage) {
            thumb.src = `${model.folder}/${firstImage.name}`;
          }
        })
        .catch(() => {
          // modelo pode ainda não ter files.json
        });

      card.onclick = () => {
        window.location.href = `model.html?id=${encodeURIComponent(modelId)}`;
      };

      grid.appendChild(card);
    });
  })
  .catch(err => {
    console.error("Erro ao carregar models_catalog.json", err);
  });

/* =========================
   SSE — NOTIFICAÇÃO DE DOWNLOAD
========================= */

let eventSource = null;
let downloadBanner = null;

function createDownloadBanner() {
  if (downloadBanner) return downloadBanner;

  const banner = document.createElement("div");
  banner.id = "download-banner";
  banner.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: #1f1f1f;
    color: #fff;
    padding: 10px;
    text-align: center;
    font-size: 14px;
    z-index: 9999;
    display: none;
  `;
  document.body.appendChild(banner);
  downloadBanner = banner;
  return banner;
}

function startSSE() {
  if (eventSource) return; // evita múltiplas conexões

  const banner = createDownloadBanner();
  eventSource = new EventSource("events");

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.status === "downloading") {
      banner.textContent = `⬇️ Baixando: ${data.model}`;
      banner.style.display = "block";
    }

    if (data.status === "finished") {
      banner.textContent = `✅ Download concluído: ${data.model}`;

      setTimeout(() => {
        banner.style.display = "none";
        eventSource.close();
        eventSource = null;
        location.reload();
      }, 2000);
    }
  };

  eventSource.onerror = (err) => {
    // erro temporário é normal em SSE (rede / keep-alive)
    console.warn("SSE aviso:", err);
  };
}

// inicia SSE automaticamente
startSSE();
