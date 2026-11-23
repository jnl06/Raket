/* Job page: Apply Now (POST /api/jobs/{id}/apply/) and Withdraw (DELETE /api/applications/{id}/). */
(function () {
  "use strict";

  function showError(root, message) {
    var box = root.querySelector("[data-apply-error]");
    if (!box) return;
    box.textContent = message;
    box.hidden = !message;
  }

  // ---- Apply ----
  var apply = document.querySelector("[data-apply]");
  if (apply) {
    var openBtn = apply.querySelector("[data-apply-open]");
    var panel = apply.querySelector(".apply-panel");
    var done = apply.querySelector("[data-apply-done]");

    function toggle(show) {
      panel.hidden = !show;
      openBtn.hidden = show;
      openBtn.setAttribute("aria-expanded", String(show));
      if (show) panel.querySelector("textarea").focus();
      else openBtn.focus();
    }

    openBtn.addEventListener("click", function () { toggle(true); });
    apply.querySelector("[data-apply-cancel]").addEventListener("click", function () {
      showError(apply, "");
      toggle(false);
    });

    panel.addEventListener("submit", function (event) {
      event.preventDefault();
      var submit = panel.querySelector('button[type="submit"]');
      showError(apply, "");
      submit.disabled = true;
      submit.textContent = "Submitting…";

      window.RaketAPI.post(apply.dataset.url, {
        cover_note: panel.elements.cover_note.value,
      }).then(function (res) {
        if (res.ok) {
          panel.hidden = true;
          done.textContent = "Application sent! The household will review it.";
          done.hidden = false;
          // Reload so the page shows the saved application status (and a Withdraw option).
          setTimeout(function () { window.location.reload(); }, 1200);
          return;
        }
        submit.disabled = false;
        submit.textContent = "Submit application";
        if (res.status === 401) {
          window.location.href = "/signin/?next=" + encodeURIComponent(window.location.pathname);
          return;
        }
        var fields = res.error.fields || {};
        showError(apply, (fields.cover_note && fields.cover_note[0]) || res.error.message);
        // Already applied / job closed: the page is stale, so refresh it after the message.
        if (res.status === 409) setTimeout(function () { window.location.reload(); }, 1800);
      });
    });
  }

  // ---- Withdraw ----
  var box = document.querySelector("[data-apply-withdraw]");
  if (box) {
    var withdraw = box.querySelector("[data-withdraw]");
    if (withdraw) {
      withdraw.addEventListener("click", function () {
        withdraw.disabled = true;
        withdraw.textContent = "Withdrawing…";
        window.RaketAPI.del(box.dataset.url).then(function (res) {
          if (res.ok) { window.location.reload(); return; }
          withdraw.disabled = false;
          withdraw.textContent = "Withdraw application";
          showError(box, res.error.message);
        });
      });
    }
  }
})();
