/* Tiny client for the Raket JSON API (/api/...). Session cookie auth + CSRF header. */
(function () {
  "use strict";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  /**
   * request("POST", "/api/auth/login/", {email, password})
   * -> Promise<{ok, status, data, error}>   (never rejects on HTTP errors)
   * error = {code, message, fields?} straight from the API's error envelope.
   */
  function request(method, url, body) {
    var options = {
      method: method,
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-CSRFToken": csrfToken() },
    };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    return fetch(url, options)
      .then(function (res) {
        return res
          .json()
          .catch(function () { return {}; })
          .then(function (data) {
            return {
              ok: res.ok,
              status: res.status,
              data: data,
              error: res.ok ? null : data.error || { code: "error", message: "Something went wrong. Please try again." },
            };
          });
      })
      .catch(function () {
        return {
          ok: false,
          status: 0,
          data: {},
          error: { code: "network", message: "Can't reach the server. Check your connection and try again." },
        };
      });
  }

  window.RaketAPI = {
    get: function (url) { return request("GET", url); },
    post: function (url, body) { return request("POST", url, body || {}); },
    patch: function (url, body) { return request("PATCH", url, body || {}); },
    del: function (url) { return request("DELETE", url); },
  };
})();
