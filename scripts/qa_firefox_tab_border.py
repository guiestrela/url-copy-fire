"""Check the selected Firefox tab border blends with its themed background."""
import os
from pathlib import Path
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'],prefix='tab-outline-') as tmp:
    palette=Path(tmp)
    (palette/'colors.toml').write_text('background="#111c18"\nforeground="#c1c497"\naccent="#509475"\nlighter_background="#23372b"\n')
    (palette/'chromium.theme').write_text('17,28,24')
    os.environ['URL_ROUTE_THEME_DIR']=tmp
    options=Options();options.add_argument('-headless')
    driver=webdriver.Firefox(options=options,service=Service(service_args=['--allow-system-access']))
    try:
        xpi=Path(os.environ.get('TEST_XPI',str(root/'build/url-route-firefox-omarchy-sync-0.2.3.xpi')))
        driver.install_addon(str(xpi),temporary=True)
        driver.set_context('chrome')
        previous=None
        for base in ('17,28,24','80,30,100'):
            (palette/'chromium.theme').write_text(base)
            for attempt in range(40):
                result=driver.execute_script('''const tab=gBrowser.selectedTab.querySelector('.tab-background');const s=getComputedStyle(tab);return {fill:s.backgroundColor,outline:s.outlineColor,outlineWidth:s.outlineWidth,outlineStyle:s.outlineStyle,themeLine:getComputedStyle(document.documentElement).getPropertyValue('--lwt-tab-line-color'),fieldFocus:getComputedStyle(document.documentElement).getPropertyValue('--toolbar-field-focus-border-color')};''')
                if result['themeLine'] and (previous is None or result['fill']!=previous):break
                time.sleep(.25)
            print('TAB_BORDER',result,flush=True)
            assert result['outline']==result['fill'], 'Selected tab still has a contrasting border'
            previous=result['fill']
        image=Path(os.environ['TMPDIR'])/'firefox-selected-tab-no-accent-border.png'
        driver.find_element('css selector','.tabbrowser-tab[selected] .tab-background').screenshot(str(image))
        print('SCREENSHOT',image)
        print('PASS: selected-tab border follows theme fill for green and purple palettes')
    finally:
        driver.quit()
