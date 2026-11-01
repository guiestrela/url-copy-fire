"""Build minimal browser-chrome theme synchronization extensions."""
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ID = 'url-route-omarchy-sync@local.invalid'
background = (ROOT/'scripts/omarchy_theme_sync.js').read_text()
subprocess.run(['node','--check','-'], input=background, text=True, check=True)
html = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Omarchy Theme Sync</title><link rel="stylesheet" href="status.css"><h1>Omarchy Theme Sync</h1><p id="state">Connecting…</p><pre id="colors"></pre><p>Updates application toolbars when the desktop palette changes. No browsing or email data is read.</p><script src="status.js"></script></html>'''
css = ''' :root{color-scheme:light dark}body{width:340px;margin:0;padding:16px;background:var(--bg,Canvas);color:var(--fg,CanvasText);font:14px system-ui}h1{font-size:18px}pre{white-space:pre-wrap}'''
status = '''async function refresh(){const state=await browser.runtime.sendMessage({type:'URL_ROUTE_THEME_STATUS'});document.getElementById('state').textContent=state.status;document.getElementById('colors').textContent=state.ok?'Toolbar: '+state.colors.toolbar+'\\nText: '+state.colors.toolbar_text+'\\nAccent: '+state.colors.tab_line:'';if(state.ok){document.documentElement.style.setProperty('--bg',state.colors.popup);document.documentElement.style.setProperty('--fg',state.colors.popup_text);}}refresh().catch(e=>document.getElementById('state').textContent=e.message);setInterval(()=>refresh().catch(()=>{}),2000);'''
for app in ('firefox','thunderbird'):
    version = '0.2.3' if app == 'firefox' else '0.2.5'
    manifest = {
      'manifest_version': 3 if app == 'firefox' else 2,
      'name': 'URL Route — Omarchy Theme Sync', 'version':version,
      'description':'Apply the active Omarchy desktop palette to application toolbars automatically.',
      'permissions':['theme','nativeMessaging'],
      'background':{'scripts':['theme-sync.js']},
      'icons':{str(size):'icons/copy-url-original.png' for size in (16,32,48,96,128)},
      'browser_specific_settings':{'gecko':{'id':ID,'strict_min_version':'140.0' if app=='firefox' else '128.0'}},
    }
    action = {'default_title':'Omarchy Theme Sync','default_popup':'status.html','default_icon':manifest['icons']}
    manifest['action' if app=='firefox' else 'browser_action'] = action
    if app == 'firefox':
      manifest['browser_specific_settings']['gecko']['data_collection_permissions'] = {'required':['none']}
    else:
      manifest['background']['persistent'] = True
      manifest['theme_experiment'] = {'colors': {'omarchy_frame': '--lwt-frame', 'omarchy_frame_inactive': '--lwt-frame-inactive'}}
      semantic_map = json.loads((ROOT/'scripts/thunderbird_semantic_map.json').read_text())
      manifest['theme_experiment']['colors'].update({key:value['css'] for key,value in semantic_map.items()})
      manifest['theme_experiment']['stylesheet'] = 'semantic-overrides.css'
    app_background = background
    if app == 'firefox':
      app_background = background.replace('const colors = message.theme.colors;', 'const colors = {...message.theme.colors, tab_line: message.theme.colors.tab_selected || message.theme.colors.toolbar};')
    if app == 'thunderbird':
      semantic_sources = json.dumps({key:value['semantic'] for key,value in semantic_map.items()})
      semantic_code = 'const semantic = message.theme.semantic || {}; const semanticSources = '+semantic_sources+'; const semanticColors = Object.fromEntries(Object.entries(semanticSources).map(([key,source]) => [key, semantic[source] || message.theme.colors.tab_line])); const colors = {...message.theme.colors, ...semanticColors, omarchy_frame: message.theme.colors.toolbar, omarchy_frame_inactive: message.theme.colors.toolbar};'
      app_background = background.replace('const colors = message.theme.colors;', semantic_code)
    target=ROOT/'build'/f'{app}-omarchy-sync'
    target.mkdir(parents=True,exist_ok=True)
    files={'manifest.json':json.dumps(manifest,indent=2),'theme-sync.js':app_background,'status.html':html,'status.css':css,'status.js':status}
    if app == 'thunderbird':
      files['semantic-overrides.css'] = (ROOT/'scripts/thunderbird_semantic_overrides.css').read_text()
    xpi=ROOT/'build'/f'url-route-{app}-omarchy-sync-{version}.xpi'
    with ZipFile(xpi,'w',ZIP_DEFLATED) as z:
      for name,content in files.items():
        (target/name).write_text(content)
        z.writestr(name,content)
      for name in sorted(set(manifest['icons'].values())):
        (target/name).parent.mkdir(exist_ok=True)
        content=(ROOT/name).read_bytes()
        (target/name).write_bytes(content)
        z.writestr(name,content)
    with ZipFile(xpi) as z:
      assert z.testzip() is None
    print('BUILT',xpi)
