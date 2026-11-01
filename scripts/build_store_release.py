"""Build deterministic store-review XPIs from readable source; Python 3.11+, stdlib only."""
import hashlib
import json
from pathlib import Path
import struct
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/store-release'
VERSION = '0.3.0'
EXTENSION_ID = 'url-route-omarchy-sync@local.invalid'
SIZES = (16, 32, 48, 96, 128)


def archive(path, files):
    with ZipFile(path, 'w', ZIP_DEFLATED) as package:
        for name, content in sorted(files.items()):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            package.writestr(info, content)
    with ZipFile(path) as package:
        assert package.testzip() is None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    semantic_map = json.loads((ROOT / 'scripts/thunderbird_semantic_map.json').read_text())
    hashes = {}
    for app in ('firefox', 'thunderbird'):
        is_firefox = app == 'firefox'
        config = {
            'target': app,
            'semanticMappings': {} if is_firefox else {
                key: value['semantic'] for key, value in semantic_map.items()
            },
        }
        manifest = {
            'manifest_version': 3 if is_firefox else 2,
            'name': 'URL Route — Omarchy Theme Sync',
            'version': VERSION,
            'author': 'Guiestrela',
            'homepage_url': 'https://github.com/guiestrela/url-copy-fire',
            'description': 'Sync application colors with Omarchy on Linux. Requires the local companion.',
            'permissions': ['theme', 'nativeMessaging'],
            'background': {'scripts': ['target-config.js', 'theme-sync.js']},
            'icons': {str(size): f'icons/copy-url-{size}.png' for size in SIZES},
            'browser_specific_settings': {'gecko': {
                'id': EXTENSION_ID,
                'strict_min_version': '158.0',
            }},
        }
        action = {
            'default_title': 'Omarchy Theme Sync',
            'default_popup': 'status.html',
            'default_icon': manifest['icons'],
        }
        manifest['action' if is_firefox else 'browser_action'] = action
        if is_firefox:
            manifest['browser_specific_settings']['gecko']['data_collection_permissions'] = {
                'required': ['none'],
            }
        else:
            manifest['background']['persistent'] = True
            manifest['theme_experiment'] = {
                'colors': {
                    'omarchy_frame': '--lwt-frame',
                    'omarchy_frame_inactive': '--lwt-frame-inactive',
                    **{key: value['css'] for key, value in semantic_map.items()},
                },
                'stylesheet': 'semantic-overrides.css',
            }
        files = {
            'manifest.json': json.dumps(manifest, ensure_ascii=False, indent=2).encode(),
            'target-config.js': (
                '"use strict";\n\nconst URL_ROUTE_CONFIG = '
                + json.dumps(config, indent=2) + ';\n'
            ).encode(),
            'theme-sync.js': (ROOT / 'src/theme-sync/background.js').read_bytes(),
            'LICENSE': (ROOT / 'LICENSE').read_bytes(),
        }
        for name in ('status.js', 'status.html', 'status.css'):
            files[name] = (ROOT / 'src/theme-sync' / name).read_bytes()
        if not is_firefox:
            files['semantic-overrides.css'] = (
                ROOT / 'scripts/thunderbird_semantic_overrides.css'
            ).read_bytes()
        for size in SIZES:
            name = f'icons/copy-url-{size}.png'
            image = (ROOT / name).read_bytes()
            assert image[:8] == b'\x89PNG\r\n\x1a\n'
            assert struct.unpack('>II', image[16:24]) == (size, size)
            files[name] = image
        files['icons/LICENSE-OMARCHY.txt'] = (ROOT / 'icons/LICENSE-OMARCHY.txt').read_bytes()
        destination = OUT / app
        destination.mkdir(exist_ok=True)
        for name, content in files.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        package = OUT / f'url-route-{app}-store-review-{VERSION}.xpi'
        hashes[package.name] = archive(package, files)
        print('BUILT', package)
    (OUT / 'SHA256SUMS.txt').write_text(''.join(
        f'{value}  {name}\n' for name, value in sorted(hashes.items())
    ))
    print('Deterministic SHA-256 records written.')


if __name__ == '__main__':
    build()
