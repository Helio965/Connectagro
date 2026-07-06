// ConnectAgro — JavaScript base compartilhado pelas páginas.
// Comportamentos específicos (ex.: mapa) ficam em seus próprios arquivos.

// Abre/fecha a barra lateral em telas pequenas.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".flash").forEach(function (flash) {
    window.setTimeout(function () {
      flash.classList.add("is-hiding");
    }, 5000);
  });

  // Mostrar/ocultar senha nos campos com botão de olho.
  document.querySelectorAll("[data-password-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      var input = document.getElementById(button.getAttribute("data-target"));
      if (!input) return;

      var mostrar = input.type === "password";
      input.type = mostrar ? "text" : "password";
      button.classList.toggle("is-visible", mostrar);
      button.setAttribute("aria-pressed", String(mostrar));
      button.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
    });
  });

  var toggle = document.getElementById("sidebar-toggle");
  var sidebar = document.getElementById("sidebar");
  var backdrop = document.getElementById("sidebar-backdrop");
  if (!toggle || !sidebar) return;

  sidebar.querySelectorAll("[data-sidebar-toggle]").forEach(function (button) {
    var targetId = button.getAttribute("data-sidebar-toggle");
    var submenu = document.getElementById(targetId);
    if (!submenu) return;

    function setGroupOpen(isOpen) {
      submenu.classList.toggle("open", isOpen);
      button.classList.toggle("is-open", isOpen);
      button.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }

    setGroupOpen(submenu.classList.contains("open"));

    button.addEventListener("click", function () {
      setGroupOpen(!submenu.classList.contains("open"));
    });
  });

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
