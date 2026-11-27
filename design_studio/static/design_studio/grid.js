/* Design Studio tables marked data-grid: the whole row opens it (click or Enter), headers sort, and an optional
 * toolbar (data-grid-search / data-grid-status / data-grid-count) filters the rows. */
(function () {
  "use strict";

  function cellValue(row, index, kind) {
    var cell = row.cells[index];
    var raw = cell.hasAttribute("data-value") ? cell.getAttribute("data-value") : cell.textContent.trim().toLowerCase();
    return kind === "number" ? parseFloat(raw) || 0 : raw;
  }

  function sortBy(table, header) {
    var index = Array.prototype.indexOf.call(header.parentNode.children, header);
    var kind = header.querySelector("button").getAttribute("data-sort");
    var ascending = header.getAttribute("aria-sort") !== "ascending";
    Array.prototype.forEach.call(table.tHead.rows[0].cells, function (cell) { if (cell.hasAttribute("aria-sort")) cell.setAttribute("aria-sort", "none"); });
    header.setAttribute("aria-sort", ascending ? "ascending" : "descending");
    var body = table.tBodies[0];
    Array.prototype.slice.call(body.rows).sort(function (a, b) {
      var x = cellValue(a, index, kind), y = cellValue(b, index, kind);
      return (x < y ? -1 : x > y ? 1 : 0) * (ascending ? 1 : -1);
    }).forEach(function (row) { body.appendChild(row); });
  }

  function filter(table) {
    var search = document.querySelector("[data-grid-search='" + table.id + "']");
    var status = document.querySelector("[data-grid-status='" + table.id + "']");
    var count = document.querySelector("[data-grid-count='" + table.id + "']");
    var words = search ? search.value.trim().toLowerCase() : "";
    var wanted = status ? status.value : "";
    var shown = 0;
    Array.prototype.forEach.call(table.tBodies[0].rows, function (row) {
      var visible = (!words || row.textContent.toLowerCase().indexOf(words) !== -1) && (!wanted || row.getAttribute("data-status") === wanted);
      row.hidden = !visible;
      if (visible) shown += 1;
    });
    if (count) count.textContent = shown + (shown === 1 ? " batch" : " batches");
    var empty = table.closest(".ds-table-wrap").nextElementSibling;
    if (empty && empty.hasAttribute("data-grid-empty")) empty.hidden = shown > 0;
  }

  function setup(table) {
    table.tBodies[0].addEventListener("click", function (event) {
      if (event.target.closest("a, button, input, select, label")) return;
      var row = event.target.closest("tr[data-href]");
      if (row) window.location.href = row.getAttribute("data-href");
    });
    table.tBodies[0].addEventListener("keydown", function (event) {
      var row = event.target.closest("tr[data-href]");
      if (row && event.key === "Enter" && event.target === row) window.location.href = row.getAttribute("data-href");
    });
    Array.prototype.forEach.call(table.querySelectorAll("th button[data-sort]"), function (button) {
      button.addEventListener("click", function () { sortBy(table, button.parentNode); });
    });
    ["data-grid-search", "data-grid-status"].forEach(function (name) {
      var control = document.querySelector("[" + name + "='" + table.id + "']");
      if (control) control.addEventListener("input", function () { filter(table); });
      if (control) control.addEventListener("change", function () { filter(table); });
    });
    filter(table);
  }

  Array.prototype.forEach.call(document.querySelectorAll("table[data-grid]"), setup);
})();
