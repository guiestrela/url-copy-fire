document.addEventListener("DOMContentLoaded", () => {
  const themeMode = document.getElementById("theme-mode");
  const themeBadge = document.getElementById("theme-badge");
  const urlInput = document.getElementById("url");
  const titleInput = document.getElementById("title");
  const historyList = document.getElementById("history-list");
  const historyEmpty = document.getElementById("history-empty");
  const clearHistory = document.getElementById("clear-history");

  const getHistory = async () => {
    const data = await browser.storage.local.get("urlRouteHistory", []);
    return Array.isArray(data.urlRouteHistory) ? data.urlRouteHistory : [];
  };
  const saveHistory = async (items) => browser.storage.local.set({ urlRouteHistory: items });
  const escapeHtml = (s) => (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const renderHistory = (items) => {
    historyList.innerHTML = "";
    if (!items.length) { historyEmpty.style.display = "block"; return; }
    historyEmpty.style.display = "none";
    items.forEach((h, i) => {
      const li = document.createElement("li");
      const body = h.title ? `${escapeHtml(h.type || "ação")} — ${escapeHtml((h.url || "") + (h.title ? " — " + h.title : ""))}` : escapeHtml(h.type || "ação");
      li.innerHTML = `<div class="hi-idx">#${i+1}</div><div class="hi-body">${body}</div>`;
      historyList.appendChild(li);
    });
  };
  const showToast = (msg) => {
    const t = document.createElement("div");
    t.textContent = msg;
    t.style.cssText = "position:fixed;left:50%;bottom:16px;transform:translateX(-50%);padding:8px 12px;background:#111827;color:#fff;border-radius:8px;font:13px/1.3 system-ui;z-index:99999;opacity:0;transition:opacity .2s;";
    document.body.appendChild(t);
    requestAnimationFrame(() => { t.style.opacity = "1"; });
    setTimeout(() => { t.style.opacity = "0"; setTimeout(() => t.remove(), 300); }, 2000);
  };
  const runAction = async (name) => {
    try {
      const res = await browser.runtime.sendMessage({ type: "URL_ROUTE_ACTION", payload: { name } });
      if (res && res.ok) showToast((res.result && res.result.text) || "OK");
      else showToast("Error: " + (res && res.error ? res.error : "unknown"));
    } catch (e) { showToast("Error: " + e); }
  };
  const getActive = async () => {
    try {
      const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url) {
        urlInput.value = tab.url;
        try {
          const data = await browser.scripting.executeScript({ target: { tabId: tab.id }, func: () => ({ title: document.title }) });
          if (data && data[0] && data[0].result) titleInput.value = data[0].result.title;
        } catch (e) {}
      }
    } catch (e) {}
  };
  document.querySelectorAll(".actions .btn").forEach((btn) => {
    btn.onclick = async () => {
      const act = btn.dataset.act;
      if (act === "theme-default") { themeMode.value = "auto"; readTheme(); await browser.storage.sync.set({ urlRouteTheme: "auto" }); return; }
      if (act === "open-options") { browser.runtime.openOptionsPage(); return; }
      if (act === "share") {
        const tab = await getActive();
        const url = tab && tab.url ? tab.url : urlInput.value.trim() || "";
        const title = tab && tab.title ? tab.title : titleInput.value.trim() || "";
        const payload = { ts: Date.now(), url, title, host: (() => { try { return new URL(url).hostname; } catch (e) { return ""; } })() };
        let text;
        if (themeMode.value === "markdown") text = `📌 **${title || "untitled"}**\n🔗 ${url}`;
        else if (themeMode.value === "text") text = `${url}\n→ ${title || "untitled"}`;
        else text = JSON.stringify(payload, null, 2);
        await runAction("share");
        await addHistory({ url, title, type: "share", text, mode: themeMode.value });
        renderHistory(await getHistory());
        return;
      }
      runAction(act);
    };
  });
  clearHistory.addEventListener("click", async () => { await saveHistory([]); renderHistory(await getHistory()); });
  const readTheme = () => {
    const m = themeMode.value;
    const isDark = m === "dark" || (!["light", "dark"].includes(m) && window.matchMedia("(prefers-color-scheme: dark)").matches);
    themeBadge.textContent = (isDark ? "🌙 Dark" : "☀️ Light") + " · " + (m === "auto" ? "system" : m);
  };
  readTheme();
  (async () => {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url) {
      urlInput.value = tab.url;
      try {
        const data = await browser.scripting.executeScript({ target: { tabId: tab.id }, func: () => ({ title: document.title }) });
        if (data && data[0] && data[0].result) titleInput.value = data[0].result.title;
      } catch (e) {}
    }
    const items = await getHistory(); renderHistory(items); readTheme();
  })();
});
