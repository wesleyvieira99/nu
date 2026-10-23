def luminance(color):
    if len(color) != 3 or any(not 0 <= x <= 1 for x in color):
        raise ValueError('Expected three channels in [0, 1]')
    linear = [x / 12.92 if x <= .04045 else
              ((x + .055) / 1.055) ** 2.4 for x in color]
    return sum(x * w for x, w in zip(linear, (.2126, .7152, .0722)))


def contrast(first, second):
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + .05) / (low + .05)

black = rgb('#000000')
white = rgb('#FFFFFF')
assert contrast(black, white) == 21
assert contrast(white, black) == 21
assert contrast(black, black) == 1
assert text_check('#777777', '#FFFFFF')['passes'] is False
assert text_check('#767676', '#FFFFFF')['passes'] is True