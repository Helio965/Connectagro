// ConnectAgro — JavaScript base compartilhado pelas páginas.
// Comportamentos específicos (ex.: mapa) ficam em seus próprios arquivos.

// Abre/fecha a barra lateral em telas pequenas.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".flash").forEach(function (flash) {
    window.setTimeout(function () {
      flash.classList.add("is-hiding");
    }, 5000);
  });

  var toggle = document.getElementById("sidebar-toggle");
  var sidebar = document.getElementById("sidebar");
  var backdrop = document.getElementById("sidebar-backdrop");
  if (!toggle || !sidebar) return;

  function abrir() {
    sidebar.classList.add("open");
    if (backdrop) backdrop.classList.add("show");
    toggle.setAttribute("aria-expanded", "true");
  }
  function fechar() {
    sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("show");
    toggle.setAttribute("aria-expanded", "false");
  }

  toggle.addEventListener("click", function () {
    if (sidebar.classList.contains("open")) {
      fechar();
    } else {
      abrir();
    }
  });

  if (backdrop) backdrop.addEventListener("click", fechar);

  // Ao tocar em um link no mobile, fecha o menu para revelar o conteúdo.
  sidebar.querySelectorAll(".sidebar-nav a").forEach(function (link) {
    link.addEventListener("click", fechar);
  });

  // Fecha com a tecla Esc.
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") fechar();
  });
});
