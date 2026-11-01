// Runs before React/CSS paints. Cache is a first-paint hint; server settings win.
(function () {
  var key = 'pels-theme-preference';
  var current = 'system';
  try { current = localStorage.getItem(key) || 'system'; } catch (_) {}
  function apply(preference) {
    current = ['light', 'dark', 'system'].indexOf(preference) >= 0 ? preference : 'system';
    var dark = current === 'dark' || current === 'system' && matchMedia('(prefers-color-scheme: dark)').matches;
    var root = document.documentElement;
    var chrome = dark ? '#202223' : '#f3f5f5';
    root.dataset.theme = dark ? 'dark' : 'light';
    root.style.colorScheme = dark ? 'dark' : 'light';
    root.style.backgroundColor = chrome;
    root.style.setProperty('--app-chrome-bg', chrome);
    document.querySelector('meta[name="theme-color"]').setAttribute('content', chrome);
    document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]').setAttribute('content', dark ? 'black' : 'default');
    try { localStorage.setItem(key, current); } catch (_) {}
  }
  window.PELSTheme = {read: function () { return current; }, apply: apply};
  apply(current);
}());
