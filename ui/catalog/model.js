const params = new URLSearchParams(window.location.search);
const site = params.get("site");
const model = params.get("model");

if (!site || !model) {
  document.body.innerHTML = "<h2>Modelo nao informado</h2>";
  throw new Error("site/model ausente");
}

const displayModel = model.replace(/-/g, " ");

document.getElementById("model-name").textContent = displayModel;

const imagesGrid = document.getElementById("images");
const videosGrid = document.getElementById("videos");
const imgCountEl = document.getElementById("img-count");
const videoCountEl = document.getElementById("video-count");
const preview = document.getElementById("image-preview");
const previewImg = document.getElementById("preview-img");
const previewVideo = document.getElementById("preview-video");
const previewPrev = document.getElementById("preview-prev");
const previewNext = document.getElementById("preview-next");
const previewClose = document.getElementById("preview-close");
const toggleImages = document.getElementById("toggle-images");
const toggleVideos = document.getElementById("toggle-videos");
const imagesHeader = document.getElementById("images-header");
const videosHeader = document.getElementById("videos-header");
const manageToggle = document.getElementById("manage-toggle-model");

let imageList = [];
let videoList = [];
let currentType = "images";
let currentIndex = 0;

function openPreview(type, index) {
  if (!preview || !previewImg || !previewVideo) return;
  currentType = type;
  currentIndex = index;

  if (type === "videos") {
    const name = videoList[index];
    previewVideo.src = `/media/${site}/${model}/${name}`;
    previewVideo.style.display = "block";
    previewImg.style.display = "none";
    previewVideo.currentTime = 0;
    const playPromise = previewVideo.play();
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise.catch(() => {
        previewVideo.muted = true;
        previewVideo.play().catch(() => {});
      });
    }
  } else {
    const name = imageList[index];
    previewImg.src = `/media/${site}/${model}/${name}`;
    previewImg.style.display = "block";
    previewVideo.style.display = "none";
    previewVideo.pause();
    previewVideo.removeAttribute("src");
    
    // Pré-carregar imagens adjacentes para navegação mais suave
    const preloadAdjacent = (i) => {
      if (i >= 0 && i < imageList.length) {
        const img = new Image();
        img.src = `/media/${site}/${model}/${imageList[i]}`;
      }
    };
    preloadAdjacent(index + 1);
    preloadAdjacent(index - 1);
  }

  preview.classList.remove("hidden");
}

function closePreview() {
  if (!preview || !previewImg || !previewVideo) return;
  previewImg.src = "";
  previewVideo.pause();
  previewVideo.removeAttribute("src");
  preview.classList.add("hidden");
}

function changePreview(step) {
  const list = currentType === "videos" ? videoList : imageList;
  if (list.length === 0) return;
  currentIndex = (currentIndex + step + list.length) % list.length;
  openPreview(currentType, currentIndex);
}

if (preview) {
  preview.addEventListener("click", (event) => {
    if (event.target === preview || event.target.classList.contains("preview-backdrop")) {
      closePreview();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePreview();
    if (event.key === "ArrowLeft") changePreview(-1);
    if (event.key === "ArrowRight") changePreview(1);
  });
}

if (previewPrev) {
  previewPrev.addEventListener("click", () => changePreview(-1));
}
if (previewNext) {
  previewNext.addEventListener("click", () => changePreview(1));
}
if (previewClose) {
  previewClose.addEventListener("click", closePreview);
}

function setSectionToggle(button, grid) {
  if (!button || !grid) return;
  button.addEventListener("click", () => {
    const isHidden = grid.style.display === "none";
    grid.style.display = isHidden ? "grid" : "none";
    button.textContent = isHidden ? "Ocultar" : "Mostrar";
  });
}

setSectionToggle(toggleImages, imagesGrid);
setSectionToggle(toggleVideos, videosGrid);

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

function deleteFile(filename, element) {
  // Usar DeleteManager para gerenciar a exclusão
  const deleteManager = DeleteManager.createFileDelete(
    site,
    model,
    filename,
    element,
    {
      onSuccess: () => {
        // Atualizar arrays
        imageList = imageList.filter(f => f !== filename);
        videoList = videoList.filter(f => f !== filename);
        
        // Atualizar contadores
        imgCountEl.textContent = imageList.length;
        videoCountEl.textContent = videoList.length;
        
        // Esconder seções se vazias
        if (imageList.length === 0) {
          imagesGrid.style.display = "none";
          if (imagesHeader) imagesHeader.style.display = "none";
        }
        if (videoList.length === 0) {
          videosGrid.style.display = "none";
          if (videosHeader) videosHeader.style.display = "none";
        }
      }
    }
  );
  
  deleteManager.execute();
}}

