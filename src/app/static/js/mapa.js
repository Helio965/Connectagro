(function () {
  const container = document.getElementById("mapa-glebas");
  if (!container) {
    return;
  }

  function mostrarMensagem(texto) {
    container.innerHTML = `<p class="mapa-empty">${texto}</p>`;
  }

  if (typeof L === "undefined") {
    mostrarMensagem("Mapa indisponível sem conexão com a biblioteca de mapas.");
    return;
  }

  const url = container.dataset.mapaUrl || "/mapa/dados";
  const mapa = L.map(container).setView([-15.7801, -47.9292], 4);
  const limites = L.latLngBounds([]);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(mapa);

  function escaparHtml(valor) {
    return String(valor || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function textoPopup(gleba) {
    const linhas = [
      `<strong>${escaparHtml(gleba.nome)}</strong>`,
      `Lat: ${Number(gleba.latitude).toFixed(6)}`,
      `Lon: ${Number(gleba.longitude).toFixed(6)}`,
    ];
    if (gleba.area_ha !== null && gleba.area_ha !== undefined) {
      linhas.push(`Área: ${Number(gleba.area_ha).toLocaleString("pt-BR")} ha`);
    }
    if (gleba.tipo_solo) {
      linhas.push(`Solo: ${escaparHtml(gleba.tipo_solo)}`);
    }
    return linhas.join("<br>");
  }

  fetch(url, { headers: { Accept: "application/json" } })
    .then((resposta) => {
      if (!resposta.ok) {
        throw new Error("Falha ao carregar dados do mapa");
      }
      return resposta.json();
    })
    .then((dados) => {
      const glebas = Array.isArray(dados.glebas) ? dados.glebas : [];

      glebas.forEach((gleba) => {
        const latitude = Number(gleba.latitude);
        const longitude = Number(gleba.longitude);
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
          return;
        }

        L.marker([latitude, longitude]).addTo(mapa).bindPopup(textoPopup(gleba));
        limites.extend([latitude, longitude]);

        if (gleba.poligono_geojson) {
          try {
            const camada = L.geoJSON(gleba.poligono_geojson, {
              style: {
                color: "#2e7d32",
                fillColor: "#81c784",
                fillOpacity: 0.18,
                weight: 2,
              },
            }).addTo(mapa);
            const limitesPoligono = camada.getBounds();
            if (limitesPoligono.isValid()) {
              limites.extend(limitesPoligono);
            }
          } catch (erro) {
            // GeoJSON inválido já é filtrado no backend; esta proteção evita quebra visual.
          }
        }
      });

      if (limites.isValid()) {
        mapa.fitBounds(limites, { padding: [24, 24], maxZoom: 16 });
      }
    })
    .catch(() => {
      mostrarMensagem("Não foi possível carregar os dados do mapa.");
    });
}());
