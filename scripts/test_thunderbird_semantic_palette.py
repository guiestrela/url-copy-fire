"""Semantic Thunderbird accents must come from the desktop palette, not fixed blue."""
import json
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('host',Path(__file__).with_name('omarchy_theme_host.py'))
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
class SemanticPaletteTests(unittest.TestCase):
    def test_semantic_colors_follow_palette_and_remain_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'colors.toml').write_text('background="#111c18"\nforeground="#c1c497"\naccent="#509475"\nyellow="#d4b665"\nred="#d56370"\ngreen="#63b07a"\n')
            payload=host.read_theme(root)
            self.assertIn('semantic',payload,'Unread, badge and warning colors are not synchronized')
            colors=payload['colors'];semantic=payload['semantic']
            self.assertEqual(semantic['accent'],'#509475')
            self.assertEqual(semantic['warning'],'#d4b665')
            self.assertEqual(semantic['error'],'#d56370')
            self.assertGreaterEqual(host.contrast(semantic['unread'],colors['sidebar']),4.5)
            self.assertGreaterEqual(host.contrast(semantic['accent'],semantic['accent_text']),4.5)
            self.assertGreaterEqual(host.contrast(semantic['warning_bg'],semantic['warning_text']),4.5)
            self.assertGreaterEqual(host.contrast(semantic['error_bg'],semantic['error_text']),4.5)
            (root/'colors.toml').write_text('background="#f8f5ec"\nforeground="#202124"\naccent="#8064b8"\nyellow="#a87919"\nred="#a32244"\n')
            light=host.read_theme(root)
            self.assertEqual(light['semantic']['accent'],'#8064b8')
            self.assertGreaterEqual(host.contrast(light['semantic']['unread'],light['colors']['sidebar']),4.5)

    def test_success_consumers_remain_readable_on_light_and_dark_surfaces(self):
        mapping = json.loads(Path(__file__).with_name('thunderbird_semantic_map.json').read_text())
        fixtures = (
            ('#ffffff', '#ffffff'),  # White "green" on white previously had contrast 1.
            ('#111c18', '#63b07a'),
            ('#f8f5ec', '#b0eabb'),
            ('#000000', '#000000'),
        )
        icons = ('omarchy_marker_success', 'omarchy_notification_success_icon',
                 'omarchy_unread_dot_fill', 'omarchy_unread_dot_stroke', 'omarchy_sent')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for background, green in fixtures:
                with self.subTest(background=background, green=green):
                    (root / 'colors.toml').write_text(
                        f'background="{background}"\nforeground="#202124"\n'
                        f'accent="#509475"\ngreen="{green}"\n')
                    payload = host.read_theme(root)
                    semantic, colors = payload['semantic'], payload['colors']
                    self.assertEqual(semantic['success'], green, 'Keep the raw background accent')
                    self.assertEqual(mapping['omarchy_success_text']['semantic'], 'success_text')
                    self.assertGreaterEqual(host.contrast(semantic['success_text'], colors['sidebar']), 4.5)
                    for background_color in (colors['sidebar'], semantic['success_bg']):
                        self.assertGreaterEqual(host.contrast(semantic['success_icon'], background_color), 3)
                    for key in icons:
                        self.assertEqual(mapping[key]['semantic'], 'success_icon', key)
                    self.assertEqual(mapping['omarchy_notification_success_bg']['semantic'], 'success_bg')

if __name__=='__main__':unittest.main()
