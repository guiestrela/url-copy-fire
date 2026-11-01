#!/usr/bin/python3
"""Read-only native messaging host: stream Omarchy palette changes, never browser data."""
import colorsys
import json
import os
from pathlib import Path
import re
import select
import struct
import sys
import time
import tomllib


def color(value):
    if isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        return value
    raise ValueError('Invalid six-digit theme color')


def rgb(value):
    value = color(value)
    return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))


def hex_color(channels):
    return '#' + ''.join(f'{max(0, min(255, round(channel))):02x}' for channel in channels)


def luminance(value):
    channels = [c / 255 for c in rgb(value)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(first, second):
    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


def neutral_text(background):
    candidates = ('#ffffff', '#202124')
    best = max(candidates, key=lambda candidate: contrast(candidate, background))
    return best if contrast(best, background) >= 4.5 else '#000000'


def toolbar_surface(base):
    # Chromium-style separation: preserve hue while lightening the active surface.
    hue, lightness, saturation = colorsys.rgb_to_hls(*(c / 255 for c in rgb(base)))
    target = 1.7 if lightness <= 0.05 else 1.6
    low, high = lightness, 1.0
    for _ in range(20):
        middle = (low + high) / 2
        candidate = hex_color(c * 255 for c in colorsys.hls_to_rgb(hue, middle, saturation))
        if contrast(base, candidate) >= target:
            high = middle
        else:
            low = middle
    return hex_color(c * 255 for c in colorsys.hls_to_rgb(hue, high, saturation))


def readable_accent(value, background, *other_backgrounds, minimum_ratio=4.5):
    backgrounds = (background, *other_backgrounds)
    def minimum_contrast(candidate):
        return min(contrast(candidate, surface) for surface in backgrounds)
    if minimum_contrast(value) >= minimum_ratio:
        return value
    hue, lightness, saturation = colorsys.rgb_to_hls(*(c / 255 for c in rgb(value)))
    target = (max((0.0, 1.0), key=lambda level: minimum_contrast(
        '#ffffff' if level else '#000000')) if other_backgrounds
        else 1.0 if luminance(background) < 0.18 else 0.0)
    low, high = 0.0, 1.0
    for _ in range(24):
        fraction = (low + high) / 2
        level = lightness + (target - lightness) * fraction
        candidate = hex_color(c * 255 for c in colorsys.hls_to_rgb(hue, level, saturation))
        if minimum_contrast(candidate) >= minimum_ratio:
            high = fraction
        else:
            low = fraction
    level = lightness + (target - lightness) * high
    return hex_color(c * 255 for c in colorsys.hls_to_rgb(hue, level, saturation))


def semantic_palette(palette, colors):
    accent = color(palette.get('accent', colors['tab_line']))
    warning = color(palette.get('yellow', palette.get('orange', accent)))
    error = color(palette.get('red', accent))
    success = color(palette.get('green', accent))
    surface = colors['sidebar']
    def tinted(value):
        return hex_color(a * 0.18 + b * 0.82 for a, b in zip(rgb(value), rgb(surface)))
    warning_bg, error_bg = tinted(warning), tinted(error)
    success_bg = tinted(success)
    success_text = readable_accent(success, surface)
    success_icon = readable_accent(success, surface, success_bg, minimum_ratio=3)
    return {
        'accent': accent, 'accent_text': neutral_text(accent), 'accent_bg': tinted(accent),
        'success_bg': success_bg,
        'success_text': success_text, 'success_icon': success_icon,
        'unread': readable_accent(accent, surface),
        'warning': warning, 'error': error, 'success': success,
        'warning_bg': warning_bg, 'warning_text': readable_accent(warning, warning_bg),
        'error_bg': error_bg, 'error_text': readable_accent(error, error_bg),
    }


def read_theme(root):
    palette = tomllib.loads((root / 'colors.toml').read_text())
    base = color(palette['background'])
    text = color(palette.get('foreground', '#ffffff'))
    accent = color(palette.get('accent', text))
    surface = color(palette.get('lighter_background', base))
    chromium = root / 'chromium.theme'
    if chromium.exists():
        raw = chromium.read_text().strip()
        if re.fullmatch(r'\d{1,3},\s*\d{1,3},\s*\d{1,3}', raw):
            rgb_parts = [int(n.strip()) for n in raw.split(',')]
            if all(0 <= n <= 255 for n in rgb_parts):
                base = '#' + ''.join(f'{n:02x}' for n in rgb_parts)
        elif re.fullmatch(r'#[0-9a-fA-F]{6}', raw):
            base = raw
    toolbar = toolbar_surface(base)
    field = hex_color(a * 0.55 + b * 0.45 for a, b in zip(rgb(base), rgb(toolbar)))
    text = neutral_text(toolbar)
    frame_text = neutral_text(base)
    field_text = neutral_text(field)
    highlight_text = neutral_text(accent)
    colors = dict(
        frame=base, frame_inactive=base, toolbar=toolbar,
        toolbar_text=text, tab_background_text=frame_text, tab_text=text,
        tab_selected=toolbar, tab_line=accent, icons=text,
        toolbar_field=field, toolbar_field_text=field_text,
        toolbar_field_focus=field, toolbar_field_text_focus=field_text,
        toolbar_field_border=field, toolbar_field_border_focus=accent,
        toolbar_field_highlight=accent, toolbar_field_highlight_text=highlight_text,
        toolbar_top_separator=toolbar, toolbar_bottom_separator=field,
        popup=toolbar, popup_text=text, popup_border=field,
        popup_highlight=accent, popup_highlight_text=highlight_text,
        sidebar=field, sidebar_text=field_text, sidebar_border=toolbar,
        sidebar_highlight=accent, sidebar_highlight_text=highlight_text,
        ntp_background=base, ntp_text=frame_text,
        button_background_hover=field, button_background_active=base,
    )
    return {'colors': colors, 'semantic': semantic_palette(palette, colors)}


def send(payload):
    data = json.dumps(payload, separators=(',', ':')).encode()
    sys.stdout.buffer.write(struct.pack('@I', len(data)) + data)
    sys.stdout.buffer.flush()


def main():
    root = Path(os.environ.get('URL_ROUTE_THEME_DIR', str(Path.home() / '.local/state/omarchy/current/theme')))
    previous = None
    while True:
        try:
            theme = read_theme(root)
            message = {'ok': True, 'theme': theme, 'source': 'Omarchy'}
            signature = json.dumps(message, sort_keys=True)
            if signature != previous:
                send(message)
                previous = signature
        except (ValueError, KeyError, OSError, tomllib.TOMLDecodeError) as error:
            message = {'ok': False, 'error': 'Desktop palette unavailable or invalid'}
            signature = json.dumps(message)
            if signature != previous:
                send(message)
                previous = signature
            print(str(error), file=sys.stderr)
        readable, _, _ = select.select([sys.stdin.buffer], [], [], 1)
        if readable:
            header = sys.stdin.buffer.read(4)
            if not header:
                return
            if len(header) != 4:
                return
            size = struct.unpack('@I', header)[0]
            if size > 4096:
                return
            if len(sys.stdin.buffer.read(size)) != size:
                return

if __name__ == '__main__':
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
