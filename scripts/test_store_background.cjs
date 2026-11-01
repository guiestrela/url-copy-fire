const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../src/theme-sync/background.js"), "utf8");
const tick = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
function palette(toolbar = "#284238") {
  const keys = [
    "frame", "frame_inactive", "toolbar", "toolbar_text", "tab_background_text", "tab_text",
    "tab_selected", "tab_line", "icons", "toolbar_field", "toolbar_field_text",
    "toolbar_field_focus", "toolbar_field_text_focus", "toolbar_field_border",
    "toolbar_field_border_focus", "toolbar_field_highlight", "toolbar_field_highlight_text",
    "toolbar_top_separator", "toolbar_bottom_separator", "popup", "popup_text", "popup_border",
    "popup_highlight", "popup_highlight_text", "sidebar", "sidebar_text", "sidebar_border",
    "sidebar_highlight", "sidebar_highlight_text", "ntp_background", "ntp_text",
    "button_background_hover", "button_background_active",
  ];
  return { ok: true, theme: { colors: Object.fromEntries(keys.map(key => [key, toolbar])) } };
}
function harness(update = async () => {}, config = { target: "firefox", semanticMappings: {} }) {
  let incoming, query, disconnected;
  let nextTimer = 0;
  const timers = new Map();
  const applied = [];
  const port = {
    onMessage: { addListener: fn => { incoming = fn; } },
    onDisconnect: { addListener: fn => { disconnected = fn; } },
  };
  const context = {
    URL_ROUTE_CONFIG: config,
    browser: {
      runtime: { connectNative: () => port, onMessage: { addListener: fn => { query = fn; } } },
      theme: { update: theme => { applied.push(theme); return update(theme); } },
    },
    setTimeout: (fn, delay) => { timers.set(++nextTimer, { fn, delay }); return nextTimer; },
    clearTimeout: id => timers.delete(id),
  };
  vm.runInNewContext(source, context);
  return {
    incoming: value => incoming(value), disconnected: () => disconnected(), applied, timers,
    status: () => query({ type: "URL_ROUTE_THEME_STATUS" }),
    fire: () => { const [id, timer] = timers.entries().next().value; timers.delete(id); timer.fn(); },
  };
}
async function run() {
  const normal = harness();
  normal.incoming(palette());
  await tick();
  assert.equal(normal.applied[0].colors.tab_line, "#284238");
  assert.equal((await normal.status()).ok, true);

  const pending = deferred();
  let attempts = 0;
  const retry = harness(() => ++attempts === 1 ? pending.promise : Promise.resolve());
  retry.incoming(palette());
  await tick();
  pending.reject(new Error("Transient theme failure"));
  await tick();
  assert.equal(retry.timers.size, 1, "Rejected theme updates must retry without another native message");
  retry.fire();
  await tick();
  assert.equal(retry.applied.length, 2);
  assert.equal((await retry.status()).ok, true);
  assert.equal(retry.timers.size, 0);

  const bounded = harness(() => Promise.reject(new Error("Still unavailable")));
  bounded.incoming(palette());
  await tick();
  const delays = [];
  for (let count = 0; bounded.timers.size && count < 10; count++) {
    delays.push([...bounded.timers.values()][0].delay);
    bounded.fire();
    await tick();
  }
  assert.equal(bounded.timers.size, 0, "Retries must stop after a bounded number of attempts");
  assert.ok(delays.length > 0 && delays.length <= 5);
  assert.ok(delays.every((delay, index) => delay > 0 && delay <= 5000 && (!index || delay >= delays[index - 1])));

  const disconnectedUpdate = deferred();
  const disconnected = harness(() => disconnectedUpdate.promise);
  disconnected.incoming(palette());
  await tick();
  disconnected.disconnected();
  disconnectedUpdate.resolve();
  await tick();
  assert.equal((await disconnected.status()).ok, false, "An old resolution must not overwrite disconnect status");

  const staleUpdate = deferred();
  let calls = 0;
  const stale = harness(() => ++calls === 1 ? staleUpdate.promise : Promise.resolve());
  stale.incoming(palette());
  await tick();
  stale.incoming({ ok: false });
  staleUpdate.reject(new Error("Obsolete error"));
  await tick();
  assert.doesNotMatch((await stale.status()).status, /Obsolete/);
  assert.equal(stale.timers.size, 0);
  stale.incoming(palette("#112233"));
  await tick();
  assert.equal((await stale.status()).colors.toolbar, "#112233");

  const cancel = harness(() => Promise.reject(new Error("Temporary")));
  cancel.incoming(palette());
  await tick();
  cancel.incoming(palette("#112233"));
  assert.equal(cancel.timers.size, 0, "A new message must cancel the older retry immediately");
  await tick();
  cancel.disconnected();
  assert.equal(cancel.timers.size, 1, "Only reconnect may remain after disconnect");

  const serialUpdate = deferred();
  let serialCalls = 0;
  const serial = harness(() => ++serialCalls === 1 ? serialUpdate.promise : Promise.resolve());
  serial.incoming(palette());
  await tick();
  serial.incoming(palette("#223344"));
  await tick();
  assert.equal(serial.applied.length, 1, "Deferred updates must remain serialized");
  serialUpdate.resolve();
  await tick();
  assert.equal(serial.applied.length, 2);
  assert.equal((await serial.status()).colors.toolbar, "#223344");
  const malformed = [null, [], ["#112233"], {}, { toolbar: "#112233" },
    { ...palette().theme.colors, unknown_color: "#112233" },
    { ...palette().theme.colors, toolbar: null },
    { ...palette().theme.colors, toolbar: "url(https://invalid/)" },
  ];
  const missing = palette().theme.colors;
  delete missing.frame;
  malformed.push(missing);
  for (const colors of malformed) {
    const invalid = harness();
    invalid.incoming({ ok: true, theme: { colors } });
    await tick();
    assert.equal(invalid.applied.length, 0, `Reject malformed base colors: ${JSON.stringify(colors)}`);
    assert.equal((await invalid.status()).ok, false);
    assert.equal(invalid.timers.size, 0, "Malformed messages must never retry");
  }
  const hostTheme = JSON.parse(require("node:child_process").execFileSync("python3", ["-c", `
import json, runpy, sys, tempfile
from pathlib import Path
host = runpy.run_path(sys.argv[1])
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / 'colors.toml').write_text('background="#ffffff"\\naccent="#509475"\\ngreen="#ffffff"\\n')
    print(json.dumps(host['read_theme'](root)))
`, path.join(__dirname, "omarchy_theme_host.py")], { encoding: "utf8" }));
  assert.deepEqual(Object.keys(hostTheme.colors).sort(), Object.keys(palette().theme.colors).sort(),
    "The required schema must match the real native host, not a partial synthetic fixture");
  const semanticMappings = Object.fromEntries(Object.entries(JSON.parse(fs.readFileSync(
    path.join(__dirname, "thunderbird_semantic_map.json"), "utf8"))).map(([key, value]) => [key, value.semantic]));
  for (const target of ["firefox", "thunderbird"]) {
    const realHost = harness(undefined, { target, semanticMappings });
    realHost.incoming({ ok: true, theme: hostTheme });
    await tick();
    assert.equal((await realHost.status()).ok, true, `Accept real host payload for ${target}`);
    if (target === "thunderbird") {
      assert.equal(realHost.applied[0].colors.omarchy_success_text, hostTheme.semantic.success_text);
      assert.equal(realHost.applied[0].colors.omarchy_notification_success_icon, hostTheme.semantic.success_icon);
    }
  }
  console.log("PASS: Firefox palette, deferred updates, bounded retries, disconnect and stale-generation guards, strict host schema, real-host Firefox/Thunderbird mapping");
}
run().catch(error => { console.error(error); process.exitCode = 1; });
