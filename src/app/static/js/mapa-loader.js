(function () {
  "use strict";
  const loader = document.currentScript;
  if (!loader) return;

  function iniciarMapa() {
    const script = document.createElement("script");
    script.src = loader.dataset.mapaScript;
    script.onerror = function () {
      const aviso = document.getElementById("mapa-disponibilidade");
      if (aviso) {
        aviso.textContent = "Não foi possível iniciar o mapa. As informações textuais continuam disponíveis.";
        aviso.hidden = false;
      }
    };
    document.head.appendChild(script);
  }

  // O plugin depende de Leaflet; não executá-lo quando a biblioteca falhar.
  if (typeof window.L === "undefined") {
    iniciarMapa();
    return;
  }
  const draw = document.createElement("script");
  draw.src = loader.dataset.drawScript;
  draw.onload = iniciarMapa;
  draw.onerror = iniciarMapa; // O módulo principal mantém leitura sem o editor.
  document.head.appendChild(draw);
}());
