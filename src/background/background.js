/**
 * src/background/background.js
 *
 * Central action router for the URL Route extension.
 *
 * Message contract:
 *   - { type: "URL_ROUTE_ACTION", payload: { name } }
 *   - { type: "URL_ROUTE_LIST" }
 *
 * Handlers: copy-url, copy-title, copy-url-title, toggle-theme, open-options,
 *           theme-default, share
 */

const SUB_BOTS = {
  ordem: "http://localhost:8001/v1",
  conhecimento: "http://localhost:8002/v1",
};

const ACTION_ROUTE = {
  "copy-url": "ordem",
  "copy-title": "ordem",
  "copy-url-title": "ordem",
  "theme-auto": "ordem",
  "theme-light": "ordem",
  "theme-dark": "ordem",
  "open-options": "ordem",
  "theme-default": "ordem",
  "share": "conhecimento",
};

const WHITELIST = new Set(Object.keys(ACTION_ROUTE));

async function postToBot(url, payload) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return { ok: res.ok, status: res.status };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

async function deliverViaRelay(payload) {
  const outbox = process.env.TEAM_LEADER_HOME + "/bot_relay/outbox";
  const fs = require("fs");
  const os = require("os");
  try {
    fs.mkdirSync(os.homedir() + "/.urlroute/bot_relay", { recursive: true });
    fs.writeFileSync(os.homedir() + "/.urlroute/bot_relay/outbox", JSON.stringify(payload));
  } catch (e) {
    console.warn("relay outbox unavailable:", e.message);
  }
}

async function handleAction(name, payload) {
  if (!WHITELIST.has(name)) {
    return { ok: false, error: "unknown action: " + name };
  }
  const sub = ACTION_ROUTE[name];
  const targetUrl = SUB_BOTS[sub];
  if (targetUrl) {
    const res = await postToBot(targetUrl, { action: name, payload: payload || {} });
    return { ok: res.ok, action: name, sub: sub, bot_url: targetUrl };
  }
  return { ok: true, action: name, sub: sub };
}

async function handleMessage(msg) {
  if (!msg || msg.type !== "URL_ROUTE_ACTION") {
    return { ok: false, error: "expected URL_ROUTE_ACTION" };
  }
  const { name } = msg.payload || {};
  if (!name) {
    return { ok: false, error: "missing payload.name" };
  }
  const result = await handleAction(name, msg.payload.payload || {});
  return { ok: result.ok, result, error: result.error };
}

browser.runtime.onMessage.addListener(handleMessage);

browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action !== "URL_ROUTE_ACTION") return;
  const { name } = msg.payload || {};
  sendResponse({ ok: true, delivered: true, payload: name });
});

let history = [];
async function getHistory() {
  const data = await browser.storage.local.get("urlRouteHistory", []);
  return Array.isArray(data.urlRouteHistory) ? data.urlRouteHistory : [];
}

async function saveHistory(items) {
  await browser.storage.local.set({ urlRouteHistory: items });
}

async function addHistory(item) {
  const list = await getHistory();
  list.unshift(item);
  if (list.length > 50) list.length = 50;
  await saveHistory(list);
  return list;
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return { ok: true, text };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

async function handleCopyAction(name) {
  const active = await new Promise((resolve) => {
    browser.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const t = tabs && tabs.length ? tabs[0] : null;
      resolve(t && t.url ? { url: t.url, title: t.title } : null);
    });
  });
  let text = "";
  if (!active) {
    return { ok: false, error: "no active tab" };
  }
  if (name === "copy-url") {
    text = active.url;
  } else if (name === "copy-title") {
    text = active.title;
  } else if (name === "copy-url-title") {
    text = active.url + "\n" + active.title;
  }
  const res = await copyToClipboard(text);
  const entry = { type: "copy", url: active.url, title: active.title, ts: Date.now() };
  await addHistory(entry);
  return { ...res, entry };
}

async function handleShare(payload) {
  const res = await handleAction("share", payload || {});
  const data = res.result;
  const entry = {
    type: "share",
    url: data && data.url ? data.url : "",
    title: data && data.title ? data.title : "",
    ts: Date.now(),
    mode: payload && payload.mode ? payload.mode : "json",
  };
  await addHistory(entry);
  return { ok: true, delivered: true, action: "share", data };
}

browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "URL_ROUTE_ACTION" && msg.payload && msg.payload.name === "share") {
    handleShare(msg.payload.payload).then((r) => sendResponse(r)).then(() => {});
  }
});

browser.runtime.onInstalled.addListener(() => {
  browser.contextMenus.create({ id: "urlroute-copy-url", title: "Copy URL", contexts: ["action"] });
  browser.contextMenus.create({ id: "urlroute-copy-title", title: "Copy Title", contexts: ["action"] });
  browser.contextMenus.create({ id: "urlroute-copy-url-title", title: "Copy URL + Title", contexts: ["action"] });
});

browser.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "urlroute-copy-url") await handleCopyAction("copy-url");
  else if (info.menuItemId === "urlroute-copy-title") await handleCopyAction("copy-title");
  else if (info.menuItemId === "urlroute-copy-url-title") await handleCopyAction("copy-url-title");
  else return;
});
