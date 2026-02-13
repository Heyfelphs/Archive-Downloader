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

      grid.appendChild(card);
    });
  })
  .catch(err => {
    console.error("Erro ao carregar a lista de sites", err);
  });
