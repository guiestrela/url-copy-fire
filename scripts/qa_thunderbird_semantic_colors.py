"""Test semantic palette colors in real Thunderbird chrome and about:3pane, without email data."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
import omarchy_theme_host as host

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'],prefix='tb-semantic-qa-') as tmp:
    root=Path(tmp);profile=root/'profile';profile.mkdir();palette=root/'palette';palette.mkdir()
    def set_palette(accent,warning,error):
        (palette/'colors.toml').write_text(f'background="#111c18"\nforeground="#c1c497"\naccent="{accent}"\nyellow="{warning}"\nred="{error}"\ngreen="#63b07a"\n')
        (palette/'chromium.theme').write_text('17,28,24')
    set_palette('#509475','#d4b665','#d56370')
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    prefs={'marionette.port':port,'mail.provider.enabled':False,'mail.shell.checkDefaultClient':False,'mailnews.start_page.enabled':False,'mailnews.start_page.url':''}
    (profile/'user.js').write_text(''.join(f'user_pref({json.dumps(k)}, {json.dumps(v)});\n' for k,v in prefs.items()))
    env=os.environ.copy();env['URL_ROUTE_THEME_DIR']=str(palette)
    env.update({'XDG_CONFIG_HOME':str(root/'config'),'XDG_CACHE_HOME':str(root/'cache'),'XDG_DATA_HOME':str(root/'data')})
    log=(root/'thunderbird.log').open('w')
    process=subprocess.Popen(['/usr/bin/thunderbird','--headless','--no-remote','--profile',str(profile),'--marionette','--remote-allow-system-access'],env=env,stdout=log,stderr=subprocess.STDOUT)
    driver=None
    try:
        for _ in range(120):
            if process.poll() is not None:raise RuntimeError('Thunderbird exited')
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.3):break
            except OSError:time.sleep(.5)
        else:raise TimeoutError('No isolated Thunderbird connection')
        binary=next((Path.home()/'.cache/selenium/geckodriver/linux64').glob('*/geckodriver'))
        driver=webdriver.Firefox(options=Options(),service=Service(executable_path=str(binary),service_args=['--connect-existing','--marionette-port',str(port),'--allow-system-access']))
        package=Path(os.environ.get('TEST_XPI',str(ROOT/'build/url-route-thunderbird-omarchy-sync-0.2.5.xpi')))
        driver.install_addon(str(package),temporary=True);driver.set_context('chrome')
        for accent,warning,error in [('#509475','#d4b665','#d56370'),('#a576d8','#e2b951','#e17090')]:
            set_palette(accent,warning,error)
            expected=host.read_theme(palette)['semantic']
            def css(value):
                return 'rgb(' + ', '.join(str(c) for c in host.rgb(value)) + ')'
            for _ in range(40):
                report=driver.execute_script('''let w=Services.wm.getMostRecentWindow('mail:3pane');let t=w.document.getElementById('tabmail');let p=t.currentAbout3Pane;const variables=['--new-folder-color','--folderpane-unread-new-count-background','--folderpane-unread-count-text','--folder-color-inbox','--color-text-warning','--color-text-critical'];function get(win){let s=win.getComputedStyle(win.document.documentElement);return Object.fromEntries(variables.map(v=>[v,s.getPropertyValue(v).trim()]));}return {main:get(w),pane:p?get(p):null,paneURL:p?.location.href};''')
                actual=report.get('pane') or {}
                if actual.get('--folderpane-unread-new-count-background')==css(accent):break
                time.sleep(.25)
            print('SEMANTIC_SCOPE',json.dumps(report),flush=True)
            assert report['pane'], 'about:3pane is not available'
            assert actual['--folderpane-unread-new-count-background']==css(accent), 'Badge still uses a fixed Thunderbird blue'
            assert actual['--new-folder-color']==css(expected['unread']), 'New-message label does not use the palette'
            assert actual['--folder-color-inbox']==css(expected['unread'])
            assert actual['--color-text-warning']==css(expected['warning_text'])
            assert actual['--color-text-critical']==css(expected['error_text'])
            widgets=driver.execute_script('''const w=Services.wm.getMostRecentWindow('mail:3pane').document.getElementById('tabmail').currentAbout3Pane;const d=w.document;const probe=d.createElement('div');probe.innerHTML='<li class="unread new-messages"><div class="container"><span class="name">Fixture folder</span><span class="unread-count folder-count-badge">3</span></div></li><div id="threadTree" rows="thread-card"><div class="card-layout" data-properties="unread new"><span class="subject">Fixture subject</span></div></div>';d.body.append(probe);const name=w.getComputedStyle(probe.querySelector('.name'));const badge=w.getComputedStyle(probe.querySelector('.unread-count'));const subject=w.getComputedStyle(probe.querySelector('.subject'));const result={label:name.color,badge:badge.backgroundColor,badgeText:badge.color,subject:subject.color};probe.remove();return result;''')
            print('REAL_WIDGET_STYLES',widgets,flush=True)
            assert widgets['label']==css(expected['unread']),widgets
            assert widgets['badge']==css(accent),widgets
            assert widgets['badgeText']==css(expected['accent_text']),widgets
            assert widgets['subject']==css(expected['unread']),widgets
            notifications=driver.execute_async_script('''const done=arguments[0];const w=Services.wm.getMostRecentWindow('mail:3pane');(async()=>{if(!w.customElements.get('moz-message-bar'))w.eval("ChromeUtils.importESModule('chrome://global/content/elements/moz-message-bar.mjs', {global:'current'})");const result={};for(const type of ['warning','error']){const bar=w.document.createElementNS('http://www.w3.org/1999/xhtml','moz-message-bar');bar.setAttribute('type',type);bar.message='Fixture notification';w.document.documentElement.append(bar);await bar.updateComplete;await new Promise(r=>w.setTimeout(r,80));const s=w.getComputedStyle(bar);result[type]={background:s.backgroundColor,text:s.color,icon:w.getComputedStyle(bar.shadowRoot.querySelector('.icon')).color};bar.remove();}done(result);})().catch(e=>done({error:e.message}));''')
            print('REAL_NOTIFICATION_STYLES',notifications,flush=True)
            assert notifications.get('warning',{}).get('background')==css(expected['warning_bg']),notifications
            assert notifications.get('error',{}).get('background')==css(expected['error_bg']),notifications
            infobars=driver.execute_async_script('''const done=arguments[0];const w=Services.wm.getMostRecentWindow('mail:3pane');(async()=>{const box=new w.MozElements.NotificationBox(stack=>w.document.documentElement.append(stack));const result={};for(const [kind,priority] of [['warning',box.PRIORITY_WARNING_MEDIUM],['error',box.PRIORITY_CRITICAL_MEDIUM]]){const bar=await box.appendNotification('theme-fixture-'+kind,{label:'Fixture notification',priority});await new Promise(r=>w.setTimeout(r,150));const s=w.getComputedStyle(bar);result[kind]={background:s.backgroundColor,text:s.color,type:bar.getAttribute('type')};}box.stack.remove();done(result);})().catch(e=>done({error:e.message}));''')
            print('THUNDERBIRD_INFOBAR_STYLES',infobars,flush=True)
            assert infobars.get('warning',{}).get('background')==css(expected['warning_bg']),infobars
            assert infobars.get('error',{}).get('background')==css(expected['error_bg']),infobars
        print('PASS: live unread/badge/folder/warning/error colors follow the desktop palette in about:3pane',flush=True)
    finally:
        if driver:
            try:driver.quit()
            except Exception:pass
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close()
