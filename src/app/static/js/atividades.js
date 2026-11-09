/* Itens do formulário operacional; validações definitivas pertencem ao backend. */
(function () {
  "use strict";
  document.querySelectorAll("[data-operacional-form]").forEach(function (form) {
    var container = form.querySelector("[data-items-container]");
    var addButton = form.querySelector("[data-add-item]");
    var itemTemplate = form.querySelector("#operacional-item-template");
    var itemStatus = form.querySelector("[data-items-status]");
    var nextIndex = container ? container.querySelectorAll("[data-item-row]").length : 0;

    function refreshItems() {
      if (!container) return;
      var rows = container.querySelectorAll("[data-item-row]");
      rows.forEach(function (row, index) {
        var number = row.querySelector("[data-item-number]");
        if (number) number.textContent = String(index + 1);
      });
      if (addButton) addButton.disabled = rows.length >= 20;
      if (itemStatus) itemStatus.textContent = rows.length + " de 20 produtos adicionados.";
    }

    if (container && addButton && itemTemplate) {
      addButton.addEventListener("click", function () {
        if (container.querySelectorAll("[data-item-row]").length >= 20) return;
        var fragment = document.createElement("template");
        fragment.innerHTML = itemTemplate.innerHTML.replace(/__INDEX__/g, String(nextIndex++));
        container.appendChild(fragment.content.cloneNode(true));
        refreshItems();
        var rows = container.querySelectorAll("[data-item-row]");
        var firstField = rows[rows.length - 1].querySelector("select, input:not([type=hidden])");
        if (firstField) firstField.focus();
      });
      container.addEventListener("click", function (event) {
        var button = event.target.closest("[data-remove-item]");
        if (!button || button.disabled) return;
        button.closest("[data-item-row]").remove();
        refreshItems();
        addButton.focus();
      });
      refreshItems();
    }

    form.addEventListener("submit", function (event) {
      if (form.dataset.submitting === "true") {
        event.preventDefault();
        return;
      }
      form.dataset.submitting = "true";
      var saveButton = form.querySelector("[data-save-button]");
      if (saveButton) saveButton.disabled = true;
      var status = form.querySelector("[data-save-status]");
      if (status) status.textContent = "Salvando…";
    });
    window.addEventListener("pageshow", function () {
      delete form.dataset.submitting;
      var saveButton = form.querySelector("[data-save-button]");
      if (saveButton) saveButton.disabled = false;
      var status = form.querySelector("[data-save-status]");
      if (status) status.textContent = "";
    });
  });
}());
