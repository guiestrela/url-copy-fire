"use strict";
const themeKeys = ['--bg','--fg','--border'];
function themeColor(value) {
  if (Array.isArray(value) && value.length === 3 && value.every(n => Number.isFinite(n) && n >= 0 && n <= 255)) return `rgb(${value.join(',')})`;
  return typeof value === 'string' && value.trim() ? value : null;
}
async function applyThunderbirdTheme() {
  const root = document.documentElement;
  for (const key of themeKeys) root.style.removeProperty(key);
  if (root.dataset.theme !== 'auto') return;
  try {
    const win = await browser.windows.getCurrent();
    const theme = await browser.theme.getCurrent(win.id);
    const colors = theme.colors || {};
    const palette = [colors.popup || colors.toolbar || colors.frame, colors.popup_text || colors.toolbar_text || colors.tab_background_text, colors.popup_border || colors.toolbar_bottom_separator];
    palette.forEach((value,index) => {const color = themeColor(value); if(color) root.style.setProperty(themeKeys[index],color);});
  } catch (error) { console.warn('Theme colors unavailable; using system colors.',error); }
}
browser.theme.onUpdated.addListener(async () => { await applyThunderbirdTheme(); });