fetch(`api/model?site=${encodeURIComponent(site)}&model=${encodeURIComponent(model)}`)
  .then(res => res.json())
  .then(data => {
    imageList = Array.isArray(data.images) ? data.images : [];
    videoList = Array.isArray(data.videos) ? data.videos : [];

    // IntersectionObserver para lazy loading
    const mediaObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const media = entry.target;
          const src = media.dataset.src;
          if (src) {
            media.src = src;
            media.removeAttribute('data-src');
            mediaObserver.unobserve(media);
          }
        }
      });
    }, { rootMargin: '200px' });

    // Usar DocumentFragment para melhor performance
    const imagesFragment = document.createDocumentFragment();
    
    imageList.forEach((name, index) => {
      const container = document.createElement("div");
      container.className = "thumb-container";
      
      const img = document.createElement("img");
      // Usar lazy loading
      img.dataset.src = `/media/${site}/${model}/${name}`;
      img.className = "thumb";
      img.loading = "lazy";
      img.onclick = () => openPreview("images", index);
      container.appendChild(img);
      
      const deleteBtn = document.createElement("button");
      deleteBtn.className = "nav-btn manage-action delete-file";
      deleteBtn.textContent = "🗑 Excluir";
      deleteBtn.type = "button";
      deleteBtn.onclick = (e) => {
        e.stopPropagation();
        deleteFile(name, container);
      };
      container.appendChild(deleteBtn);
      
      imagesFragment.appendChild(container);
      mediaObserver.observe(img);
    });
    
    imagesGrid.appendChild(imagesFragment);

    // Videos com DocumentFragment
    const videosFragment = document.createDocumentFragment();
    
    videoList.forEach((name, index) => {
      const videoCard = document.createElement("div");
      videoCard.className = "video-thumb";
      
      const video = document.createElement("video");
      // Usar lazy loading
      video.dataset.src = `/media/${site}/${model}/${name}`;
      video.preload = "none";  // Mudado de metadata para none
      video.muted = true;
      video.playsInline = true;
      video.className = "thumb";
      videoCard.appendChild(video);
      
      const playIcon = document.createElement("span");
      playIcon.className = "video-play";
      playIcon.textContent = "▶";
      videoCard.appendChild(playIcon);
      
      const deleteBtn = document.createElement("button");
      deleteBtn.className = "nav-btn manage-action delete-file";
      deleteBtn.textContent = "🗑 Excluir";
      deleteBtn.type = "button";
      deleteBtn.onclick = (e) => {
        e.stopPropagation();
        deleteFile(name, videoCard);
      };
      videoCard.appendChild(deleteBtn);
      
      videoCard.onclick = () => openPreview("videos", index);
      videosFragment.appendChild(videoCard);
      mediaObserver.observe(video);
    });
    
    videosGrid.appendChild(videosFragment);

    imgCountEl.textContent = imageList.length;
    videoCountEl.textContent = videoList.length;

    if (imageList.length === 0) {
      imagesGrid.style.display = "none";
      if (imagesHeader) imagesHeader.style.display = "none";
    }
    if (videoList.length === 0) {
      videosGrid.style.display = "none";
      if (videosHeader) videosHeader.style.display = "none";
    }
  })
  .catch(err => {
    console.error("Erro ao carregar arquivos", err);
    imagesGrid.innerHTML = "<p>Erro ao carregar arquivos</p>";
  });
