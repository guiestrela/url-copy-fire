"""Verify build icon identity against the installed original Chromium asset."""
import hashlib
import json
from pathlib import Path
import unittest
from zipfile import ZipFile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/usr/share/omarchy/default/chromium/extensions/copy-url/icon.png')
class OriginalIconTests(unittest.TestCase):
    def test_firefox_and_thunderbird_embed_the_exact_original(self):
        expected=SOURCE.read_bytes()
        for app in ('firefox','thunderbird'):
            package=ROOT/'build'/f'url-route-{app}-omarchy-sync-0.2.2.xpi'
            self.assertTrue(package.is_file(),f'New icon package missing: {app}')
            with ZipFile(package) as z:
                manifest=json.loads(z.read('manifest.json'))
                action=manifest['action' if app=='firefox' else 'browser_action']
                self.assertEqual(action['default_icon'],manifest['icons'])
                self.assertEqual(set(manifest['icons']),{'16','32','48','96','128'})
                for icon in set(manifest['icons'].values()):
                    self.assertEqual(z.read(icon),expected)
                self.assertEqual(manifest['permissions'],['theme','nativeMessaging'])
                previous = ROOT/'build'/f'url-route-{app}-omarchy-sync-0.2.1.xpi'
                if previous.exists():
                    with ZipFile(previous) as old:
                        for script in ('theme-sync.js','status.js','status.css','status.html'):
                            self.assertEqual(z.read(script),old.read(script),'Theme behavior changed during icon-only update')
        print('Exact original PNG SHA-256:',hashlib.sha256(expected).hexdigest())
    def test_original_alpha_is_preserved_in_project(self):
        target=ROOT/'icons/copy-url-original.png'
        self.assertTrue(target.is_file(),'Original asset has not been copied')
        self.assertEqual(target.read_bytes(),SOURCE.read_bytes())
        with Image.open(target) as im:
            self.assertEqual(im.mode,'RGBA')
            self.assertEqual(im.size,(300,300))

if __name__=='__main__':unittest.main()
