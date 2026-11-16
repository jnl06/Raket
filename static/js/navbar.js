(function () {
  const dropdowns = Array.from(document.querySelectorAll("[data-dropdown]"));

  function setOpen(dropdown, open) {
    const trigger = dropdown.querySelector(".navbar__link");
    const menu = dropdown.querySelector(".navbar__menu");
    menu.hidden = !open;
    trigger.setAttribute("aria-expanded", String(open));
  }

  function closeAll(except) {
    dropdowns.forEach((d) => {
      if (d !== except) setOpen(d, false);
    });
  }

  dropdowns.forEach((dropdown) => {
    dropdown.querySelectorAll("[data-dropdown-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const menu = dropdown.querySelector(".navbar__menu");
        const willOpen = menu.hidden;
        closeAll(dropdown);
        setOpen(dropdown, willOpen);
        if (!willOpen) dropdown.querySelector(".navbar__link").focus();
      });
    });
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("[data-dropdown]")) closeAll();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });
})();
