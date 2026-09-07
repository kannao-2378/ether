(function () {
  "use strict";
  document.documentElement.style.visibility = "hidden";
  fetch("/api/admin/session", { credentials: "same-origin", cache: "no-store" })
    .then(function (response) { return response.json(); })
    .then(function (session) {
      if (!session.authenticated) {
        location.replace("/kan/admin/?next=" + encodeURIComponent(location.pathname + location.search));
        return;
      }
      document.documentElement.style.visibility = "";
    })
    .catch(function () { location.replace("/kan/admin/"); });
})();
