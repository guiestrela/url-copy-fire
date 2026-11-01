"use strict";

let themeSyncState = { ok: false, status: "Connecting to the local Omarchy helper…" };
let activePort = null;
let retryTimer = null;
let updateQueue = Promise.resolve();
let paletteRetryTimer = null;
let paletteGeneration = 0;
let latestPalette = null;
const PALETTE_RETRY_DELAYS = [250, 500, 1000, 2000];

function cancelPaletteRetry() {
  clearTimeout(paletteRetryTimer);
  paletteRetryTimer = null;
  paletteGeneration += 1;
}

function queuePaletteUpdate(port, generation, attempt = 0) {
  updateQueue = updateQueue.catch(() => {}).then(async () => {
    const current = () => port === activePort && generation === paletteGeneration;
    if (!current()) {
      return;
    }
    const colors = latestPalette;
    try {
      await browser.theme.update({ colors });
      if (current()) {
        themeSyncState = {
          ok: true,
          status: "Omarchy colors applied to application toolbars.",
          colors,
        };
      }
    } catch (error) {
      if (!current()) {
        return;
      }
      themeSyncState = { ok: false, status: error.message };
      if (attempt < PALETTE_RETRY_DELAYS.length) {
        paletteRetryTimer = setTimeout(() => {
          paletteRetryTimer = null;
          if (current()) {
            queuePaletteUpdate(port, generation, attempt + 1);
          }
        }, PALETTE_RETRY_DELAYS[attempt]);
      }
    }
  });
}

function validColor(value) {
  return typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value);
}

const BASE_COLOR_KEYS = [
  "frame", "frame_inactive", "toolbar", "toolbar_text", "tab_background_text", "tab_text",
  "tab_selected", "tab_line", "icons", "toolbar_field", "toolbar_field_text",
  "toolbar_field_focus", "toolbar_field_text_focus", "toolbar_field_border",
  "toolbar_field_border_focus", "toolbar_field_highlight", "toolbar_field_highlight_text",
  "toolbar_top_separator", "toolbar_bottom_separator", "popup", "popup_text", "popup_border",
  "popup_highlight", "popup_highlight_text", "sidebar", "sidebar_text", "sidebar_border",
  "sidebar_highlight", "sidebar_highlight_text", "ntp_background", "ntp_text",
  "button_background_hover", "button_background_active",
];

function mapPalette(message) {
  if (!message || !message.ok || !message.theme || !message.theme.colors) {
    throw new Error("The local helper could not read the desktop palette.");
  }
  const base = message.theme.colors;
  if (typeof base !== "object" || Array.isArray(base)) {
    throw new Error("The local helper returned invalid theme colors.");
  }
  const entries = Object.entries(base);
  if (entries.length !== BASE_COLOR_KEYS.length ||
      !BASE_COLOR_KEYS.every(key => Object.prototype.hasOwnProperty.call(base, key)) ||
      !entries.every(([key, value]) => BASE_COLOR_KEYS.includes(key) && validColor(value))) {
    throw new Error("The local helper returned invalid theme colors.");
  }
  const colors = { ...base };
  if (URL_ROUTE_CONFIG.target === "firefox") {
    colors.tab_line = colors.tab_selected || colors.toolbar;
    if (!validColor(colors.tab_line)) {
      throw new Error("The selected-tab theme color is missing.");
    }
  } else {
    const semantic = message.theme.semantic || {};
    for (const [key, source] of Object.entries(URL_ROUTE_CONFIG.semanticMappings)) {
      if (!validColor(semantic[source])) {
        throw new Error("Update the local companion: semantic theme colors are missing.");
      }
      colors[key] = semantic[source];
    }
    if (!validColor(colors.toolbar)) {
      throw new Error("The toolbar theme color is missing.");
    }
    colors.omarchy_frame = colors.toolbar;
    colors.omarchy_frame_inactive = colors.toolbar;
  }
  return colors;
}

function scheduleReconnect() {
  clearTimeout(retryTimer);
  retryTimer = setTimeout(connectThemeHost, 5000);
}

function connectThemeHost() {
  if (activePort) {
    return;
  }
  clearTimeout(retryTimer);
  try {
    const port = browser.runtime.connectNative("url_route.omarchy_theme");
    activePort = port;
    port.onMessage.addListener(message => {
      if (port !== activePort) {
        return;
      }
      cancelPaletteRetry();
      try {
        latestPalette = mapPalette(message);
        queuePaletteUpdate(port, paletteGeneration);
      } catch (error) {
        themeSyncState = { ok: false, status: error.message };
      }
    });
    port.onDisconnect.addListener(() => {
      // Access the error to consume the API's lastError without logging local paths.
      const ignoredError = port.error || browser.runtime.lastError;
      void ignoredError;
      if (port !== activePort) {
        return;
      }
      cancelPaletteRetry();
      latestPalette = null;
      activePort = null;
      themeSyncState = {
        ok: false,
        status: "Local helper unavailable. Install the companion and reopen this popup.",
      };
      scheduleReconnect();
    });
  } catch (error) {
    activePort = null;
    themeSyncState = {
      ok: false,
      status: "Local helper unavailable. Install the companion and reopen this popup.",
    };
    scheduleReconnect();
  }
}

browser.runtime.onMessage.addListener(message => {
  if (message && message.type === "URL_ROUTE_THEME_STATUS") {
    if (!activePort) {
      connectThemeHost();
    }
    return Promise.resolve(themeSyncState);
  }
  return undefined;
});

connectThemeHost();
