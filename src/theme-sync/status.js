"use strict";

const stateLabel = document.getElementById("state");
const colorDetails = document.getElementById("colors");

async function refreshStatus() {
  const state = await browser.runtime.sendMessage({
    type: "URL_ROUTE_THEME_STATUS",
  });
  if (!state || typeof state.status !== "string") {
    throw new Error("Theme synchronization status is unavailable.");
  }
  stateLabel.textContent = state.status;
  colorDetails.textContent = "";
  if (state.ok && state.colors) {
    colorDetails.textContent = [
      `Toolbar: ${state.colors.toolbar}`,
      `Text: ${state.colors.toolbar_text}`,
    ].join("\n");
    document.documentElement.style.setProperty("--popup-bg", state.colors.popup);
    document.documentElement.style.setProperty("--popup-fg", state.colors.popup_text);
  }
}

function showFailure(error) {
  stateLabel.textContent = error.message;
}

refreshStatus().catch(showFailure);
setInterval(() => refreshStatus().catch(showFailure), 2000);
