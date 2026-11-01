/**
 * src/content/content.js
 * Floating router widget for URL Route.
 * Detects the system theme, routes actions to the background service worker,
 * and sits on top of the page until dismissed.
 */
(function () {
  const STORAGE_KEY = "urlRouteTheme";
  const MODE_AUTO = "auto";
  let widget = null;
  let pid = null;

  const THEMES = {
    auto: "(prefers-color-scheme: dark)",
    light: "(prefers-color-scheme: light)",
    dark: "(prefers-color-scheme: dark)",
  };

  function getThemeFromStorage() {
    try {
      const n = localStorage.getItem(STORAGE_KEY);
      if (n === MODE_AUTO || n === "light" || n === "dark") return n;
    } catch (e) {}
    return MODE_AUTO;
  }

  function updateTheme(mode, badge) {
    const isDark = mode === "dark" || (mode === MODE_AUTO && window.matchMedia(THEMES.auto).matches);
    if (badge) badge.textContent = (isDark ? "🌙 Dark" : "☀️ Light") + " · " + mode;
    document.documentElement.classList.toggle("urlroute-dark", isDark);
    document.documentElement.classList.toggle("urlroute-light", !isDark);
  }

  function createWidget() {
    if (widget) return;
    const root = document.createElement("div");
    root.id = "urlroute-widget";
    root.innerHTML = `
      <div class="urlroute-node">
        <div class="urlroute-handle"><span>🔗 URL Route</span><span class="urlroute-close">✕</span></div>
        <div class="urlroute-rows">
          <button class="urlroute-row" data-action="copy-url" title="Copy URL">📋 Copy URL</button>
          <button class="urlroute-row" data-action="copy-title" title="Copy Title">📋 Copy Title</button>
          <button class="urlroute-row" data-action="copy-url-title" title="Copy URL + Title">📋 Copy URL + Título</button>
          <button class="urlroute-row" data-action="share" title="Compartilhar (Team Leader)">📤 Compartilhar</button>
        </div>
        <div class="urlroute-color">
          <span class="urlroute-dot"></span>
          <button class="urlroute-setting" id="urlroute-theme" title="Theme mode">Auto</button>
        </div>
      </div>
    `;
    document.body.appendChild(root);

    widget = {
      close: () => { root.remove(); widget = null; },
      theme: () => document.getElementById("urlroute-theme"),
      mode: getThemeFromStorage(),
      badge: document.getElementById("urlroute-theme"),
    };
    widget.theme().onclick = () => {
      const m = widget.mode === MODE_AUTO ? "light" : MODE_AUTO;
      widget.mode = m;
      localStorage.setItem(STORAGE_KEY, m);
      updateTheme(m, widget.badge);
      browser.runtime.sendMessage({ type: "URL_ROUTE_ACTION", payload: { name: "theme-" + m } });
    };
  }

  function broadcast(action) {
    try { browser.runtime.sendMessage({ type: "URL_ROUTE_ACTION", payload: { name: action } }); } catch (e) {}
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest(".urlroute-row");
    if (t) {
      const a = t.dataset.action;
      broadcast(a);
      if (a === "copy-url" || a === "copy-title" || a === "copy-url-title") {
        navigator.clipboard.writeText(a === "copy-url" ? location.href : a === "copy-title" ? document.title : location.href + "\n" + document.title).then(() => {
          const msg = a === "copy-url" ? "URL copiada" : a === "copy-title" ? "Título copiado" : "URL e título copiados";
          const toast = document.createElement("div");
          toast.textContent = "✅ " + msg;
          toast.style.cssText = "position:fixed;left:50%;bottom:20px;padding:10px 18px;border-radius:8px;background:#111827;color:#fff;z-index:2147483647;font:14px/1.4 system-ui;opacity:0;transition:opacity .25s;";
          document.body.appendChild(toast);
          requestAnimationFrame(() => { toast.style.opacity = "1"; });
          setTimeout(() => { toast.style.opacity = "0"; setTimeout(() => toast.remove(), 300); }, 2000);
        }).catch(() => {});
      }
    }
  });

  document.addEventListener("click", (e) => {
    const t = e.target.closest(".urlroute-color .urlroute-setting");
    if (t) {
      const current = widget.mode || getThemeFromStorage();
      const m = current === MODE_AUTO ? "light" : current === "light" ? "dark" : MODE_AUTO;
      widget.mode = m;
      localStorage.setItem(STORAGE_KEY, m);
      updateTheme(m, widget.badge);
      try { browser.runtime.sendMessage({ type: "URL_ROUTE_ACTION", payload: { name: "theme-" + m } }); } catch (e) {}
    }
  });

  document.addEventListener("click", (e) => {
    const t = e.target.closest(".urlroute-close");
    if (t) { widget.close(); }
  });

  return {
    init: () => {
      createWidget();
      const stored = getThemeFromStorage();
      updateTheme(stored);
      browser.runtime.sendMessage({ type: "URL_ROUTE_LIST", payload: {} });
      return { id: "urlroute-infinite" };
    },
  };
})();
