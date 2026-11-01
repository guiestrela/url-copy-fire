"""Package the standalone popup test for temporary Firefox installation."""
import json
import subprocess
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
source = root / 'build/url-route-thunderbird-0.1.3.xpi'
target = root / 'build/url-route-firefox-0.1.3.xpi'
with ZipFile(source) as z:
    files = {name: z.read(name) for name in z.namelist()}
manifest = json.loads(files['manifest.json'])
manifest['manifest_version'] = 3
manifest['name'] = 'URL Route — Firefox Test'
manifest['description'] = 'Copy web tab URLs and titles, with local history and Firefox theme colors.'
manifest.pop('applications', None)
manifest['browser_specific_settings'] = {'gecko': {
    'id': 'url-route-firefox-test@local.invalid',
    'strict_min_version': '140.0',
    'data_collection_permissions': {'required': ['none']},
}}
manifest['action'] = manifest.pop('browser_action')
files['manifest.json'] = json.dumps(manifest, indent=2).encode()
files['popup.html'] = files['popup.html'].replace(b'Thunderbird theme', b'Firefox theme')
for name in ('popup.js','theme.js'):
    subprocess.run(['node','--check','-'],input=files[name],check=True)
with ZipFile(target,'w',ZIP_DEFLATED) as z:
    for name,content in files.items():
        z.writestr(name,content)
with ZipFile(target) as z:
    assert z.testzip() is None
    data = json.loads(z.read('manifest.json'))
    assert data['manifest_version'] == 3
    assert 'browser_action' not in data and 'applications' not in data
    assert 'theme.js' in z.namelist()
    assert 'Firefox theme' in z.read('popup.html').decode()
print('Firefox XPI:',target)
print('Verified: archive, MV3 target, theme script, JS syntax.')
