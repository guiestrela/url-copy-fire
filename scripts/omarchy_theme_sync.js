"use strict";
let themeSyncState = {ok: false, status: 'Connecting to Omarchy…'};
let themePort = null;
let retry = null;
function connectThemeHost() {
  if (themePort) return;
  try {
    const port = browser.runtime.connectNative('url_route.omarchy_theme');
    themePort = port;
    port.onMessage.addListener(async message => {
      try {
        if (!message.ok || !message.theme || !message.theme.colors) throw new Error(message.error || 'Invalid desktop palette');
        const colors = message.theme.colors;
        if (!Object.values(colors).every(value => typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value))) throw new Error('Invalid theme color');
        await browser.theme.update({colors});
        themeSyncState = {ok: true, status: 'Omarchy colors applied to application toolbars.', colors, updatedAt: new Date().toISOString()};
      } catch (error) {
        themeSyncState = {ok: false, status: error.message};
      }
    });
    port.onDisconnect.addListener(() => {
      const detail = port.error?.message || browser.runtime.lastError?.message || 'Native bridge disconnected';
      themeSyncState = {ok:false, status:detail};
      themePort = null;
      clearTimeout(retry);
      retry = setTimeout(connectThemeHost, 5000);
    });
  } catch (error) {
    themeSyncState = {ok:false, status:error.message};
    clearTimeout(retry);
    retry = setTimeout(connectThemeHost,5000);
  }
}
browser.runtime.onMessage.addListener(message => {
  if (message?.type === 'URL_ROUTE_THEME_STATUS') return Promise.resolve(themeSyncState);
});
connectThemeHost();
