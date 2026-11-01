"""Regression checks for target-specific compatibility in actual store packages."""
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import build_store_release as release


class StoreCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory()
        cls.previous_out = release.OUT
        release.OUT = Path(cls.workspace.name)
        try:
            release.build()
            cls.manifests = {}
            cls.configs = {}
            cls.members = {}
            for app in ('firefox', 'thunderbird'):
                candidates = list(release.OUT.glob(f'url-route-{app}-store-review-*.xpi'))
                if len(candidates) != 1:
                    raise AssertionError(f'Expected one {app} package, got {candidates}')
                filename = candidates[0]
                with ZipFile(filename) as package:
                    cls.manifests[app] = json.loads(package.read('manifest.json'))
                    config_source = package.read('target-config.js').decode()
                    cls.configs[app] = json.loads(config_source.split('const URL_ROUTE_CONFIG = ', 1)[1].strip().removesuffix(';'))
                    cls.members[app] = set(package.namelist())
        finally:
            release.OUT = cls.previous_out

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def test_thunderbird_theme_experiment_has_tested_branch_maximum(self):
        manifest = self.manifests['thunderbird']
        self.assertIn('theme_experiment', manifest)
        gecko = manifest['browser_specific_settings']['gecko']
        self.assertEqual(gecko['strict_min_version'], '158.0')
        self.assertEqual(
            gecko.get('strict_max_version'), '158.*',
            'ATN requires strict_max_version for Thunderbird theme experiments',
        )

    def test_thunderbird_store_correction_uses_new_version(self):
        self.assertEqual(self.manifests['thunderbird']['version'], '0.3.1')

    def test_thunderbird_package_contains_target_specific_rendering(self):
        self.assertEqual(self.configs['thunderbird']['target'], 'thunderbird')
        self.assertTrue(self.configs['thunderbird']['semanticMappings'])
        self.assertEqual(self.manifests['thunderbird']['manifest_version'], 2)
        self.assertEqual(self.manifests['thunderbird']['theme_experiment']['colors']['omarchy_frame'], '--lwt-frame')
        self.assertIn('semantic-overrides.css', self.members['thunderbird'])

    def test_firefox_version_is_not_changed_by_thunderbird_correction(self):
        self.assertEqual(self.manifests['firefox']['version'], '0.3.0')
        self.assertEqual(self.configs['firefox']['target'], 'firefox')

    def test_firefox_does_not_inherit_thunderbird_branch_limit(self):
        manifest = self.manifests['firefox']
        self.assertNotIn('theme_experiment', manifest)
        self.assertNotIn('strict_max_version', manifest['browser_specific_settings']['gecko'])


if __name__ == '__main__':
    unittest.main()
