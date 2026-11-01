"""Verify Firefox uses the original Copy URL asset on its actual toolbar button."""
from pathlib import Path
import os
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

root=Path(__file__).resolve().parents[1]
options=Options();options.add_argument('-headless')
driver=webdriver.Firefox(options=options,service=Service(service_args=['--allow-system-access']))
try:
    package=Path(os.environ.get('TEST_XPI',str(root/'build/url-route-firefox-omarchy-sync-0.2.2.xpi')))
    ident=driver.install_addon(str(package),temporary=True)
    driver.set_context('chrome')
    result=None
    for _ in range(30):
        result=driver.execute_script('''
          const id=arguments[0].toLowerCase().replace(/[^a-z0-9_-]/g,'_')+'-browser-action';
          CustomizableUI.addWidgetToArea(id,CustomizableUI.AREA_NAVBAR);
          const button=document.getElementById(id);
          const image=button?.querySelector('.toolbarbutton-icon');
          if(!image)return null;
          return {id,src:getComputedStyle(image).listStyleImage,width:image.getBoundingClientRect().width};
        ''',ident)
        if result and 'copy-url-' in result['src']:break
        time.sleep(.3)
    print('FIREFOX_TOOLBAR_ICON',result,flush=True)
    assert result and 'copy-url-' in result['src'],result
    assert result['width']>0,result
    shot=Path(os.environ['TMPDIR'])/'firefox-copy-url-original-icon.png'
    driver.find_element('id',result['id']).screenshot(str(shot))
    print('SCREENSHOT',shot)
    print('PASS: original Chromium PNG selected and rendered by the real Firefox toolbar button')
finally:
    driver.quit()
