(function () {
  "use strict";
  var state = null;
  var moduleList = document.querySelector("#moduleList");
  var saveStatus = document.querySelector("#saveStatus");
  var preview = document.querySelector("#previewFrame");
  var returnTo = new URLSearchParams(location.search).get("next");
  if (returnTo && !returnTo.startsWith("/portfolio/") && !returnTo.startsWith("/kan/")) returnTo = null;

  function api(url, options) {
    return fetch(url, Object.assign({ credentials: "same-origin" }, options || {})).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) throw new Error(body.error || "操作失败");
        return body;
      });
    });
  }

  function openAdmin() {
    if (returnTo) { location.replace(returnTo); return; }
    api("../content.json?time=" + Date.now()).then(function (content) { state = content; render(); })
      .catch(function (error) { saveStatus.textContent = "读取内容失败：" + error.message; });
  }

  function render() {
    document.querySelectorAll("[data-field]").forEach(function (input) { input.value = state[input.dataset.field] || ""; });
    document.querySelectorAll("[data-type]").forEach(function (input) {
      var parts = input.dataset.type.split(".");
      input.value = state.typography && state.typography[parts[0]] ? state.typography[parts[0]][parts[1]] || "" : "";
    });
    renderModules();
  }

  function renderModules() {
    moduleList.replaceChildren();
    state.modules.forEach(function (item, index) {
      var card = document.createElement("article");
      card.className = "module-card";
      card.innerHTML = '<div class="module-card__top"><strong></strong><label><input type="checkbox"> 显示</label></div><label>名称<input data-key="title"></label><label>副标题<input data-key="subtitle"></label><label>目标链接<input data-key="href" placeholder="暂未开放可留空"></label><div class="module-actions"><button type="button" data-action="up">上移</button><button type="button" data-action="down">下移</button><button class="danger" type="button" data-action="delete">删除</button></div>';
      card.querySelector("strong").textContent = String(index + 1).padStart(2, "0") + " · " + (item.title || "未命名入口");
      var checkbox = card.querySelector('input[type="checkbox"]');
      checkbox.checked = item.enabled !== false;
      checkbox.addEventListener("change", function () { item.enabled = checkbox.checked; });
      card.querySelectorAll("[data-key]").forEach(function (input) { input.value = item[input.dataset.key] || ""; input.addEventListener("input", function () { item[input.dataset.key] = input.value; }); });
      card.querySelector('[data-action="up"]').addEventListener("click", function () { if (index > 0) { state.modules.splice(index - 1, 0, state.modules.splice(index, 1)[0]); renderModules(); } });
      card.querySelector('[data-action="down"]').addEventListener("click", function () { if (index < state.modules.length - 1) { state.modules.splice(index + 1, 0, state.modules.splice(index, 1)[0]); renderModules(); } });
      card.querySelector('[data-action="delete"]').addEventListener("click", function () { if (confirm("确定删除这个入口模块吗？")) { state.modules.splice(index, 1); renderModules(); } });
      moduleList.appendChild(card);
    });
  }

  document.querySelectorAll("[data-field]").forEach(function (input) { input.addEventListener("input", function () { if (state) state[input.dataset.field] = input.value; }); });
  document.querySelectorAll("[data-type]").forEach(function (input) { input.addEventListener("input", function () { if (!state) return; var parts = input.dataset.type.split("."); state.typography[parts[0]] = state.typography[parts[0]] || {}; state.typography[parts[0]][parts[1]] = Number(input.value); }); });

  document.querySelector("#addModuleButton").addEventListener("click", function () { state.modules.push({ id: "module-" + Date.now(), title: "新入口", subtitle: "New section", href: "", enabled: true, kind: "number" }); renderModules(); });
  document.querySelector("#saveButton").addEventListener("click", function () {
    saveStatus.textContent = "正在保存…";
    api("/api/hub/content", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state) })
      .then(function () {
        saveStatus.textContent = "已保存";
        try { localStorage.setItem("kan-content-updated", String(Date.now())); } catch (error) { /* Storage may be unavailable. */ }
        preview.contentWindow.location.reload();
      })
      .catch(function (error) { saveStatus.textContent = error.message; });
  });
  document.querySelector("#logoutButton").addEventListener("click", function () { api("/api/admin/logout", { method: "POST" }).finally(function () { location.reload(); }); });
  openAdmin();
})();
