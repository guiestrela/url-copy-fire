"""Verify real Thunderbird chrome and live native-palette updates in a scratch profile."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import tempfile
import omarchy_theme_host as host
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'),prefix='tb-sync-qa-') as tmp:
    scratch=Path(tmp); profile=scratch/'profile'; profile.mkdir()
    palette=scratch/'palette'; palette.mkdir()
    (palette/'colors.toml').write_text('background="#102030"\nforeground="#eaf0ff"\naccent="#ff2fb3"\nlighter_background="#223344"\n')
    (palette/'chromium.theme').write_text('20,55,40')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    prefs={'marionette.port':port,'mail.provider.enabled':False,'mail.shell.checkDefaultClient':False,'mailnews.start_page.enabled':False,'mailnews.start_page.url':'','datareporting.policy.dataSubmissionEnabled':False}
    (profile/'user.js').write_text(''.join(f'user_pref({json.dumps(k)},{json.dumps(v)});\n' for k,v in prefs.items()))
    env=os.environ.copy(); env['URL_ROUTE_THEME_DIR']=str(palette)
    env.update({'XDG_CACHE_HOME':str(scratch/'cache'),'XDG_CONFIG_HOME':str(scratch/'config'),'XDG_DATA_HOME':str(scratch/'data')})
    log=(scratch/'thunderbird.log').open('w')
    proc=subprocess.Popen(['/usr/bin/thunderbird','--headless','--no-remote','--profile',str(profile),'--marionette','--remote-allow-system-access'],env=env,stdout=log,stderr=subprocess.STDOUT)
    driver=None
    try:
        for attempt in range(120):
            if proc.poll() is not None: raise RuntimeError('Isolated Thunderbird exited')
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.3):break
            except OSError:time.sleep(.5)
        else:raise TimeoutError('Thunderbird Marionette not available')
        geckodriver=next((Path.home()/'.cache/selenium/geckodriver/linux64').glob('*/geckodriver'))
        driver=webdriver.Firefox(options=Options(),service=Service(executable_path=str(geckodriver),service_args=['--connect-existing','--marionette-port',str(port),'--allow-system-access']))
        xpi=Path(os.environ.get('TEST_XPI',str(ROOT/'build/url-route-thunderbird-omarchy-sync-0.2.1.xpi')))
        print('INSTALLED',driver.install_addon(str(xpi),temporary=True),flush=True)
        driver.set_context('chrome')
        def check(rgb):
            for attempt in range(40):
                actual=driver.execute_script("let w=Services.wm.getMostRecentWindow('mail:3pane');if(!w)return null;let d=w.document;return {toolbox:w.getComputedStyle(d.getElementById('navigation-toolbox')).backgroundColor, text:w.getComputedStyle(d.getElementById('unifiedToolbar')).color, frame:w.getComputedStyle(d.documentElement).getPropertyValue('--lwt-frame')};")
                if actual and actual['toolbox']==rgb:break
                time.sleep(.5)
            print('THUNDERBIRD_CHROME',actual,'EXPECTED',rgb,flush=True)
            assert actual and actual['toolbox']==rgb,actual
            assert actual['text']=='rgb(255, 255, 255)',actual
        def expected_toolbar():
            channels = host.rgb(host.read_theme(palette)['colors']['toolbar'])
            return 'rgb(' + ', '.join(str(c) for c in channels) + ')'
        check(expected_toolbar())
        (palette/'chromium.theme').write_text('80,30,100')
        check(expected_toolbar())
        print('PASS: Thunderbird native bridge, actual main toolbar, live palette change without reload',flush=True)
    finally:
        if driver:
            try:driver.quit()
            except Exception:pass
        if proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        log.close()
