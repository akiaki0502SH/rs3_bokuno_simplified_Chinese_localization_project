"""Position body CJK glyphs on a common baseline; retain short-stroke design.

Historical v288 builds keep their old geometry routine for reproducibility.
New body glyphs use this rule after decoding the original font bitmap.
"""
from PIL import Image
from build_font_payloads import encode_pixels
from font_geometry_v1 import unpack,ADVANCE,VISIBLE_COLUMNS

BASELINE=13  # final foreground row, zero-based in the 16x16 storage cell


def normalize_baseline(raw,short_glyph_source_y=None):
    im=unpack(raw);box=im.getbbox()
    if box is None:raise ValueError('Blank CJK glyph')
    w,h=box[2]-box[0],box[3]-box[1]
    if w>VISIBLE_COLUMNS or h>BASELINE+1:raise ValueError('Glyph cannot fit without cropping')
    x=(ADVANCE-w)//2
    # 一 and 二 have deliberately short ink patterns. Their font-design
    # position is not the same as the last ink row of a full body character.
    y=BASELINE+1-h if h>=10 else(box[1]if short_glyph_source_y is None else short_glyph_source_y)
    if y<0 or y+h>16:raise ValueError('Invalid vertical placement')
    out=Image.new('1',(16,16),0);out.paste(im.crop(box),(x,y))
    assert im.crop(box).tobytes()==out.crop(out.getbbox()).tobytes()
    assert sum(im.get_flattened_data())==sum(out.get_flattened_data())
    assert out.getbbox()[2]<=VISIBLE_COLUMNS
    return encode_pixels(out),{'before_bbox':list(box),'after_bbox':list(out.getbbox()),
        'shift':[x-box[0],y-box[1]],'ink_pixels':sum(im.get_flattened_data()),
        'body_baseline':BASELINE if h>=10 else None,
        'short_stroke_design_preserved':h<10,'all_strokes_preserved':True}
