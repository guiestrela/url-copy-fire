"""Package companion and reproducible review sources using explicit file allowlists."""
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import sys
from zipfile import ZipFile

from build_store_release import ROOT, OUT, VERSION, APP_VERSIONS, archive, build

BUILD_NOTES = '''URL Route — Omarchy Theme Sync: source review package

This candidate has not been published or approved by a store.
Main code: MIT License, Copyright (c) 2026 Guiestrela.
Compatibility: Firefox 158.0+; Thunderbird 158.0 through 158.* only.
Support: guilhermestrela@gmail.com
Repository and companion source: https://github.com/guiestrela/url-copy-fire
GitHub account: guiestrela. No packaged GitHub Release has been published yet.
The icon's third-party permission notice is included in icons/LICENSE-OMARCHY.txt.

Build environment: Linux and Python 3.11 or later. No npm package, network
access, minifier or transpiler is required to reproduce the XPI files.
All image assets and readable sources are included.

From this source directory run:
  python3 scripts/build_store_release.py

Compare the generated build/store-release/*.xpi SHA-256 hashes with the
submitted candidates. ZIP timestamps and file order are fixed for reproducibility.
The old prototype/root manifest, backend and unrelated scripts are intentionally
not included. The XPI is a theme integration, not a URL-copying add-on.

Local companion:
  python3 scripts/install_omarchy_theme_host.py
Uninstall only after removing the extension from both applications:
  python3 scripts/install_omarchy_theme_host.py --uninstall

Linux with Omarchy palette files and Python 3.11+ are required for normal use.
The companion is separate from the XPI, uses native messaging, and reads only
local desktop palette files. It is not a system service and opens no port.
No browsing, email, contacts or credentials are required to review functionality.

Optional regression tests:
  node scripts/test_store_background.cjs
  python3 scripts/test_store_compatibility.py
  python3 scripts/test_omarchy_theme_host.py
  python3 scripts/test_thunderbird_semantic_palette.py
  python3 scripts/test_native_host_installer.py

Browser automation additionally requires Selenium, geckodriver and the relevant
installed browser. Run only in an isolated VM/disposable profiles. QA scripts
are review tooling and are not inside the XPI.
'''
COMPANION_NOTES = '''URL Route — Omarchy Theme Sync: Linux local companion

This program is a separate requirement for the Firefox/Thunderbird extension.
Requires Linux, Omarchy and Python 3.11 or later. No root access, system service
or network download is required by the installer or companion.

Install for the current user:
  python3 install_omarchy_theme_host.py

It registers the native application url_route.omarchy_theme for extension ID
url-route-omarchy-sync@local.invalid. Only that extension ID may connect.
Restart/reload the extension if it was open while the helper was unavailable.

Uninstall only after removing the extension from both Firefox and Thunderbird:
  python3 install_omarchy_theme_host.py --uninstall

The program reads Omarchy colors.toml and chromium.theme under the current
user's local state directory and sends only theme colors/status over a local
native messaging pipe. There is no browsing/email access, analytics or network
connection. The extension does not send browser/email content to this helper.

Author: Guiestrela. Main-code license: MIT; see the included LICENSE.
Support: guilhermestrela@gmail.com
Repository and companion source: https://github.com/guiestrela/url-copy-fire
GitHub account: guiestrela. No packaged GitHub Release has been published yet.
'''


def source_inputs():
    fixed = [
        'LICENSE',
        'scripts/build_store_release.py', 'scripts/bundle_store_review.py',
        'scripts/install_omarchy_theme_host.py', 'scripts/omarchy_theme_host.py',
        'scripts/thunderbird_semantic_map.json',
        'scripts/thunderbird_semantic_overrides.css',
        'scripts/test_store_compatibility.py',
        'scripts/test_native_host_installer.py',
        'scripts/test_omarchy_theme_host.py',
        'scripts/test_thunderbird_semantic_palette.py',
        'scripts/qa_omarchy_sync_firefox.py',
        'scripts/qa_omarchy_sync_thunderbird.py',
        'scripts/qa_firefox_tab_border.py',
        'scripts/qa_firefox_original_icon.py',
        'scripts/qa_thunderbird_semantic_colors.py',
        'icons/copy-url-original.png', 'icons/LICENSE-OMARCHY.txt',
    ]
    fixed.extend(f'icons/copy-url-{size}.png' for size in (16, 32, 48, 96, 128))
    fixed.extend(str(p.relative_to(ROOT)) for p in sorted((ROOT / 'src/theme-sync').glob('*')) if p.is_file())
    fixed.extend(str(p.relative_to(ROOT)) for p in sorted((ROOT / 'scripts').glob('test_store_background*.cjs')))
    return sorted(set(fixed))


def main():
    build()
    source = {'url-route-store-source/BUILD-INSTRUCTIONS.txt': BUILD_NOTES.encode()}
    for name in source_inputs():
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f'Missing or unsafe source input: {name}')
        source['url-route-store-source/' + name] = path.read_bytes()
    source_zip = OUT / f'url-route-review-source-{VERSION}.zip'
    archive(source_zip, source)
    companion = {
        'INSTALL.txt': COMPANION_NOTES.encode(),
        'LICENSE': (ROOT / 'LICENSE').read_bytes(),
        'install_omarchy_theme_host.py': (ROOT / 'scripts/install_omarchy_theme_host.py').read_bytes(),
        'omarchy_theme_host.py': (ROOT / 'scripts/omarchy_theme_host.py').read_bytes(),
    }
    companion_zip = OUT / f'url-route-native-companion-{VERSION}.zip'
    archive(companion_zip, companion)
    candidates = [
        OUT / f'url-route-{app}-store-review-{version}.xpi'
        for app, version in APP_VERSIONS.items()
    ]
    expected = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in candidates}
    with tempfile.TemporaryDirectory() as tmp:
        with ZipFile(source_zip) as package:
            package.extractall(tmp)
        extracted = Path(tmp) / 'url-route-store-source'
        subprocess.run([sys.executable, str(extracted / 'scripts/build_store_release.py')], check=True, capture_output=True)
        for name, digest in expected.items():
            rebuilt = extracted / 'build/store-release' / name
            if hashlib.sha256(rebuilt.read_bytes()).hexdigest() != digest:
                raise RuntimeError(f'Source archive does not reproduce {name}')
    # Hash the four distributable artifacts, never a previous review-kit ZIP.
    artifacts = [OUT / name for name in sorted(expected)] + [companion_zip, source_zip]
    records = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts}
    (OUT / 'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name, digest in records.items()))
    (OUT / 'source-reproduction.json').write_text(json.dumps({
        'passed': True, 'source_archive': source_zip.name,
        'reproduced_xpis': expected,
        'companion_archive': companion_zip.name,
    }, indent=2))
    print('SOURCE_ARCHIVE', source_zip)
    print('COMPANION_ARCHIVE', companion_zip)
    print('PASS: extracted source archive reproduces both submitted XPI hashes')


if __name__ == '__main__':
    main()
