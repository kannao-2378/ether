(function () {
  "use strict";
  var select = document.querySelector("#pageSelect");
  var frame = document.querySelector("#editorFrame");
  var open = document.querySelector("#openButton");
  var reload = document.querySelector("#reloadButton");

  function loadSelected() {
    frame.src = select.value;
    open.href = select.value;
    sessionStorage.setItem("portfolio-admin-page", select.value);
  }

  var saved = sessionStorage.getItem("portfolio-admin-page");
  if (saved && Array.prototype.some.call(select.options, function (option) { return option.value === saved; })) {
    select.value = saved;
    loadSelected();
  }

  select.addEventListener("change", loadSelected);
  reload.addEventListener("click", function () { frame.contentWindow.location.reload(); });
})();
