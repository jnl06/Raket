/* Sign in / Sign up / Forgot + Reset password: submits the forms to /api/auth/*. */
(function () {
  "use strict";

  function $(root, sel) { return root.querySelector(sel); }

  function clearErrors(form) {
    form.querySelectorAll("[data-error-for]").forEach(function (el) { el.textContent = ""; });
    form.querySelectorAll(".has-error").forEach(function (el) { el.classList.remove("has-error"); });
    form.querySelectorAll("[aria-invalid]").forEach(function (el) { el.removeAttribute("aria-invalid"); });
    var alert = $(form, "[data-alert]");
    if (alert) { alert.hidden = true; alert.textContent = ""; alert.classList.remove("auth-alert--ok"); }
  }

  function showAlert(form, message, ok) {
    var alert = $(form, "[data-alert]");
    if (!alert) return;
    alert.textContent = message;
    alert.classList.toggle("auth-alert--ok", !!ok);
    alert.hidden = false;
  }

  // Puts API field errors next to their inputs; anything unmatched goes in the top alert.
  function showErrors(form, error) {
    clearErrors(form);
    var fields = (error && error.fields) || {};
    var leftovers = [];
    var firstInvalid = null;

    Object.keys(fields).forEach(function (name) {
      var slot = $(form, '[data-error-for="' + name + '"]');
      var text = [].concat(fields[name]).join(" ");
      if (!slot) { leftovers.push(text); return; }
      slot.textContent = text;
      var wrap = slot.closest(".auth-field");
      if (wrap) wrap.classList.add("has-error");
      var input = form.elements[name];
      if (input && input.setAttribute) {
        input.setAttribute("aria-invalid", "true");
        if (!firstInvalid) firstInvalid = input;
      } else if (input && input.length && !firstInvalid) {
        firstInvalid = input[0]; // radio group
      }
    });

    if (!Object.keys(fields).length || leftovers.length) {
      showAlert(form, leftovers.length ? leftovers.join(" ") : (error && error.message) || "Something went wrong.");
    }
    if (firstInvalid && firstInvalid.focus) firstInvalid.focus();
  }

  function setBusy(form, busy) {
    var button = $(form, 'button[type="submit"]');
    if (!button) return;
    if (busy) {
      button.dataset.label = button.textContent;
      button.textContent = button.dataset.busyLabel || "Please wait…";
    } else if (button.dataset.label) {
      button.textContent = button.dataset.label;
    }
    button.disabled = busy;
  }

  function value(form, name) {
    var el = form.elements[name];
    if (!el) return "";
    if (el.type === "checkbox") return el.checked;
    return el.value;
  }

  function goNext(form) {
    window.location.href = form.dataset.next || "/";
  }

  var handlers = {
    signin: function (form) {
      return window.RaketAPI.post("/api/auth/login/", {
        email: value(form, "email").trim(),
        password: value(form, "password"),
        remember_me: value(form, "remember_me"),
      }).then(function (res) {
        if (res.ok) return goNext(form);
        showErrors(form, res.error);
      });
    },

    signup: function (form) {
      var role = form.querySelector('input[name="role"]:checked');
      return window.RaketAPI.post("/api/auth/register/", {
        role: role ? role.value : "",
        full_name: value(form, "full_name"),
        email: value(form, "email"),
        phone: value(form, "phone"),
        password: value(form, "password"),
        confirm_password: value(form, "confirm_password"),
        agree_terms: value(form, "agree_terms"),
      }).then(function (res) {
        if (res.ok) return goNext(form);
        showErrors(form, res.error);
      });
    },

    forgot: function (form) {
      return window.RaketAPI.post("/api/auth/password-reset/", {
        email: value(form, "email").trim(),
      }).then(function (res) {
        if (!res.ok) return showErrors(form, res.error);
        form.reset();
        // The API answers 200 whether or not the email has an account, so we say the same.
        showAlert(form, "If an account exists for that email, a reset link is on its way. Check your inbox.", true);
      });
    },

    reset: function (form) {
      var password = value(form, "new_password");
      if (password !== value(form, "confirm_password")) {
        return Promise.resolve(showErrors(form, { fields: { confirm_password: ["Passwords do not match."] } }));
      }
      return window.RaketAPI.post("/api/auth/password-reset/confirm/", {
        uid: form.dataset.uid,
        token: form.dataset.token,
        new_password: password,
      }).then(function (res) {
        if (!res.ok) return showErrors(form, res.error);
        form.reset();
        showAlert(form, "Your password has been changed. You can sign in now.", true);
        var button = $(form, 'button[type="submit"]');
        if (button) button.hidden = true;
      });
    },
  };

  document.querySelectorAll("form[data-auth]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var run = handlers[form.dataset.auth];
      if (!run) return;
      clearErrors(form);
      setBusy(form, true);
      run(form).then(function () { setBusy(form, false); });
    });
  });

  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    button.addEventListener("click", function () {
      var input = button.parentElement.querySelector("input");
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });
})();
