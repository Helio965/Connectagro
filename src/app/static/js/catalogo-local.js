/* Evita repetição acidental do envio; o servidor mantém a validação definitiva. */
(function () {
  "use strict";
  document.querySelectorAll("[data-catalogo-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (form.dataset.submitting === "true") {
        event.preventDefault();
        return;
      }
      form.dataset.submitting = "true";
      form.querySelectorAll("button[type=submit]").forEach(function (button) { button.disabled = true; });
      var status = form.querySelector("[data-save-status]");
      if (status) status.textContent = "Salvando…";
    });
    window.addEventListener("pageshow", function () {
      delete form.dataset.submitting;
      form.querySelectorAll("button[type=submit]").forEach(function (button) { button.disabled = false; });
      var status = form.querySelector("[data-save-status]");
      if (status) status.textContent = "";
    });
  });
}());
