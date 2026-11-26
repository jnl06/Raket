/* Header: mobile menu toggle (closes on Escape, outside click or link click) and Sign out.
   Loaded by templates/base.html. */
(function () {
  "use strict";

  var toggle = document.querySelector("[data-menu-toggle]");
  var menu = document.querySelector("[data-menu]");

  function setMenu(open) {
    if (!toggle || !menu) return;
    menu.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
  }

  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      setMenu(toggle.getAttribute("aria-expanded") !== "true");
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        setMenu(false);
        toggle.focus();
      }
    });

    document.addEventListener("click", function (e) {
      if (toggle.getAttribute("aria-expanded") !== "true") return;
      if (!menu.contains(e.target) && !toggle.contains(e.target)) setMenu(false);
    });

    menu.addEventListener("click", function (e) {
      if (e.target.closest("a")) setMenu(false);
    });
  }

  // Desktop dropdowns: click to open, one at a time, Escape or outside click closes.
  var dropdowns = [].slice.call(document.querySelectorAll("[data-dropdown]"));

  function setDropdown(dropdown, open) {
    var trigger = dropdown.querySelector("[data-dropdown-toggle]");
    dropdown.querySelector(".navbar__menu").hidden = !open;
    dropdown.classList.toggle("is-open", open);
    trigger.setAttribute("aria-expanded", String(open));
  }

  document.addEventListener("click", function (e) {
    var toggleBtn = e.target.closest("[data-dropdown-toggle]");
    var current = toggleBtn ? toggleBtn.closest("[data-dropdown]") : null;
    dropdowns.forEach(function (d) {
      setDropdown(d, d === current && !d.classList.contains("is-open"));
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    dropdowns.forEach(function (d) {
      if (!d.classList.contains("is-open")) return;
      setDropdown(d, false);
      d.querySelector("[data-dropdown-toggle]").focus();
    });
  });

  // Sign out -> POST /api/auth/logout/ then back to the home page.
  document.addEventListener("click", function (e) {
    var button = e.target.closest("[data-logout]");
    if (!button || !window.RaketAPI) return;
    button.disabled = true;
    button.textContent = "Signing out…";
    window.RaketAPI.post("/api/auth/logout/").then(function () {
      window.location.href = "/";
    });
  });
})();
