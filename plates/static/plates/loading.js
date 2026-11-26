/* Plates pages: a loading bar and a busy label while a form is sent, and plate images that stop
 * shimmering once loaded. Buttons opt in with data-busy="Making preview..."; downloads do not. */
(function () {
  "use strict";
  var bar = document.getElementById("pl-page-progress");

  function markLoaded(image) {
    if (image.complete && image.naturalWidth) image.classList.add("is-loaded");
    image.addEventListener("load", function () { image.classList.add("is-loaded"); });
  }

  Array.prototype.forEach.call(document.querySelectorAll("img.pl-plate, img.pl-thumb"), markLoaded);

  document.addEventListener("submit", function (event) {
    var button = event.submitter || document.activeElement;
    if (!button || !button.hasAttribute || !button.hasAttribute("data-busy")) return;
    setTimeout(function () {
      if (!button.hasAttribute("data-label")) button.setAttribute("data-label", button.textContent);
      button.textContent = button.getAttribute("data-busy");
      button.classList.add("is-busy");
      if (bar) bar.hidden = false;
    }, 0);
  });

  window.addEventListener("pageshow", function () {
    if (bar) bar.hidden = true;
    Array.prototype.forEach.call(document.querySelectorAll("[data-label]"), function (button) {
      button.textContent = button.getAttribute("data-label");
      button.classList.remove("is-busy");
    });
  });
})();
