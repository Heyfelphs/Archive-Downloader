const params = new URLSearchParams(window.location.search);
const modelId = params.get("id");

if (!modelId) {
  document.body.innerHTML = "<h2>Modelo não informado</h2>";
  throw new Error("modelId ausente");
}

const imageExtensions = ["jpg", "jpeg", "png", "webp", "gif"];
const videoExtensions = ["mp4", "webm", "mov", "mkv"];

function getExtension(name) {
  return name.split(".").pop().toLowerCase();
}

fetch("models_catalog.json")
  .then(res => res.json())
  .then(data => {
    const model = data.models[modelId];

    if (!model) {
      document.body.innerHTML = "<h2>Modelo não encontrado</h2>";
      return;
    }

    // nome da modelo (vem pronto do backend)
    document.getElementById("model-name").textContent = model.display_name;

    // link do perfil (se existir)
    document.getElementById("model-info").innerHTML = model.profile_url
      ? `🔗 <a href="${model.profile_url}" target="_blank">Perfil original</a>`
      : "";

    const imagesGrid = document.getElementById("images");
    const videosGrid = document.getElementById("videos");

    const imgCountEl = document.getElementById("img-count");
    const videoCountEl = document.getElementById("video-count");

    let images = [];
    let videos = [];

    fetch(`${model.folder}/files.json`)
      .then(res => res.json())
      .then(payload => {
        const files = payload.files || [];

        files.forEach(file => {
          const ext = getExtension(file.name);
          if (imageExtensions.includes(ext)) images.push(file);
          else if (videoExtensions.includes(ext)) videos.push(file);
        });

        // 🔤 ordenação alfabética
        images.sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
        videos.sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));

        // imagens
        images.forEach(file => {
          const img = document.createElement("img");
          img.src = `${model.folder}/${file.name}`;
          img.className = "thumb";
          img.onclick = () => window.open(img.src, "_blank");
          imagesGrid.appendChild(img);
        });

        // vídeos
        videos.forEach(file => {
          const video = document.createElement("video");
          video.src = `${model.folder}/${file.name}`;
          video.controls = true;
          video.className = "thumb";
          videosGrid.appendChild(video);
        });

        // contadores
        imgCountEl.textContent = images.length;
        videoCountEl.textContent = videos.length;

        // esconder se vazio
        if (images.length === 0) imagesGrid.style.display = "none";
        if (videos.length === 0) videosGrid.style.display = "none";
      })
      .catch(err => {
        console.error("Erro ao carregar files.json", err);
        imagesGrid.innerHTML = "<p>Erro ao carregar arquivos</p>";
      });
  })
  .catch(err => {
    console.error("Erro ao carregar models_catalog.json", err);
  });
