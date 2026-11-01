"""Regression tests for Omarchy -> browser chrome theme mapping."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

class PaletteTests(unittest.TestCase):
    def test_desktop_palette_colors_the_browser_chrome(self):
        path = Path(__file__).with_name('omarchy_theme_host.py')
        self.assertTrue(path.exists(), 'Missing desktop -> browser chrome bridge')
        spec = importlib.util.spec_from_file_location('theme_host', path)
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'colors.toml').write_text('background="#0c0b0d"\nforeground="#D8D1CC"\naccent="#ff2fb3"\nlighter_background="#19181a"\nmode="dark"\n')
            (root/'chromium.theme').write_text('20,55,40\n')
            payload = host.read_theme(root)
            self.assertEqual(payload['colors']['frame'], '#143728')
            self.assertNotEqual(payload['colors']['toolbar'], '#143728')
            self.assertEqual(payload['colors']['toolbar_text'], '#ffffff')
            self.assertEqual(payload['colors']['tab_line'], '#ff2fb3')
            (root/'chromium.theme').write_text('not a color')
            self.assertEqual(host.read_theme(root)['colors']['frame'], '#0c0b0d')
            (root/'colors.toml').write_text('background="javascript:bad"')
            with self.assertRaises(ValueError): host.read_theme(root)

    def test_brave_like_toolbar_is_lighter_with_neutral_text(self):
        path = Path(__file__).with_name('omarchy_theme_host.py')
        spec = importlib.util.spec_from_file_location('theme_host', path)
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'colors.toml').write_text('background="#1a1b26"\nforeground="#a9b1d6"\naccent="#7aa2f7"\nlighter_background="#23273a"\n')
            (root/'chromium.theme').write_text('26,27,38')
            colors = host.read_theme(root)['colors']
            self.assertNotEqual(colors['toolbar'], colors['frame'], 'Toolbar is still as dark as the tab strip')
            self.assertEqual(colors['toolbar_text'], '#ffffff')
            self.assertEqual(colors['icons'], '#ffffff')
            self.assertEqual(colors['tab_selected'], colors['toolbar'])
            self.assertGreaterEqual(host.contrast(colors['toolbar'], colors['frame']), 1.6)
            self.assertGreaterEqual(host.contrast(colors['toolbar_text'], colors['toolbar']), 7)
            self.assertGreaterEqual(host.contrast(colors['toolbar_field_text'], colors['toolbar_field']), 7)
            actual = tuple(int(colors['toolbar'][i:i+2],16) for i in (1,3,5))
            reference = (58,60,84)
            self.assertTrue(all(abs(a-b)<=4 for a,b in zip(actual,reference)), (actual,reference))

    def test_light_and_extreme_palettes_keep_readable_neutral_text(self):
        path = Path(__file__).with_name('omarchy_theme_host.py')
        spec = importlib.util.spec_from_file_location('theme_host', path)
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for base in ('#ffffff', '#f0dfc0', '#000000', '#777777', '#ff0000'):
                (root/'colors.toml').write_text(f'background="{base}"\nforeground="#999999"\naccent="#ff2fb3"\n')
                colors = host.read_theme(root)['colors']
                self.assertGreaterEqual(host.contrast(colors['toolbar'], colors['toolbar_text']), 4.5)
                self.assertGreaterEqual(host.contrast(colors['toolbar_field'], colors['toolbar_field_text']), 4.5)
                self.assertGreaterEqual(host.contrast(colors['popup_highlight'], colors['popup_highlight_text']), 4.5)

if __name__ == '__main__': unittest.main()
