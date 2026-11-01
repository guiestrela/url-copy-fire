document.addEventListener("DOMContentLoaded", () => {
  const themeMode = document.getElementById("theme-mode");
  const themeBadge = document.getElementById("theme-badge");
  const historyList = document.getElementById("history-list");
  const historyEmpty = document.getElementById("history-empty");
  const clearHistory = document.getElementById("clear-history");
  const getHistory = async () => { const d = await browser.storage.local.get("urlRouteHistory", []); return Array.isArray(d.urlRouteHistory) ? d.urlRouteHistory : []; };
  const saveHistory = async (items) => browser.storage.local.set({ urlRouteHistory: items });
  const escapeHtml = (s) => (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const renderHistory = (items) => { historyList.innerHTML = ""; if (!items.length) { historyEmpty.style.display = "block"; return; } historyEmpty.style.display = "none"; items.forEach((h, i) => { const li = document.createElement("li"); const b = h.title ? `${escapeHtml(h.type || "action")} — ${escapeHtml((h.url || "") + (h.title ? " — " + h.title : ""))}` : escapeHtml(h.type || "action"); li.innerHTML = `<div class="hi-idx">#${i+1}</div><div class="hi-body">${b}</div>`; historyList.appendChild(li); }); };
  const showToast = (msg) => { const t = document.createElement("div"); t.textContent = msg; t.style.cssText = "position:fixed;left:50%;bottom:16px;transform:translateX(-50%);padding:8px 12px;background:#111827;color:#fff;border-radius:8px;font:13px/1.3 system-ui;z-index:99999;opacity:0;transition:opacity .2s;"; document.body.appendChild(t); requestAnimationFrame(() => { t.style.opacity = "1"; }); setTimeout(() => { t.style.opacity = "0"; setTimeout(() => t.remove(), 300); }, 2000); };
  clearHistory.addEventListener("click", async () => { await saveHistory([]); renderHistory(await getHistory()); });
  (async () => { const m = themeMode.value; const isDark = m === "dark" || (!["light", "dark"].includes(m) && window.matchMedia("(prefers-color-scheme: dark)").matches); themeBadge.textContent = (isDark ? "🌙 Dark" : "☀️ Light") + " · " + (m === "auto" ? "system" : m); const i = await getHistory(); renderHistory(i); })();
});
