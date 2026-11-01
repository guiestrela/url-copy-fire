#!/usr/bin/env python3
"""Isolated installer tests; every fake home and subprocess HOME is under TMPDIR."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
INSTALLER = SCRIPTS / 'install_omarchy_theme_host.py'
SOURCE = SCRIPTS / 'omarchy_theme_host.py'


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='native-installer-', dir=os.environ['TMPDIR'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home with spaces'
        self.home.mkdir()
        self.lib = self.home / '.local/lib/url-route-omarchy-sync'
        self.registration = self.home / '.mozilla/native-messaging-hosts/url_route.omarchy_theme.json'
        self.launcher = self.lib / 'omarchy_theme_host'

    def run_installer(self, *args, ok=True, script=INSTALLER):
        env = dict(os.environ, HOME=str(self.home), PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, str(script), '--home', str(self.home), *args],
                                env=env, capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def snapshot(self):
        return {str(p.relative_to(self.home)): (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
                for p in self.home.rglob('*') if p.is_file()}

    def test_different_registration_and_helpers_are_backed_up_without_clobbering(self):
        self.lib.mkdir(parents=True)
        self.registration.parent.mkdir(parents=True)
        originals = {self.registration: b'{"unrelated": true}',
                     self.launcher: b'old launcher', self.lib / SOURCE.name: b'old source'}
        for path, data in originals.items():
            path.write_bytes(data)
            path.with_name(path.name + '.bak').write_bytes(b'older backup')
        self.run_installer()
        for path, data in originals.items():
            self.assertEqual(path.with_name(path.name + '.bak').read_bytes(), b'older backup')
            backup = path.with_name(path.name + '.bak.1')
            self.assertTrue(backup.exists(), 'different file must be backed up')
            self.assertEqual(backup.read_bytes(), data)
        before = self.snapshot()
        self.run_installer()
        self.assertEqual(before, self.snapshot())

    def test_rejects_symlinks_at_every_target_level_without_writes(self):
        relatives = ['.', '.local', '.local/lib', '.local/lib/url-route-omarchy-sync',
                     '.mozilla', '.mozilla/native-messaging-hosts',
                     '.mozilla/native-messaging-hosts/url_route.omarchy_theme.json',
                     '.local/lib/url-route-omarchy-sync/omarchy_theme_host',
                     '.local/lib/url-route-omarchy-sync/omarchy_theme_host.py']
        for index, relative in enumerate(relatives):
            with self.subTest(relative=relative):
                home = self.root / ('symlink-home-' + str(index))
                outside = self.root / ('outside-' + str(index))
                outside.mkdir()
                (outside / 'keep').write_bytes(b'untouched')
                target = home if relative == '.' else home / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(outside, target_is_directory=True)
                result = self.run_installer('--home', str(home), ok=False)
                self.assertIn('unsafe', result.stderr.lower())
                self.assertEqual(sorted(p.name for p in outside.iterdir()), ['keep'])
                self.assertFalse((home / '.local/lib/url-route-omarchy-sync/omarchy_theme_host.py').is_file())

    def test_rejects_dangling_symlink_and_nonregular_target(self):
        self.registration.parent.mkdir(parents=True)
        self.registration.symlink_to(self.root / 'missing')
        self.run_installer(ok=False)
        self.assertTrue(self.registration.is_symlink())
        self.registration.unlink()
        self.registration.mkdir()
        self.run_installer(ok=False)
        self.assertFalse(self.lib.exists())

    def test_rejects_unsafe_home_permissions(self):
        self.home.chmod(0o777)
        self.run_installer(ok=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_python_before_311_fails_before_writing(self):
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('installer_under_test', INSTALLER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module.sys, 'version_info', (3, 10, 99)):
            with self.assertRaisesRegex((ValueError, RuntimeError), '3.11'):
                module.install(self.home)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_missing_sibling_source_fails_before_writing(self):
        copied = self.root / INSTALLER.name
        shutil.copyfile(INSTALLER, copied)
        self.run_installer(script=copied, ok=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_uninstall_removes_matching_files_only_and_is_repeatable(self):
        self.run_installer()
        unrelated = self.lib / 'keep.txt'
        unrelated.write_bytes(b'unrelated')
        backup = self.launcher.with_name(self.launcher.name + '.bak')
        backup.write_bytes(b'original')
        self.run_installer('--uninstall')
        self.assertFalse(self.registration.exists())
        self.assertFalse(self.launcher.exists())
        self.assertFalse((self.lib / SOURCE.name).exists())
        self.assertEqual(unrelated.read_bytes(), b'unrelated')
        self.assertEqual(backup.read_bytes(), b'original')
        before = self.snapshot()
        self.run_installer('--uninstall')
        self.assertEqual(before, self.snapshot())

    def test_uninstall_does_nothing_for_different_registration(self):
        self.run_installer()
        self.registration.write_text('{"name": "somebody_else"}')
        before = self.snapshot()
        self.run_installer('--uninstall')
        self.assertEqual(before, self.snapshot())

    def test_uninstall_preserves_modified_helper(self):
        self.run_installer()
        installed_source = self.lib / SOURCE.name
        installed_source.write_bytes(b'changed by user')
        self.run_installer('--uninstall')
        self.assertEqual(installed_source.read_bytes(), b'changed by user')
        self.assertFalse(self.registration.exists())
        self.assertFalse(self.launcher.exists())

    def test_uninstall_without_receipt_is_noop(self):
        self.lib.mkdir(parents=True)
        self.registration.parent.mkdir(parents=True)
        self.registration.write_bytes(b'unrelated')
        self.launcher.write_bytes(b'unrelated')
        before = self.snapshot()
        self.run_installer('--uninstall')
        self.assertEqual(before, self.snapshot())

    def test_uninstall_without_sibling_source_uses_receipt(self):
        self.run_installer()
        copied = self.root / INSTALLER.name
        shutil.copyfile(INSTALLER, copied)
        self.run_installer('--uninstall', script=copied)
        self.assertFalse(self.registration.exists())
        self.assertFalse(self.launcher.exists())

    def test_rejects_receipt_symlink_and_hard_linked_helper(self):
        self.lib.mkdir(parents=True)
        outside = self.root / 'outside'
        outside.write_bytes(b'unchanged')
        receipt = self.lib / '.install-receipt.json'
        receipt.symlink_to(outside)
        self.run_installer(ok=False)
        self.assertFalse(self.registration.exists())
        receipt.unlink()
        os.link(outside, self.launcher)
        self.run_installer(ok=False)
        self.assertEqual(outside.read_bytes(), b'unchanged')
        self.assertFalse(self.registration.exists())

    def test_uninstall_with_invalid_receipt_preserves_everything(self):
        self.run_installer()
        receipt = self.lib / '.install-receipt.json'
        for bad in [b'not json', b'null', b'[]', b'{"format": "unknown", "sha256": {}}']:
            with self.subTest(receipt=bad):
                receipt.write_bytes(bad)
                before = self.snapshot()
                self.run_installer('--uninstall')
                self.assertEqual(self.snapshot(), before)

    def test_uninstall_missing_registration_preserves_helpers(self):
        self.run_installer()
        self.registration.unlink()
        before = self.snapshot()
        self.run_installer('--uninstall')
        self.assertEqual(self.snapshot(), before)

    def test_uninstall_rejects_symlink_without_deleting_anything(self):
        self.run_installer()
        self.launcher.unlink()
        outside = self.root / 'external'
        outside.write_bytes(b'external')
        self.launcher.symlink_to(outside)
        before = self.registration.read_bytes()
        self.run_installer('--uninstall', ok=False)
        self.assertEqual(self.registration.read_bytes(), before)
        self.assertEqual(outside.read_bytes(), b'external')

    def test_install_with_permissive_umask_creates_private_safe_directories(self):
        spec = importlib.util.spec_from_file_location('installer_umask_test', INSTALLER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        previous = os.umask(0)
        try:
            try:
                module.install(self.home)
            except (OSError, ValueError) as error:
                self.fail('safe installation must work even with umask 000: ' + str(error))
        finally:
            os.umask(previous)
        for relative in ['.local', '.local/lib', '.local/lib/url-route-omarchy-sync',
                         '.mozilla', '.mozilla/native-messaging-hosts']:
            self.assertEqual((self.home / relative).stat().st_mode & 0o777, 0o700)

    def test_install_is_portable_executable_and_idempotent(self):
        self.run_installer()
        manifest = json.loads(self.registration.read_text())
        self.assertEqual(manifest['name'], 'url_route.omarchy_theme')
        self.assertEqual(manifest['type'], 'stdio')
        self.assertEqual(manifest['allowed_extensions'], ['url-route-omarchy-sync@local.invalid'])
        self.assertEqual(manifest['path'], str(self.launcher))
        self.assertEqual((self.lib / SOURCE.name).read_bytes(), SOURCE.read_bytes())
        self.assertTrue(os.access(self.launcher, os.X_OK))
        # Native messaging framing actually comes from the installed launcher.
        env = dict(os.environ, HOME=str(self.home))
        process = subprocess.Popen([str(self.launcher)], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            output, error = process.communicate(b'', timeout=5)
            self.assertEqual(process.returncode, 0, error)
            self.assertGreaterEqual(len(output), 4)
            length = int.from_bytes(output[:4], 'little')
            self.assertIsInstance(json.loads(output[4:4 + length]), dict)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        before = self.snapshot()
        self.run_installer()
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
