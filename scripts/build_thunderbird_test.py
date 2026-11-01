"""Build a standalone Thunderbird test XPI without changing Firefox sources."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build'
OUT.mkdir(exist_ok=True)
manifest = {
    'manifest_version': 2,
    'name': 'URL Route — Thunderbird Test',
    'version': '0.1.3',
    'description': 'Copy web tab URLs and titles, with local history and system theme.',
    'applications': {'gecko': {'id': 'url-route-test@local.invalid', 'strict_min_version': '128.0'}},
    'permissions': ['tabs', 'storage', 'clipboardWrite', 'theme'],
    'browser_action': {'default_title': 'URL Route', 'default_popup': 'popup.html'},
    'icons': {'48': 'icons/icon48.png', '96': 'icons/icon96.png'},
}
html = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>URL Route</title>
<link rel="stylesheet" href="popup.css"><main><h1>URL Route</h1>
<p id="status" role="status">Loading active tab…</p>
<label>URL<input id="url" readonly></label><label>Title<input id="title" readonly></label>
<button id="copy-url">Copy URL</button><button id="copy-title">Copy title</button>
<button id="copy-url-title">Copy URL + title + time</button>
<button id="example">Open test web tab</button>
<label>Theme<select id="theme"><option value="auto">Thunderbird theme</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
<h2>Local history</h2><ul id="history"></ul><button id="clear">Clear history</button>
<p>No email bodies are read. Nothing is sent to a server.</p></main><script src="theme.js"></script><script src="popup.js"></script></html>'''
css = ''' :root{color-scheme:light dark;--bg:#fafafa;--fg:#18212f;--border:#8090a0} @media(prefers-color-scheme:dark){:root{--bg:#17202c;--fg:#edf3fa}} :root[data-theme=light]{color-scheme:light;--bg:#fafafa;--fg:#18212f} :root[data-theme=dark]{color-scheme:dark;--bg:#17202c;--fg:#edf3fa} *{box-sizing:border-box} body{width:360px;margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px system-ui} h1{font-size:20px}h2{font-size:16px}label{display:block;margin:10px 0}input,select,button{width:100%;padding:8px;margin:4px 0;border:1px solid var(--border);border-radius:6px;color:inherit;background:var(--bg)}button{cursor:pointer}li{overflow-wrap:anywhere;margin:8px 0}ul{max-height:180px;overflow:auto;padding-left:20px}p{font-size:12px}'''
js = '''"use strict";
const $ = id => document.getElementById(id);
let current = null;
async function renderHistory() {
  const data = await browser.storage.local.get({urlRouteHistory: []});
  $("history").replaceChildren();
  for (const item of data.urlRouteHistory) {
    const li = document.createElement("li");
    li.textContent = `${item.title || "Untitled"} — ${item.url} — ${item.ts}`;
    $("history").append(li);
  }
}
async function copyAction(name) {
  if (!current || !/^https?:\\/\\//i.test(current.url || "")) throw new Error("Open a web tab first using the test button.");
  const ts = new Date().toISOString();
  const text = name === "copy-url" ? current.url : name === "copy-title" ? current.title || "" : `${current.url}\\n${current.title || ""}\\n${ts}`;
  await navigator.clipboard.writeText(text);
  const data = await browser.storage.local.get({urlRouteHistory: []});
  await browser.storage.local.set({urlRouteHistory: [{url:current.url,title:current.title || "",ts,type:name},...data.urlRouteHistory].slice(0,50)});
  await renderHistory();
  $("status").textContent = "Copied and saved locally.";
}
async function init() {
  const settings = await browser.storage.local.get({urlRouteTheme:"auto"});
  $("theme").value = settings.urlRouteTheme;
  document.documentElement.dataset.theme = settings.urlRouteTheme;
  await applyThunderbirdTheme();
  const tabs = await browser.tabs.query({active:true,currentWindow:true});
  current = tabs[0] || null;
  $("url").value = current?.url || "";
  $("title").value = current?.title || "";
  $("status").textContent = /^https?:\\/\\//i.test(current?.url || "") ? "Web tab ready." : "Mail tabs have no web URL. Open the test web tab, then reopen this popup.";
  for (const name of ["copy-url","copy-title","copy-url-title"]) {
    $(name).onclick = () => copyAction(name).catch(error => { $("status").textContent = error.message; });
  }
  $("theme").onchange = async () => {
    document.documentElement.dataset.theme = $("theme").value;
    await applyThunderbirdTheme();
    await browser.storage.local.set({urlRouteTheme:$("theme").value});
  };
  $("example").onclick = async () => { await browser.tabs.create({url:"https://example.com/",active:true}); window.close(); };
  $("clear").onclick = async () => { await browser.storage.local.set({urlRouteHistory:[]}); await renderHistory(); };
  await renderHistory();
}
init().catch(error => { $("status").textContent = error.message; });
'''
subprocess.run(['node','--check','-'], input=js, text=True, check=True)
xpi = OUT / 'url-route-thunderbird-0.1.3.xpi'
with ZipFile(xpi, 'w', ZIP_DEFLATED) as z:
    z.writestr('manifest.json', json.dumps(manifest, indent=2))
    z.writestr('popup.html', html)
    z.writestr('popup.css', css)
    z.writestr('popup.js', js)
    z.write(ROOT / 'scripts/thunderbird-theme.js', 'theme.js')
    for size in (48,96):
        z.write(ROOT / f'icons/icon{size}.png', f'icons/icon{size}.png')
with ZipFile(xpi) as z:
    assert z.testzip() is None
    assert json.loads(z.read('manifest.json')) == manifest
    print('XPI:', xpi)
    print('Archive verified:', len(z.namelist()), 'entries')
