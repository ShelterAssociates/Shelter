/* Slum search for the Slum data versions page.
 *
 * Filters the server-rendered index in #slumVersionSearchData in the browser,
 * the same way the KML upload page does, and navigates to the chosen slum.
 * Keyboard: Up/Down move the highlight (wrapping), Enter opens, Escape clears.
 */
(function () {
  "use strict";

  var MAX_ROWS = 40;

  function readIndex() {
    var node = document.getElementById("slumVersionSearchData");
    if (!node) { return []; }
    try {
      return JSON.parse(node.textContent) || [];
    } catch (err) {
      return [];
    }
  }

  function tags(row) {
    var out = "";
    if (row.version > 1) { out += '<span class="sv-tag sv-tag--v">v' + row.version + "</span>"; }
    if (row.waiting) { out += '<span class="sv-tag sv-tag--wait">waiting</span>'; }
    if (row.locations > 1) { out += '<span class="sv-tag sv-tag--loc">' + row.locations + " locations</span>"; }
    return out ? '<span class="sv-row-tags">' + out + "</span>" : "";
  }

  function rowButton(row) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "sv-row";
    button.dataset.slumId = row.id;
    /* The name and path come from the database, so they are set as text.
       Only the tags, which this file builds itself, are set as markup. */
    var name = document.createElement("span");
    name.className = "sv-row-name";
    name.textContent = row.name;
    var path = document.createElement("span");
    path.className = "sv-row-path";
    path.textContent = row.path + "  ·  #" + row.id;
    button.appendChild(name);
    button.insertAdjacentHTML("beforeend", tags(row));
    button.appendChild(path);
    return button;
  }

  function matches(index, term) {
    var needle = term.trim().toLowerCase();
    if (!needle) { return []; }
    var found = [];
    for (var i = 0; i < index.length && found.length < MAX_ROWS; i += 1) {
      if (index[i].name.toLowerCase().indexOf(needle) !== -1) { found.push(index[i]); }
    }
    return found;
  }

  function open(slumId) {
    window.location = "/slum-versions/" + slumId + "/";
  }

  /* Up/Down over a list of row buttons, wrapping at both ends. Rows are real
     buttons, so Tab and Enter already work; this adds the arrow keys. */
  function keyboard(container, input) {
    function rows() {
      return Array.prototype.slice.call(container.querySelectorAll(".sv-row"));
    }

    function move(step) {
      var all = rows();
      if (!all.length) { return; }
      var at = all.findIndex(function (row) { return row.classList.contains("is-active"); });
      /* Nothing highlighted yet: Down starts at the top, Up at the bottom. */
      var next = at === -1
        ? (step > 0 ? 0 : all.length - 1)
        : (at + step + all.length) % all.length;
      all.forEach(function (row) { row.classList.remove("is-active"); });
      all[next].classList.add("is-active");
      all[next].scrollIntoView({ block: "nearest" });
    }

    function chosen() {
      var active = container.querySelector(".sv-row.is-active");
      return active || container.querySelector(".sv-row");
    }

    function onKey(event) {
      if (event.key === "ArrowDown") { event.preventDefault(); move(1); return; }
      if (event.key === "ArrowUp") { event.preventDefault(); move(-1); return; }
      if (event.key === "Enter") {
        var row = chosen();
        if (row) { event.preventDefault(); open(row.dataset.slumId); }
        return;
      }
      if (event.key === "Escape" && input) {
        input.value = "";
        input.dispatchEvent(new Event("input"));
      }
    }

    if (input) { input.addEventListener("keydown", onKey); }
    container.addEventListener("keydown", onKey);
    container.addEventListener("click", function (event) {
      var row = event.target.closest(".sv-row");
      if (row) { open(row.dataset.slumId); }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var input = document.getElementById("slumVersionSearchInput");
    var results = document.getElementById("slumVersionSearchResults");
    if (!input || !results) { return; }
    var index = readIndex();

    input.addEventListener("input", function () {
      var found = matches(index, input.value);
      results.innerHTML = "";
      if (!input.value.trim()) {
        results.classList.remove("is-open");
        return;
      }
      if (!found.length) {
        var empty = document.createElement("div");
        empty.className = "sv-empty";
        empty.textContent = "No slum matches that name.";
        results.appendChild(empty);
      } else {
        found.forEach(function (row) { results.appendChild(rowButton(row)); });
      }
      results.classList.add("is-open");
    });

    keyboard(results, input);
    var recent = document.getElementById("slumVersionRecent");
    if (recent) { keyboard(recent, null); }
    input.focus();
  });
})();
