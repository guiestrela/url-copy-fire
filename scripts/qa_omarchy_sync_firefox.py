"""Verify actual application chrome colors applied by the native desktop bridge."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
import omarchy_theme_host as host

parser=argparse.ArgumentParser()
parser.add_argument('--fixture',action='store_true')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
fixture=tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) if args.fixture else None
if fixture:
    palette=Path(fixture.name)
    (palette/'colors.toml').write_text('background="#102030"\nforeground="#eaf0ff"\naccent="#ff2fb3"\nlighter_background="#223344"\n')
    (palette/'chromium.theme').write_text('20,55,40')
    os.environ['URL_ROUTE_THEME_DIR']=str(palette)
else:
    os.environ.pop('URL_ROUTE_THEME_DIR',None)
    palette=Path.home()/'.local/state/omarchy/current/theme'
expected=host.read_theme(palette)['colors']
options=Options();options.add_argument('-headless')
driver=webdriver.Firefox(options=options,service=Service(service_args=['--allow-system-access']))
try:
    package=Path(os.environ.get('TEST_XPI',str(root/'build/url-route-firefox-omarchy-sync-0.2.1.xpi')))
    addon=driver.install_addon(str(package),temporary=True)
    print('INSTALLED',addon,flush=True)
    def check_chrome(expected):
        driver.set_context('chrome')
        for attempt in range(30):
            actual=driver.execute_script("return {toolbar:getComputedStyle(document.getElementById('nav-bar')).backgroundColor,text:getComputedStyle(document.getElementById('nav-bar')).color,field:getComputedStyle(document.documentElement).getPropertyValue('--toolbar-field-background-color').trim(),frame:document.documentElement.style.getPropertyValue('--lwt-accent-color')};")
            h=expected['toolbar'].lstrip('#')
            rgb='rgb('+', '.join(str(int(h[i:i+2],16)) for i in (0,2,4))+')'
            if actual['toolbar']==rgb: break
            time.sleep(.5)
        print('CHROME',json.dumps(actual),'EXPECTED',rgb,flush=True)
        assert actual['toolbar']==rgb, actual
        text_rgb = 'rgb(' + ', '.join(str(c) for c in host.rgb(expected['toolbar_text'])) + ')'
        assert actual['text'] == text_rgb, actual
        assert actual['field'] != actual['toolbar'], actual
    check_chrome(expected)
    if fixture:
        (palette/'chromium.theme').write_text('80,30,100')
        check_chrome(host.read_theme(palette)['colors'])
        print('PASS: live palette change updates real Firefox toolbar without reload',flush=True)
    print('PASS: native bridge -> theme.update -> real Firefox toolbar',flush=True)
finally:
    driver.quit()
    if fixture: fixture.cleanup()
