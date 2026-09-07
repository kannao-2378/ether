(function () {
  "use strict";
  var form = document.getElementById("loginForm");
  var title = document.getElementById("loginTitle");
  var button = document.getElementById("submitButton");
  var status = document.getElementById("status");
  var next = new URLSearchParams(location.search).get("next") || "/portfolio/admin/";
  if (!next.startsWith("/portfolio/") && !next.startsWith("/kan/")) next = "/portfolio/admin/";
  var endpoint = "/api/admin/login";

  function api(url, options) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 15000);
    var settings = Object.assign({ credentials: "same-origin", cache: "no-store", signal: controller.signal }, options || {});
    return fetch(url, settings).then(function (response) {
      return response.json().then(function (body) {
        if (!response.ok) {
          var error = new Error(body.error || "请求失败");
          error.status = response.status;
          throw error;
        }
        return body;
      });
    }).finally(function () { clearTimeout(timer); });
  }

  var ready = api("/api/admin/session")
    .then(function (session) {
      if (session.authenticated) { location.replace(next); return; }
      if (session.needsSetup) {
        endpoint = "/api/admin/setup";
        title.textContent = "设置管理密码";
        button.textContent = "设置并登录";
      } else {
        endpoint = "/api/admin/login";
        title.textContent = "后台登录";
        button.textContent = "登录";
      }
      button.disabled = false;
    }).catch(function (error) {
      status.textContent = error.name === "AbortError" ? "连接服务器超时，请刷新页面重试" : error.message;
      button.textContent = "重新加载";
      button.disabled = false;
      throw error;
    });

  function submitPassword(password) {
    return api(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: password })
    }).catch(function (error) {
      if (endpoint === "/api/admin/setup" && error.status === 409) {
        endpoint = "/api/admin/login";
        title.textContent = "后台登录";
        button.textContent = "登录";
        return api(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: password })
        });
      }
      throw error;
    });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (button.textContent === "重新加载") { location.reload(); return; }
    status.textContent = "正在验证，首次登录可能需要约 3 秒…";
    button.disabled = true;
    ready.then(function () { return submitPassword(form.password.value); })
      .then(function () { location.replace(next); })
      .catch(function (error) {
        status.textContent = error.name === "AbortError" ? "验证超时，请重试" : error.message;
        button.disabled = false;
      });
  });
})();
