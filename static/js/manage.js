/* Applied jobs / Manage posted jobs / Manage applicants: row actions call the JSON API,
   then reload so the page shows what was saved. Buttons use data-action = delete | post | patch. */
(function () {
  "use strict";

  document.addEventListener("click", function (e) {
    var button = e.target.closest("[data-action]");
    if (!button || !window.RaketAPI) return;

    var card = button.closest(".row-card");
    var error = card && card.querySelector("[data-error]");
    var label = button.textContent;
    var action = button.dataset.action;
    var url = button.dataset.url;

    if (error) { error.hidden = true; error.textContent = ""; }
    button.disabled = true;
    button.textContent = button.dataset.busy || "Please wait…";

    var request;
    if (action === "delete") request = window.RaketAPI.del(url);
    else if (action === "patch") request = window.RaketAPI.patch(url, { status: button.dataset.status });
    else request = window.RaketAPI.post(url);

    request.then(function (res) {
      if (res.ok) { window.location.reload(); return; }
      button.disabled = false;
      button.textContent = label;
      if (res.status === 401) { window.location.href = "/signin/?next=" + encodeURIComponent(window.location.pathname + window.location.search); return; }
      if (error) { error.textContent = res.error.message; error.hidden = false; }
    });
  });
})();
