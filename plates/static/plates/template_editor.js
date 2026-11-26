/* Plate template editor: element table <-> JSON, live preview, QR link helper.
 * Loaded by plates/templates/plates/template_edit.html; values are only ever set with textContent/value. */
(function () {
  "use strict";
  var form = document.getElementById("template-form");
  if (!form) return;
  var jsonBox = document.getElementById("id_elements_json");
  var tableBody = document.querySelector("#element-table tbody");
  var fonts = JSON.parse(document.getElementById("plate-fonts").textContent);
  var assets = JSON.parse(document.getElementById("plate-assets").textContent);
  var logoChoices = ["auto:digipin_symbol", "auto:india_post_logo", "auto:maps_logo"].concat(assets.map(function (a) { return String(a.id); }));
  var elements = [];
  var previewTimer = null, linkTimer = null;

  function readJson() {
    try { elements = JSON.parse(jsonBox.value); } catch (e) { elements = []; }
    if (!Array.isArray(elements)) elements = [];
  }

  function writeJson() {
    jsonBox.value = JSON.stringify(elements, null, 1);
    schedulePreview();
  }

  function input(value, onChange, wide) {
    var field = document.createElement("input");
    field.value = value === undefined || value === null ? "" : value;
    if (wide) field.className = "pl-wide";
    field.addEventListener("change", function () { onChange(field.value); });
    return field;
  }

  function select(options, value, onChange) {
    var field = document.createElement("select");
    field.className = "pl-wide";
    options.forEach(function (option) {
      var item = document.createElement("option");
      item.value = option;
      item.textContent = option;
      field.appendChild(item);
    });
    field.value = value || options[0];
    field.addEventListener("change", function () { onChange(field.value); });
    return field;
  }

  function number(value) {
    var parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : parsed;
  }

  // The template stores shares of the plate (0 to 1); the table shows millimetres and points.
  function plateMm(across) {
    var value = parseFloat(document.getElementById(across ? "id_width_mm" : "id_height_mm").value);
    return value > 0 ? value : (across ? 127 : 38.1);
  }

  function rounded(value, places) {
    var factor = Math.pow(10, places);
    return Math.round(value * factor) / factor;
  }

  function toMm(share, across) { return rounded(number(share) * plateMm(across), 2); }
  function fromMm(mm, across) { return rounded(number(mm) / plateMm(across), 6); }
  function toPt(share) { return rounded(number(share) * plateMm(false) / 25.4 * 72, 1); }
  function fromPt(pt) { return rounded(number(pt) * 25.4 / 72 / plateMm(false), 6); }

  function cell(row, content) {
    var td = document.createElement("td");
    if (content instanceof Node) td.appendChild(content); else td.textContent = content || "";
    row.appendChild(td);
  }

  function fontOrLogo(element) {
    if (element.type === "text") return select(fonts, element.font, function (v) { element.font = v; writeJson(); });
    if (element.type === "image") return select(logoChoices, String(element.asset), function (v) { element.asset = v; writeJson(); });
    if (element.type === "badge" && element.child) return select(logoChoices, String(element.child.asset), function (v) { element.child.asset = v; writeJson(); });
    return "";
  }

  function colourKey(element) {
    return { text: "colour", card: "fill", badge: "fill", line: "colour", qr: "fg", image: "recolour" }[element.type];
  }

  function renderTable() {
    tableBody.textContent = "";
    elements.forEach(function (element) {
      if (!Array.isArray(element.box) || element.box.length !== 4) element.box = [0, 0, 0.1, 0.1];
      var row = document.createElement("tr");
      cell(row, element.id);
      cell(row, element.type + (element.parent ? " in " + element.parent : ""));
      [0, 1, 2, 3].forEach(function (index) {
        var across = index % 2 === 0;
        cell(row, input(toMm(element.box[index], across), function (v) { element.box[index] = fromMm(v, across); writeJson(); }));
      });
      cell(row, input(element.z, function (v) { element.z = number(v); writeJson(); }));
      cell(row, fontOrLogo(element));
      var isText = element.type === "text";
      cell(row, isText ? input(toPt(element.max_size), function (v) { element.max_size = fromPt(v); writeJson(); }) : "");
      cell(row, isText ? input(toPt(element.min_size), function (v) { element.min_size = fromPt(v); writeJson(); }) : "");
      var key = colourKey(element);
      cell(row, key ? input(element[key], function (v) { element[key] = v || null; writeJson(); }) : "");
      cell(row, isText && (element.source || "fixed") === "fixed" ? input(element.text, function (v) { element.text = v; writeJson(); }, true) : (isText ? "(" + element.source + ")" : ""));
      tableBody.appendChild(row);
    });
  }

  function showList(list, items) {
    list.textContent = "";
    items.forEach(function (text) {
      var item = document.createElement("li");
      item.textContent = text;
      list.appendChild(item);
    });
  }

  function schedulePreview() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(preview, 600);
  }

  var previewArea = document.getElementById("preview-area");
  var previewNumber = 0, previewRequest = null;

  function showLoading(on) {
    previewArea.classList.toggle("is-loading", on);
    document.getElementById("preview-progress").hidden = !on;
    document.getElementById("preview-note").hidden = !on;
  }

  function showPreview(result) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-preview-skeleton]"), function (box) { box.hidden = true; });
    Array.prototype.forEach.call(document.querySelectorAll("img[data-preview]"), function (image) {
      image.hidden = !result.image;
      if (result.image) image.src = result.image;
    });
    showList(document.getElementById("preview-problems"), result.problems);
    document.getElementById("preview-ok").hidden = result.problems.length > 0;
  }

  function preview() {
    // Only the newest request counts; an older, slower one is cancelled so the preview never jumps back.
    var mine = ++previewNumber;
    if (previewRequest) previewRequest.abort();
    previewRequest = window.AbortController ? new AbortController() : null;
    var data = new FormData(form);
    data.append("base", form.getAttribute("data-base"));
    if (document.getElementById("preview-worst").checked) data.append("worst", "1");
    showLoading(true);
    fetch(form.getAttribute("data-preview-url"), { method: "POST", body: data, credentials: "same-origin", signal: previewRequest ? previewRequest.signal : undefined })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (result) { if (mine === previewNumber) showPreview(result); })
      .catch(function (error) {
        if (error.name === "AbortError" || mine !== previewNumber) return;
        showList(document.getElementById("preview-problems"), ["The preview could not be drawn. Check the connection, then change a value to try again."]);
      })
      .then(function () { if (mine === previewNumber) showLoading(false); });
  }

  function checkLink() {
    var data = new FormData();
    data.append("pattern", document.getElementById("id_qr_link_pattern").value);
    data.append("plate_type", document.getElementById("id_plate_type").value);
    data.append("csrfmiddlewaretoken", form.querySelector("input[name=csrfmiddlewaretoken]").value);
    document.getElementById("link-filled").textContent = "Checking…";
    fetch(form.getAttribute("data-link-url"), { method: "POST", body: data, credentials: "same-origin" })
      .then(function (response) { return response.json(); })
      .then(function (result) {
        document.getElementById("link-filled").textContent = result.link || "—";
        showList(document.getElementById("link-problems"), result.problems);
        var qr = document.getElementById("link-qr");
        qr.hidden = !result.qr;
        if (result.qr) qr.src = result.qr;
      });
  }

  function scheduleLink() {
    clearTimeout(linkTimer);
    linkTimer = setTimeout(checkLink, 400);
    schedulePreview();
  }

  function insertVariable(name) {
    var box = document.getElementById("id_qr_link_pattern");
    var start = box.selectionStart || box.value.length, end = box.selectionEnd || box.value.length;
    box.value = box.value.slice(0, start) + "{" + name + "}" + box.value.slice(end);
    box.focus();
    scheduleLink();
  }

  readJson();
  renderTable();
  jsonBox.addEventListener("change", function () { readJson(); renderTable(); schedulePreview(); });
  ["id_width_mm", "id_height_mm"].forEach(function (id) {
    document.getElementById(id).addEventListener("change", renderTable);
  });
  form.addEventListener("change", function (event) {
    if (event.target.id === "id_output_kind" && event.target.value === "sticker") document.getElementById("id_holes_on").checked = false;
    if (event.target.closest && event.target.closest("#element-table")) return;
    schedulePreview();
  });
  document.getElementById("preview-worst").addEventListener("change", preview);
  document.getElementById("id_qr_link_pattern").addEventListener("input", scheduleLink);
  document.getElementById("pattern-start").addEventListener("change", function (event) {
    if (event.target.value) { document.getElementById("id_qr_link_pattern").value = event.target.value; scheduleLink(); }
  });
  Array.prototype.forEach.call(document.querySelectorAll("[data-variable]"), function (button) {
    button.addEventListener("click", function () { insertVariable(button.getAttribute("data-variable")); });
  });
  preview();
  checkLink();
})();
