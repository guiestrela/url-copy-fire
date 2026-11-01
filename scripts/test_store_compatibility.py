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
            for app in ('firefox', 'thunderbird'):
                filename = release.OUT / f'url-route-{app}-store-review-{release.VERSION}.xpi'
                with ZipFile(filename) as package:
                    cls.manifests[app] = json.loads(package.read('manifest.json'))
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

    def test_firefox_does_not_inherit_thunderbird_branch_limit(self):
        manifest = self.manifests['firefox']
        self.assertNotIn('theme_experiment', manifest)
        self.assertNotIn('strict_max_version', manifest['browser_specific_settings']['gecko'])


if __name__ == '__main__':
    unittest.main()
