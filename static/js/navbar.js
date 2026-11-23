/* Navbar: dropdowns (click to slide open/closed, one open at a time, close on outside
   click, link click or Escape) and Sign Out. Loaded by templates/base.html. */
(function () {
  "use strict";

  var CLOSE_MS = 550; // slightly longer than the CSS close animation
  var timers = new WeakMap();

  function setOpen(dropdown, open) {
    var menu = dropdown.querySelector(".navbar__menu");
    var trigger = dropdown.querySelector(".navbar__link");
    var isOpen = dropdown.classList.contains("is-open");
    if (open === isOpen) return;

    clearTimeout(timers.get(dropdown));
    trigger.setAttribute("aria-expanded", String(open));

    if (open) {
      menu.hidden = false;
      void menu.offsetHeight; // let the browser paint the closed state first
      dropdown.classList.add("is-open"); // ...then animate to open
    } else {
      dropdown.classList.remove("is-open"); // animate closed...
      timers.set(dropdown, setTimeout(function () { menu.hidden = true; }, CLOSE_MS));
    }
  }

  document.addEventListener("click", function (e) {
    var toggle = e.target.closest("[data-dropdown-toggle]");
    var current = toggle ? toggle.closest("[data-dropdown]") : null;

    document.querySelectorAll("[data-dropdown]").forEach(function (dropdown) {
      var willOpen = dropdown === current && !dropdown.classList.contains("is-open");
      setOpen(dropdown, willOpen);
      if (dropdown === current && !willOpen) dropdown.querySelector(".navbar__link").focus();
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    document.querySelectorAll("[data-dropdown]").forEach(function (d) { setOpen(d, false); });
  });

  // Sign Out -> POST /api/auth/logout/ then back to the home page.
  document.addEventListener("click", function (e) {
    var button = e.target.closest("[data-logout]");
    if (!button || !window.RaketAPI) return;
    button.disabled = true;
    window.RaketAPI.post("/api/auth/logout/").then(function () {
      window.location.href = "/";
    });
  });
})();
