"""Lossless placement of full CJK glyphs in RS3's actual character cell.

The ROM stores 16x16 tiles. Dialogue advances 14 pixels (some cached menus
use 16px cells). Some following glyphs clear column 13 of the preceding one,
so columns 0..12 are the common safe footprint across the drawing paths.
Use one rounding rule for both source fonts; do not resize or thicken strokes.
Punctuation, icons, half-width text and historical composite pairs need their
own typography and must not be passed to this full-character operation.
"""
from PIL import Image
from build_font_payloads import encode_pixels

STORAGE_SIZE = (16, 16)
ADVANCE = 14
VISIBLE_COLUMNS = 13


def is_cjk(atom):
    return len(atom) == 1 and (0x3400 <= ord(atom) <= 0x9FFF or
                              0xF900 <= ord(atom) <= 0xFAFF)


def unpack(raw):
    if len(raw) != 32:
        raise ValueError('A glyph must contain four 8x8 one-bit tiles')
    im = Image.new('1', STORAGE_SIZE, 0)
    for y in range(16):
        for x in range(16):
            im.putpixel((x, y), (raw[(y // 8 * 2 + x // 8) * 8 + y % 8]
                                 >> (7 - x % 8)) & 1)
    return im


def normalize_cjk(raw):
    im = unpack(raw)
    box = im.getbbox()
    if box is None:
        raise ValueError('Blank CJK glyph')
    width, height = box[2] - box[0], box[3] - box[1]
    if width > VISIBLE_COLUMNS:
        raise ValueError('Full glyph exceeds native visible width; do not crop')
    # Floor for both axes: odd/even dimensions can differ by at most half a
    # pixel from the shared cell centre (6.5, 7.5). A 12px glyph starts at x1.
    x, y = (ADVANCE - width) // 2, (STORAGE_SIZE[1] - height) // 2
    out = Image.new('1', STORAGE_SIZE, 0)
    out.paste(im.crop(box), (x, y))
    assert out.getbbox()[2] <= VISIBLE_COLUMNS
    assert sum(im.get_flattened_data()) == sum(out.get_flattened_data())
    assert im.crop(box).tobytes() == out.crop(out.getbbox()).tobytes()
    return encode_pixels(out), {
        'before_bbox': list(box), 'after_bbox': list(out.getbbox()),
        'shift': [x - box[0], y - box[1]],
        'ink_pixels': sum(im.get_flattened_data()),
        'previous_clipped_pixels': sum(im.getpixel((xx, yy))
                                       for yy in range(16)
                                       for xx in range(VISIBLE_COLUMNS, 16)),
        'all_strokes_preserved': True,
    }


def glyph_locations(code):
    """Return each upper/lower ROM tile address for a native or virtual code."""
    if len(code) == 1 and 0x50 <= code[0] <= 0xFF:
        bases, slot = [0x2C0000], code[0] - 0x50
    elif len(code) == 2 and code[0] in (0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x19):
        bases = [0x780000, 0x7D0000]
        slot = (7 if code[0] == 0x19 else code[0] - 0x10) * 256 + code[1]
    elif len(code) == 2 and 0x20 <= code[0] <= 0x23:
        bases, slot = [0x2C0000], (code[0] - 0x20) * 256 + code[1]
    elif len(code) == 2 and code[0] in (0x18, 0x46):
        bases, slot = [0x608000 if code[0] == 0x18 else 0x60A000], code[1]
    else:
        raise ValueError('Unsupported font code: ' + code.hex(' '))
    off = slot // 8 * 256 + slot % 8 * 16
    return [(base + off, base + off + 128) for base in bases]


def read_glyph(rom, location):
    top, bottom = location
    return rom[top:top + 16] + rom[bottom:bottom + 16]
