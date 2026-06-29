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
  const csrfToken = container.dataset.csrfToken || "";
  const canEdit = container.dataset.canEdit === "1";
  // Edição depende do plugin Leaflet.draw; sem ele, o mapa segue como leitura.
  const podeEditar = canEdit && typeof L.Control !== "undefined" && !!L.Control.Draw;

  container.innerHTML = "";
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
    const linhas = [`<strong>${escaparHtml(gleba.nome)}</strong>`];
    if (gleba.latitude !== null && gleba.latitude !== undefined) {
      linhas.push(`Lat: ${Number(gleba.latitude).toFixed(6)}`);
      linhas.push(`Lon: ${Number(gleba.longitude).toFixed(6)}`);
    }
    if (gleba.area_ha !== null && gleba.area_ha !== undefined) {
      linhas.push(`Área: ${Number(gleba.area_ha).toLocaleString("pt-BR")} ha`);
    }
    if (gleba.tipo_solo) {
      linhas.push(`Solo: ${escaparHtml(gleba.tipo_solo)}`);
    }
    return linhas.join("<br>");
  }

  const poligonoEstilo = {
    color: "#2e7d32",
    fillColor: "#81c784",
    fillOpacity: 0.18,
    weight: 2,
  };

  // Registro de glebas e suas camadas de polígono (somente leitura).
  const glebasPorId = {};
  const poligonoLayers = {};

  function desenharPoligono(gleba) {
    if (!gleba.poligono_geojson) {
      return;
    }
    try {
      const camada = L.geoJSON(gleba.poligono_geojson, { style: poligonoEstilo }).addTo(mapa);
      poligonoLayers[gleba.id] = camada;
      const b = camada.getBounds();
      if (b.isValid()) {
        limites.extend(b);
      }
    } catch (erro) {
      // GeoJSON inválido já é filtrado no backend.
    }
  }

  // ---- Edição (Leaflet.draw) ----------------------------------------------
  const status = document.getElementById("mapa-status");
  const select = document.getElementById("mapa-gleba-select");
  let drawnItems = null;
  let glebaAtivaId = null;

  function definirStatus(texto, tipo) {
    if (!status) {
      return;
    }
    status.textContent = texto || "";
    status.className = "mapa-status" + (tipo ? " mapa-status-" + tipo : "");
  }

  function limparDrawn() {
    if (drawnItems) {
      drawnItems.clearLayers();
    }
  }

  function carregarPoligonoParaEdicao(gleba) {
    limparDrawn();
    if (!gleba || !gleba.poligono_geojson) {
      return;
    }
    try {
      L.geoJSON(gleba.poligono_geojson).eachLayer((layer) => {
        if (layer.getLatLngs) {
          drawnItems.addLayer(L.polygon(layer.getLatLngs(), poligonoEstilo));
        }
      });
      const b = drawnItems.getBounds();
      if (b.isValid()) {
        mapa.fitBounds(b, { padding: [24, 24], maxZoom: 16 });
      }
    } catch (erro) {
      definirStatus("Não foi possível carregar o polígono atual.", "erro");
    }
  }

  function selecionarGleba(id) {
    glebaAtivaId = id ? Number(id) : null;
    const gleba = glebasPorId[glebaAtivaId];
    // Esconde o polígono somente-leitura da gleba ativa para não duplicar.
    Object.keys(poligonoLayers).forEach((gid) => {
      const visivel = Number(gid) !== glebaAtivaId;
      if (visivel) {
        poligonoLayers[gid].addTo(mapa);
      } else {
        mapa.removeLayer(poligonoLayers[gid]);
      }
    });
    carregarPoligonoParaEdicao(gleba);
    definirStatus(gleba ? `Editando: ${gleba.nome}` : "");
  }

  function geojsonDoDesenho() {
    if (!drawnItems) {
      return null;
    }
    const layers = drawnItems.getLayers();
    if (!layers.length) {
      return null;
    }
    // Apenas um polígono por gleba: usa a última camada desenhada.
    return layers[layers.length - 1].toGeoJSON();
  }

  function enviarPoligono(urlPost, corpo, sucessoMsg) {
    if (!glebaAtivaId) {
      definirStatus("Selecione uma gleba primeiro.", "erro");
      return;
    }
    fetch(urlPost, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
        Accept: "application/json",
      },
      body: corpo === null ? "{}" : JSON.stringify(corpo),
    })
      .then((resp) => resp.json().then((data) => ({ ok: resp.ok, data })))
      .then(({ ok, data }) => {
        if (!ok || !data.ok) {
          definirStatus((data && data.error) || "Erro ao salvar polígono.", "erro");
          return;
        }
        const gleba = data.gleba;
        glebasPorId[gleba.id] = gleba;
        if (poligonoLayers[gleba.id]) {
          mapa.removeLayer(poligonoLayers[gleba.id]);
          delete poligonoLayers[gleba.id];
        }
        definirStatus(sucessoMsg, "ok");
      })
      .catch(() => definirStatus("Falha de comunicação ao salvar polígono.", "erro"));
  }

  function configurarEdicao() {
    drawnItems = new L.FeatureGroup();
    mapa.addLayer(drawnItems);

    const desenho = new L.Control.Draw({
      edit: { featureGroup: drawnItems, remove: true },
      draw: {
        polygon: { allowIntersection: false, showArea: false },
        polyline: false, rectangle: false, circle: false,
        marker: false, circlemarker: false,
      },
    });
    mapa.addControl(desenho);

    mapa.on(L.Draw.Event.CREATED, (evento) => {
      limparDrawn();
      drawnItems.addLayer(evento.layer);
      definirStatus("Polígono desenhado. Clique em Salvar.", "ok");
    });

    if (select) {
      select.addEventListener("change", (e) => selecionarGleba(e.target.value));
    }
    const btnSalvar = document.getElementById("mapa-salvar");
    const btnLimpar = document.getElementById("mapa-limpar");
    if (btnSalvar) {
      btnSalvar.addEventListener("click", () => {
        const geojson = geojsonDoDesenho();
        if (!geojson) {
          definirStatus("Desenhe um polígono antes de salvar.", "erro");
          return;
        }
        enviarPoligono(`/mapa/glebas/${glebaAtivaId}/poligono`, geojson,
          "Polígono salvo com sucesso.");
      });
    }
    if (btnLimpar) {
      btnLimpar.addEventListener("click", () => {
        limparDrawn();
        enviarPoligono(`/mapa/glebas/${glebaAtivaId}/poligono/limpar`, null,
          "Polígono removido com sucesso.");
      });
    }
  }

  function popularSelect(glebas) {
    if (!select) {
      return;
    }
    select.innerHTML = '<option value="">Selecione uma gleba…</option>';
    glebas.forEach((gleba) => {
      const opt = document.createElement("option");
      opt.value = gleba.id;
      opt.textContent = gleba.nome;
      select.appendChild(opt);
    });
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
        glebasPorId[gleba.id] = gleba;
        const latitude = Number(gleba.latitude);
        const longitude = Number(gleba.longitude);
        if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
          L.marker([latitude, longitude]).addTo(mapa).bindPopup(textoPopup(gleba));
          limites.extend([latitude, longitude]);
        }
        desenharPoligono(gleba);
      });

      if (podeEditar) {
        configurarEdicao();
        popularSelect(glebas);
      }

      if (limites.isValid()) {
        mapa.fitBounds(limites, { padding: [24, 24], maxZoom: 16 });
      }
    })
    .catch(() => {
      mostrarMensagem("Não foi possível carregar os dados do mapa.");
    });
}());
