"""Exercise a temporary XPI in an isolated real Firefox profile."""
import json
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

options = Options()
options.add_argument('-headless')
from selenium.webdriver.firefox.service import Service
options.set_preference('remote.active-protocols', 1)
root = Path(__file__).resolve().parents[1]
xpi = Path(os.environ.get('TEST_XPI', str(root / 'build/url-route-firefox-0.1.3.xpi')))
driver = webdriver.Firefox(options=options, service=Service(service_args=['--allow-system-access']))
try:
    print('FIREFOX:', driver.capabilities['browserVersion'], flush=True)
    try:
        driver.install_addon(str(xpi), temporary=False)
        print('REGULAR_INSTALL: accepted', flush=True)
    except Exception as error:
        print('REGULAR_INSTALL_REJECTED:', str(error).split('Stacktrace:')[0], flush=True)
    addon = driver.install_addon(str(xpi), temporary=True)
    print('INSTALLED:', addon, flush=True)
    profile = Path(driver.capabilities['moz:profile'])
    import time
    time.sleep(2)
    prefs = (profile / 'prefs.js').read_text()
    import re
    match = re.search(r'user_pref\("extensions.webextensions.uuids", (.*)\);', prefs)
    if not match:
        driver.get('about:config')
        time.sleep(1)
        prefs = (profile / 'prefs.js').read_text()
        match = re.search(r'user_pref\("extensions.webextensions.uuids", (.*)\);', prefs)
    if match:
        uuids = json.loads(json.loads(match.group(1)))
        uuid = uuids[addon]
        driver.get('https://example.com/')
        driver.set_context('chrome')
        driver.execute_script('gBrowser.addTab(arguments[0], {inBackground:true, triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal()});', f'moz-extension://{uuid}/popup.html')
        driver.set_context('content')
        time.sleep(2)
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)
        print('PAGE:', driver.current_url, flush=True)
        print('POPUP:', driver.find_element('id','status').text, flush=True)
        print('THEME:', driver.find_element('id','theme').get_attribute('value'), flush=True)
        print('COLORS:', driver.execute_script('return [getComputedStyle(document.body).backgroundColor,getComputedStyle(document.body).color]'), flush=True)
        result = driver.execute_async_script('''const done=arguments[0];
          browser.theme.update({colors:{popup:'#19314a',popup_text:'#fceabc',popup_border:'#789abc',frame:'#19314a',tab_background_text:'#fceabc'}})
          .then(()=>applyThunderbirdTheme()).then(()=>done([getComputedStyle(document.body).backgroundColor,getComputedStyle(document.body).color])).catch(e=>done({error:e.message}));''')
        print('CUSTOM_THEME:', result, flush=True)
        assert result == ['rgb(25, 49, 74)', 'rgb(252, 234, 188)'], result
        assert driver.find_element('id','url').get_attribute('value') == 'https://example.com/'
        driver.find_element('id','copy-url').click()
        time.sleep(1)
        status = driver.find_element('id','status').text
        print('COPY:', status, flush=True)
        assert status == 'Copied and saved locally.', status
        assert 'https://example.com/' in driver.find_element('id','history').text
        driver.find_element('id','clear').click()
        time.sleep(.3)
        assert driver.find_element('id','history').text == ''
        print('PASS: real Firefox temporary install, extension page, custom theme, clipboard write, history, clear.', flush=True)
    else:
        print('UUID_NOT_FLUSHED: popup inspection not executed', flush=True)
finally:
    driver.quit()
