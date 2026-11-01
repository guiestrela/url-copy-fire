"""Exercise the distributed companion installer and Firefox XPI in a scratch HOME."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from zipfile import ZipFile
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/store-release'
GECKODRIVER = next((Path.home() / '.cache/selenium/geckodriver/linux64').glob('*/geckodriver'))
with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'], prefix='portable-companion-') as tmp:
    root = Path(tmp)
    home = root / 'home'
    home.mkdir(mode=0o700)
    native = root / 'companion'
    with ZipFile(OUT / 'url-route-native-companion-0.3.0.zip') as package:
        package.extractall(native)
    installer = native / 'install_omarchy_theme_host.py'
    subprocess.run([sys.executable, str(installer), '--home', str(home)], check=True)
    palette = home / '.local/state/omarchy/current/theme'
    palette.mkdir(parents=True)
    (palette / 'colors.toml').write_text(
        'background="#111c18"\nforeground="#c1c497"\naccent="#509475"\n'
        'yellow="#d4b665"\nred="#d56370"\ngreen="#63b07a"\n'
    )
    (palette / 'chromium.theme').write_text('17,28,24')
    env = os.environ.copy()
    env.pop('URL_ROUTE_THEME_DIR', None)
    env.update({
        'HOME': str(home),
        'XDG_CONFIG_HOME': str(home / '.config'),
        'XDG_CACHE_HOME': str(home / '.cache'),
        'XDG_DATA_HOME': str(home / '.local/share'),
    })
    options = Options()
    options.add_argument('-headless')
    driver = webdriver.Firefox(
        options=options,
        service=Service(
            executable_path=str(GECKODRIVER), env=env,
            service_args=['--allow-system-access'],
        ),
    )
    try:
        driver.install_addon(str(OUT / 'url-route-firefox-store-review-0.3.0.xpi'), temporary=True)
        driver.set_context('chrome')
        result = None
        for _ in range(50):
            result = driver.execute_script(
                "return getComputedStyle(document.getElementById('nav-bar')).backgroundColor;"
            )
            if result == 'rgb(40, 66, 56)':
                break
            time.sleep(.2)
        print('PORTABLE_COMPANION_FIREFOX_TOOLBAR', result, flush=True)
        assert result == 'rgb(40, 66, 56)', result
    finally:
        driver.quit()
    subprocess.run([sys.executable, str(installer), '--home', str(home), '--uninstall'], check=True)
    assert not (home / '.mozilla/native-messaging-hosts/url_route.omarchy_theme.json').exists()
    print('PASS: extracted companion -> portable install -> actual Firefox native theme -> safe uninstall')
