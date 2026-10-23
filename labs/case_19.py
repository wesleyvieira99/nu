"""Synthetic color/semantic checks; not an accessibility certification.
Run: python3 work/v2/labs/case_19.py
No Flutter runtime, screenshot capture, or Nubank code is used.
"""
from dataclasses import dataclass
import json
import unittest


def rgb(value):
    if len(value) != 7 or not value.startswith('#'):
        raise ValueError('Expected #RRGGBB')
    try:
        return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))
    except ValueError as error:
        raise ValueError('Invalid color') from error


def luminance(color):
    if len(color) != 3 or any(not 0 <= x <= 1 for x in color):
        raise ValueError('Expected three channels in [0, 1]')
    linear = [x / 12.92 if x <= .04045 else
              ((x + .055) / 1.055) ** 2.4 for x in color]
    return sum(x * w for x, w in zip(linear, (.2126, .7152, .0722)))


def contrast(first, second):
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + .05) / (low + .05)


def composite(foreground, background, alpha):
    if not 0 <= alpha <= 1:
        raise ValueError('Alpha must be in [0, 1]')
    luminance(foreground)
    luminance(background)
    return tuple(alpha * f + (1 - alpha) * b
                 for f, b in zip(foreground, background))


def text_check(text, surface, large=False):
    ratio = contrast(rgb(text), rgb(surface))
    minimum = 3.0 if large else 4.5
    return {'ratio': round(ratio, 4), 'passes': ratio >= minimum}


@dataclass(frozen=True)
class Status:
    label: str
    icon_name: str
    color: str


def status_has_redundant_cues(status):
    return bool(status.label.strip() and status.icon_name.strip())


class ContrastTests(unittest.TestCase):
    def test_black_white(self):
        self.assertAlmostEqual(contrast(rgb('#000000'), rgb('#FFFFFF')), 21)
    def test_symmetry(self):
        a, b = rgb('#48136A'), rgb('#FAFAFA')
        self.assertEqual(contrast(a, b), contrast(b, a))
    def test_same_color(self):
        self.assertEqual(contrast(rgb('#888888'), rgb('#888888')), 1)
    def test_small_text_boundary(self):
        self.assertFalse(text_check('#777777', '#FFFFFF')['passes'])
        self.assertTrue(text_check('#767676', '#FFFFFF')['passes'])
    def test_large_text(self):
        self.assertTrue(text_check('#777777', '#FFFFFF', True)['passes'])
    def test_composite_endpoints(self):
        a, b = rgb('#FFFFFF'), rgb('#000000')
        self.assertEqual(composite(a, b, 0), b)
        self.assertEqual(composite(a, b, 1), a)
    def test_transparency_lowers_this_contrast(self):
        dark, light = rgb('#000000'), rgb('#FFFFFF')
        self.assertLess(contrast(composite(dark, light, .2), light), 4.5)
    def test_invalid_hex(self):
        for value in ('white', '#GGGGGG', '#FFF'):
            with self.assertRaises(ValueError):
                rgb(value)
    def test_invalid_channels(self):
        with self.assertRaises(ValueError):
            luminance((1.2, 0, 0))
    def test_invalid_alpha(self):
        with self.assertRaises(ValueError):
            composite((0, 0, 0), (1, 1, 1), -1)
    def test_status_cues(self):
        self.assertTrue(status_has_redundant_cues(
            Status('Pagamento pendente', 'clock', '#A06000')))
    def test_color_alone_fails(self):
        self.assertFalse(status_has_redundant_cues(
            Status('', '', '#00AA00')))


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContrastTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'normal_gray': text_check('#777777', '#FFFFFF'),
                      'darker_gray': text_check('#767676', '#FFFFFF'),
                      'dark_example': text_check('#F6F1FA', '#160B22')},
                     ensure_ascii=False, indent=2))
    raise SystemExit(not result.wasSuccessful())
