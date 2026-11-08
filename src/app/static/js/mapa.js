(function () {
  "use strict";
  const container = document.getElementById("mapa-glebas");
  if (!container) return;
  const status = document.getElementById("mapa-status");
  const aviso = document.getElementById("mapa-disponibilidade");
  const tituloEdicao = document.getElementById("mapa-em-edicao");
  const avisoLegado = document.getElementById("mapa-legado");
  const tipoSelect = document.getElementById("mapa-entidade-tipo");
  const areaSelect = document.getElementById("mapa-gleba-select");
  const areaCampo = document.getElementById("mapa-area-campo");
  const btnSalvar = document.getElementById("mapa-salvar");
  const btnLimpar = document.getElementById("mapa-limpar");
  const canEdit = container.dataset.canEdit === "1";
  const propriedadeId = Number(container.dataset.propriedadeId);
  const csrfToken = container.dataset.csrfToken || "";
  const url = container.dataset.mapaUrl;
  const baseUrl = new URL(url, window.location.href).pathname.replace(/\/dados\/?$/, "");
  const entidades = new Map();
  const camadas = new Map();
  const contextosDesabilitados = new Map();
  let chaveAtiva = null;
  let dirty = false;
  let busy = false;
  let carregado = false;
  let modoAtivo = false;
  let saidaConfirmada = false;
  let editorDisponivel = false;
  let mapa = null;
  let drawnItems = null;
  let controleDesenho = null;
  let grupoPropriedade = null;
  let grupoAreas = null;
  let desenhoConfirmado = "null";
  const estiloPropriedade = { color: "#d4a94f", fillColor: "#d4a94f", fillOpacity: 0.05, weight: 3, dashArray: "9 6" };
  const estiloArea = { color: "#2e7d32", fillColor: "#81c784", fillOpacity: 0.23, weight: 2 };

  function clonar(valor) { return JSON.parse(JSON.stringify(valor)); }
  function chave(tipo, id) { return tipo + ":" + id; }
  function entidadeAtual() { return entidades.get(chaveAtiva); }
  function descricao(entidade) {
    return (entidade.tipo === "propriedade" ? "Propriedade: " : "Área de Plantio: ") + entidade.dados.nome;
  }
  function estilo(entidade) { return entidade.tipo === "propriedade" ? estiloPropriedade : estiloArea; }
  function definirStatus(texto, tipo) {
    if (!status) return;
    status.textContent = texto || "";
    status.className = "mapa-status" + (tipo ? " mapa-status-" + tipo : "");
  }
  function disponibilidade(texto) {
    if (!aviso) return;
    aviso.textContent = texto || "";
    aviso.hidden = !texto;
  }
  function formulariosDeContexto() {
    return Array.from(document.forms).filter((form) => new URL(form.action, window.location.href).pathname.endsWith("/propriedades/selecionar"));
  }
  function restaurarContextoVisual() {
    formulariosDeContexto().forEach((form) => {
      const select = form.querySelector('select[name="propriedade_id"]');
      if (select) select.value = String(propriedadeId);
    });
  }
  function atualizarControles() {
    const bloqueado = !carregado || !editorDisponivel || busy || modoAtivo;
    if (tipoSelect) tipoSelect.disabled = bloqueado;
    if (areaSelect) areaSelect.disabled = bloqueado || !entidadeAtual() || entidadeAtual().tipo !== "gleba";
    if (btnSalvar) btnSalvar.disabled = bloqueado || !chaveAtiva;
    if (btnLimpar) btnLimpar.disabled = bloqueado || !chaveAtiva;
    container.setAttribute("aria-busy", busy ? "true" : "false");
    if (controleDesenho) {
      const ferramentas = controleDesenho.getContainer();
      const indisponivel = busy || !chaveAtiva || !carregado;
      ferramentas.inert = indisponivel;
      ferramentas.classList.toggle("mapa-editor-bloqueado", indisponivel);
      ferramentas.setAttribute("aria-disabled", indisponivel ? "true" : "false");
      ferramentas.querySelectorAll("a").forEach((a) => { a.tabIndex = indisponivel ? -1 : 0; });
    }
    formulariosDeContexto().forEach((form) => {
      form.querySelectorAll("select, button").forEach((controle) => {
        if (busy || modoAtivo) {
          if (!contextosDesabilitados.has(controle)) contextosDesabilitados.set(controle, controle.disabled);
          controle.disabled = true;
        } else if (contextosDesabilitados.has(controle)) {
          controle.disabled = contextosDesabilitados.get(controle);
          contextosDesabilitados.delete(controle);
        }
      });
    });
  }
  function erroDeBiblioteca(texto) {
    disponibilidade(texto + " As informações textuais continuam disponíveis abaixo.");
    container.replaceChildren();
    const mensagem = document.createElement("p");
    mensagem.className = "mapa-empty";
    mensagem.textContent = "Visualização do mapa indisponível.";
    container.appendChild(mensagem);
    if (tituloEdicao) tituloEdicao.textContent = "Editor indisponível";
    atualizarControles();
  }

  // A navegação não pode descartar silenciosamente uma edição local.
  formulariosDeContexto().forEach((form) => {
    form.addEventListener("submit", (evento) => {
      if (busy || modoAtivo) {
        evento.preventDefault();
        restaurarContextoVisual();
        definirStatus("Conclua a edição ou aguarde o salvamento antes de trocar a Propriedade.", "erro");
      } else if (dirty) {
        if (!window.confirm("Há alterações não salvas no mapa. Descartá-las e trocar a Propriedade?")) {
          evento.preventDefault();
          restaurarContextoVisual();
        } else saidaConfirmada = true;
      }
    }, true);
  });
  window.addEventListener("beforeunload", (evento) => {
    if (!saidaConfirmada && (dirty || busy || modoAtivo)) {
      evento.preventDefault();
      evento.returnValue = "";
    }
  });

  if (typeof L === "undefined") {
    erroDeBiblioteca("Não foi possível carregar a biblioteca local de mapas.");
    return;
  }
  editorDisponivel = canEdit && !!(L.Control && L.Control.Draw);
  mapa = L.map(container).setView([-15.7801, -47.9292], 4);
  grupoPropriedade = L.featureGroup().addTo(mapa);
  grupoAreas = L.featureGroup().addTo(mapa);
  L.control.layers(null, { "Contorno da Propriedade": grupoPropriedade, "Áreas de Plantio": grupoAreas }).addTo(mapa);
  const base = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "&copy; OpenStreetMap contributors",
  }).addTo(mapa);
  base.on("tileerror", () => disponibilidade("A imagem de fundo está indisponível. As delimitações e informações textuais continuam disponíveis."));
  if (canEdit && !editorDisponivel) {
    disponibilidade("O editor de desenhos está indisponível. Você pode consultar as delimitações e as informações textuais.");
    if (tituloEdicao) tituloEdicao.textContent = "Editor indisponível: a biblioteca de desenho não foi carregada";
  }
  window.addEventListener("resize", () => mapa.invalidateSize());

  function textoPopup(entidade) {
    const bloco = document.createElement("div");
    const nome = document.createElement("strong");
    nome.textContent = descricao(entidade);
    bloco.appendChild(nome);
    const area = entidade.tipo === "propriedade" ? entidade.dados.area_total_ha : entidade.dados.area_ha;
    if (typeof area === "number" && Number.isFinite(area)) {
      const linha = document.createElement("div");
      linha.textContent = "Área informada: " + area.toLocaleString("pt-BR") + " ha";
      bloco.appendChild(linha);
    }
    return bloco;
  }
  function atualizarTexto(entidade) {
    const linha = document.querySelector('[data-mapa-entidade="' + chave(entidade.tipo, entidade.dados.id) + '"]');
    if (!linha) return;
    const estado = linha.querySelector("[data-mapa-poligono-estado]");
    if (estado) estado.textContent = entidade.dados.poligono_estado === "invalido"
      ? "Delimitação antiga inválida: preservada no cadastro e não exibida."
      : entidade.dados.poligono_geojson ? "Polígono cadastrado" : "Sem polígono cadastrado";
    const contencao = linha.querySelector("[data-mapa-contencao]");
    if (contencao && entidade.dados.contencao) {
      contencao.textContent = entidade.dados.contencao.mensagem;
      contencao.classList.toggle("mapa-contencao-aviso", entidade.dados.contencao.status === "fora_do_limite");
    }
  }
  function reconstruirCamada(entidade) {
    const id = chave(entidade.tipo, entidade.dados.id);
    const grupo = entidade.tipo === "propriedade" ? grupoPropriedade : grupoAreas;
    if (camadas.has(id)) {
      grupo.removeLayer(camadas.get(id));
      camadas.delete(id);
    }
    if (entidade.dados.poligono_geojson) {
      const camada = L.geoJSON(entidade.dados.poligono_geojson, { style: estilo(entidade) });
      camada.bindPopup(textoPopup(entidade));
      camadas.set(id, camada);
      if (!editorDisponivel || id !== chaveAtiva) grupo.addLayer(camada);
    }
    atualizarTexto(entidade);
  }
  function registrarEntidade(tipo, dados) {
    if (!dados || !Number.isSafeInteger(dados.id) || dados.id < 1 || typeof dados.nome !== "string") throw new Error("Resposta de mapa inválida.");
    const entidade = { tipo: tipo, dados: dados };
    entidades.set(chave(tipo, dados.id), entidade);
    reconstruirCamada(entidade);
  }

  // Draw edita Polygons: decompor multigeometrias sem perder partes ou furos.
  function partesDoGeojson(geojson) {
    if (!geojson) return [];
    if (geojson.type === "Feature") return partesDoGeojson(geojson.geometry);
    if (geojson.type === "FeatureCollection") return geojson.features.flatMap(partesDoGeojson);
    if (geojson.type === "Polygon") return [geojson.coordinates];
    if (geojson.type === "MultiPolygon") return geojson.coordinates;
    return [];
  }
  function geometriaDoDesenho() {
    const partes = [];
    if (drawnItems) drawnItems.eachLayer((layer) => partes.push(...partesDoGeojson(layer.toGeoJSON(false))));
    if (!partes.length) return null;
    return partes.length === 1 ? { type: "Polygon", coordinates: partes[0] } : { type: "MultiPolygon", coordinates: partes };
  }
  function payloadDoDesenho() {
    const geometria = geometriaDoDesenho();
    const original = entidadeAtual().dados.poligono_geojson;
    if (geometria && original && original.type === "Feature") {
      const feature = clonar(original);
      feature.geometry = geometria;
      // bbox refere-se à geometria anterior; não enviar extensão desatualizada.
      delete feature.bbox;
      return feature;
    }
    return geometria;
  }
  function atualizarDirty() {
    dirty = JSON.stringify(geometriaDoDesenho()) !== desenhoConfirmado;
    saidaConfirmada = false;
  }
  function carregarDesenho(entidade) {
    drawnItems.clearLayers();
    partesDoGeojson(entidade.dados.poligono_geojson).forEach((coordenadas) => {
      L.geoJSON({ type: "Polygon", coordinates: coordenadas }, { style: estilo(entidade) })
        .eachLayer((layer) => drawnItems.addLayer(layer));
    });
    desenhoConfirmado = JSON.stringify(geometriaDoDesenho());
    dirty = false;
    saidaConfirmada = false;
    if (avisoLegado) {
      const original = entidade.dados.poligono_geojson;
      avisoLegado.hidden = !original || original.type !== "FeatureCollection";
    }
    if (entidade.dados.poligono_estado === "invalido") definirStatus("A delimitação antiga é inválida e permanece preservada. Desenhe uma nova delimitação para substituí-la.", "erro");
    else definirStatus(entidade.dados.poligono_geojson ? "Ajuste o desenho e clique em Salvar polígono." : "Nenhuma delimitação cadastrada. Desenhe e salve um polígono.");
  }
  function restaurarSeletores() {
    const atual = entidadeAtual();
    if (tipoSelect) tipoSelect.value = atual ? atual.tipo : "propriedade";
    if (areaSelect && atual && atual.tipo === "gleba") areaSelect.value = String(atual.dados.id);
    if (areaCampo) areaCampo.hidden = !atual || atual.tipo !== "gleba";
  }
  function selecionarEntidade(novaChave) {
    if (novaChave === chaveAtiva) return;
    if (!entidades.has(novaChave) || busy || modoAtivo) { restaurarSeletores(); return; }
    if (dirty && !window.confirm("Há alterações não salvas. Descartá-las e selecionar outro elemento?")) {
      restaurarSeletores();
      return;
    }
    const anterior = entidadeAtual();
    chaveAtiva = novaChave;
    if (anterior) reconstruirCamada(anterior);
    const atual = entidadeAtual();
    reconstruirCamada(atual);
    carregarDesenho(atual);
    restaurarSeletores();
    tituloEdicao.textContent = "Editando " + descricao(atual);
    const limites = drawnItems.getBounds();
    if (limites.isValid()) {
      // Uma troca rápida não pode manter o enquadramento da entidade anterior.
      mapa.stop();
      mapa.fitBounds(limites, { padding: [24, 24], maxZoom: 17, animate: false });
    }
    atualizarControles();
  }

  function erroHttp(resposta, dados) {
    if (resposta.redirected || resposta.status === 401) return "Sua sessão expirou. Recarregue a página e entre novamente. O desenho local foi preservado.";
    if (resposta.status === 403) return "Acesso negado. Seu perfil não pode alterar esta delimitação. O desenho foi preservado.";
    if (resposta.status === 404 || resposta.status === 409) return "O ambiente ou seu acesso mudou. Recarregue a página antes de salvar. O desenho foi preservado.";
    if (dados && typeof dados.error === "string") return dados.error + " O desenho foi preservado.";
    if (resposta.status === 400) return "Não foi possível validar o formulário. Recarregue a página antes de tentar novamente. O desenho foi preservado.";
    return "Não foi possível confirmar a operação no servidor. O desenho foi preservado.";
  }
  async function enviarPoligono(limpar) {
    const alvo = entidadeAtual();
    if (!alvo || busy || modoAtivo || !editorDisponivel) return;
    const corpo = limpar ? {} : payloadDoDesenho();
    if (!limpar && !corpo) {
      definirStatus("Desenhe um polígono antes de salvar. Para remover a delimitação salva, use Limpar polígono.", "erro");
      return;
    }
    if (limpar && !window.confirm("Remover a delimitação de " + descricao(alvo) + "?")) return;
    if (!limpar && alvo.dados.poligono_geojson && alvo.dados.poligono_geojson.type === "FeatureCollection"
        && !window.confirm("Salvar a coleção legada reunindo todos os polígonos em Polygon ou MultiPolygon? Todas as partes e seus furos serão mantidos.")) return;
    const alvoChave = chave(alvo.tipo, alvo.dados.id);
    const rota = baseUrl + "/" + (alvo.tipo === "propriedade" ? "propriedades" : "glebas") + "/" + alvo.dados.id + "/poligono" + (limpar ? "/limpar" : "");
    busy = true;
    atualizarControles();
    definirStatus(limpar ? "Removendo delimitação…" : "Salvando delimitação…");
    try {
      const resposta = await fetch(rota, {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken, Accept: "application/json" }, body: JSON.stringify(corpo),
      });
      const json = (resposta.headers.get("content-type") || "").includes("application/json");
      const dados = json ? await resposta.json() : null;
      if (!resposta.ok || !dados || dados.ok !== true || resposta.redirected) throw new Error(erroHttp(resposta, dados));
      const atualizado = alvo.tipo === "propriedade" ? dados.propriedade : dados.gleba;
      if (!atualizado || atualizado.id !== alvo.dados.id || chaveAtiva !== alvoChave) throw new Error("A resposta não corresponde ao elemento em edição. Recarregue a página. O desenho foi preservado.");
      if (alvo.tipo === "propriedade" && (!Array.isArray(dados.glebas) || dados.propriedade.id !== propriedadeId)) throw new Error("Resposta territorial incompleta. Recarregue a página. O desenho foi preservado.");
      registrarEntidade(alvo.tipo, atualizado);
      if (alvo.tipo === "propriedade") dados.glebas.forEach((gleba) => registrarEntidade("gleba", gleba));
      carregarDesenho(entidadeAtual());
      definirStatus((dados.message || "Operação confirmada.") + (entidadeAtual().dados.contencao && entidadeAtual().dados.contencao.status === "fora_do_limite" ? " " + entidadeAtual().dados.contencao.mensagem : ""), "ok");
    } catch (erro) {
      const mensagem = erro instanceof TypeError ? "Falha de conexão. O desenho e suas alterações foram preservados; tente novamente."
        : erro instanceof SyntaxError ? "O servidor enviou uma resposta inválida. O desenho foi preservado; tente novamente." : erro.message;
      definirStatus(mensagem, "erro");
    } finally {
      busy = false;
      atualizarControles();
    }
  }

  function configurarEdicao() {
    drawnItems = new L.FeatureGroup().addTo(mapa);
    controleDesenho = new L.Control.Draw({
      edit: { featureGroup: drawnItems, remove: true },
      draw: { polygon: { allowIntersection: false, showArea: false }, polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false },
    });
    mapa.addControl(controleDesenho);
    controleDesenho.getContainer().addEventListener("click", (evento) => {
      if (busy || !chaveAtiva) { evento.preventDefault(); evento.stopImmediatePropagation(); }
    }, true);
    mapa.on(L.Draw.Event.CREATED, (evento) => {
      if (busy || !chaveAtiva) return;
      // Cada desenho é uma parte; conservar todas as partes existentes e os furos.
      evento.layer.setStyle(estilo(entidadeAtual()));
      drawnItems.addLayer(evento.layer);
      atualizarDirty();
      definirStatus("Parte desenhada. Ajuste as partes no editor e clique em Salvar polígono.");
    });
    mapa.on(L.Draw.Event.EDITED + " " + L.Draw.Event.DELETED, () => {
      atualizarDirty();
      definirStatus("Alterações locais prontas. Clique em Salvar polígono para confirmá-las.");
    });
    mapa.on("draw:drawstart draw:editstart draw:deletestart", () => {
      modoAtivo = true;
      atualizarControles();
      definirStatus("Conclua ou cancele a ferramenta de desenho antes de salvar ou trocar o elemento.");
    });
    mapa.on("draw:drawstop draw:editstop draw:deletestop", () => {
      modoAtivo = false;
      atualizarDirty();
      atualizarControles();
    });
    tipoSelect.addEventListener("change", () => {
      const primeiraArea = Array.from(entidades.values()).find((entidade) => entidade.tipo === "gleba");
      selecionarEntidade(tipoSelect.value === "propriedade" ? chave("propriedade", propriedadeId) : primeiraArea ? chave("gleba", Number(areaSelect.value) || primeiraArea.dados.id) : null);
    });
    areaSelect.addEventListener("change", () => selecionarEntidade(chave("gleba", Number(areaSelect.value))));
    btnSalvar.addEventListener("click", () => enviarPoligono(false));
    btnLimpar.addEventListener("click", () => enviarPoligono(true));
  }
  async function carregarDados() {
    try {
      const resposta = await fetch(url, { headers: { Accept: "application/json" } });
      if (!resposta.ok || resposta.redirected || !(resposta.headers.get("content-type") || "").includes("application/json")) throw new Error("Não foi possível carregar os dados. Recarregue a página e confira sua sessão.");
      const dados = await resposta.json();
      if (!dados.propriedade || dados.propriedade.id !== propriedadeId || !Array.isArray(dados.glebas)) throw new Error("A Propriedade ativa mudou. Recarregue a página para abrir o ambiente correto.");
      registrarEntidade("propriedade", dados.propriedade);
      dados.glebas.forEach((gleba) => registrarEntidade("gleba", gleba));
      if (editorDisponivel) {
        configurarEdicao();
        areaSelect.replaceChildren();
        dados.glebas.forEach((gleba) => {
          const opcao = document.createElement("option");
          opcao.value = String(gleba.id); opcao.textContent = gleba.nome; areaSelect.appendChild(opcao);
        });
        tipoSelect.querySelector('option[value="gleba"]').disabled = !dados.glebas.length;
      }
      carregado = true;
      if (editorDisponivel) selecionarEntidade(chave("propriedade", propriedadeId));
      else atualizarControles();
      const limites = L.latLngBounds([]);
      camadas.forEach((camada) => { if (camada.getBounds().isValid()) limites.extend(camada.getBounds()); });
      if (limites.isValid()) {
        mapa.stop();
        mapa.fitBounds(limites, { padding: [24, 24], maxZoom: 16, animate: false });
      }
      else disponibilidade("Nenhuma delimitação cadastrada para exibir. As informações textuais e o cadastro continuam disponíveis.");
    } catch (erro) {
      disponibilidade(erro.message || "Não foi possível carregar os dados do mapa. As informações textuais continuam disponíveis.");
      if (tituloEdicao) tituloEdicao.textContent = "Editor indisponível até recarregar os dados";
      carregado = false;
      atualizarControles();
    }
  }
  atualizarControles();
  carregarDados();
}());
