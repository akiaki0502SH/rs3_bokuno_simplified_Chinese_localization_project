"""Render a proposed digit set alongside unchanged ROM Chinese glyphs.

This creates preview images and candidate glyph data only. It never writes a
ROM, updates the active mapping, or promotes the candidate font.
"""
from pathlib import Path
import hashlib,json,sys
from PIL import Image,ImageDraw,ImageFont
from font_geometry_v1 import glyph_locations,read_glyph,unpack
from build_font_payloads import encode_pixels

P=Path(__file__).resolve().parents[1]
Q=P/'qa/digit_font_preview_20261017_01'
F=P/'font/digit_preview_20261017_01'
sha=lambda z:hashlib.sha256(z).hexdigest().upper()


def main():
    for dest in [Q,F]:
        assert dest.resolve().is_relative_to(P) and not dest.exists()
    manifest=P/'text/translations/translation_sources_current.json';manifest_raw=manifest.read_bytes()
    m=json.loads(manifest_raw);romfile=P/m['latest_test_ROM']['file'];rom=romfile.read_bytes()
    assert sha(rom)==m['latest_test_ROM']['SHA256']
    mapping=json.loads((P/m['latest_font_mapping']).read_text(encoding='utf8'))
    proposed={};records=[]
    for i in range(10):
        digit=str(i);native=read_glyph(rom,glyph_locations(bytes([0x23,i]))[0]);im=unpack(native)
        box=im.getbbox();w,h=box[2]-box[0],box[3]-box[1]
        x,y=(14-w)//2,14-h
        candidate=Image.new('1',(16,16),0);candidate.paste(im.crop(box),(x,y))
        assert candidate.getbbox()[3]==14 and candidate.getbbox()[2]<=13
        assert candidate.crop(candidate.getbbox()).tobytes()==im.crop(box).tobytes()
        assert sum(candidate.get_flattened_data())==sum(im.get_flattened_data())
        current=read_glyph(rom,glyph_locations(bytes.fromhex(mapping[digit]))[0]);old=unpack(current)
        proposed[digit]=candidate
        records.append({'digit':digit,'current_code':mapping[digit],
            'current_bbox':list(old.getbbox()),'native_reference_code':f'23 {i:02X}',
            'native_reference_bbox':list(box),'candidate_bbox':list(candidate.getbbox()),
            'height':h,'bottom_y':13,'glyph_hex':encode_pixels(candidate).hex(' ').upper(),
            'reference_strokes_preserved':True,'only_repositioned_from_native_reference':True})
    Q.mkdir();F.mkdir()
    glyph_data={'schema':'dialogue-digit-preview-candidate-v1','status':'PREVIEW_ONLY_AWAITING_USER_REVIEW',
        'base_ROM':m['latest_test_ROM'],'candidate':'Native full-size digits, horizontally centred in the 14px dialogue advance and aligned to body bottom y13.',
        'digit_ink_height':10,'CJK_ink_height':12,'normal_dialogue_advance':14,
        'glyphs':records,'ROM_write_performed':False,'active_mapping_changed':False}
    (F/'candidate_digits.json').write_text(json.dumps(glyph_data,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')

    def strip(text,corrected,scale=4):
        raw=Image.new('1',(14*len(text)+2,16),0)
        for i,ch in enumerate(text):
            if corrected and ch in proposed:im=proposed[ch]
            else:
                assert ch in mapping,ch
                im=unpack(read_glyph(rom,glyph_locations(bytes.fromhex(mapping[ch]))[0]))
            raw.paste(im,(14*i,0),im)
        return raw.resize((raw.width*scale,raw.height*scale),Image.Resampling.NEAREST)

    W=1440;H=1090;canvas=Image.new('RGB',(W,H),'#101719');draw=ImageDraw.Draw(canvas)
    fontpath='C:/Windows/Fonts/msyh.ttc'
    title=ImageFont.truetype(fontpath,30);heading=ImageFont.truetype(fontpath,24)
    regular=ImageFont.truetype(fontpath,19);small=ImageFont.truetype(fontpath,16)
    draw.text((42,24),'对白数字字形 · 修正预览',font=title,fill='#f4f2e8')
    draw.text((44,70),'候选采用原生大号数字，统一大小并对齐字底；汉字取自当前 v293',font=regular,fill='#b8c9c9')
    draw.rounded_rectangle((1190,28,1394,72),radius=12,fill='#243a35')
    draw.text((1211,37),'仅预览 · 未写ROM',font=small,fill='#b9dfce')
    left,right=42,737;cw=661
    for x,label,sub in [(left,'当前字形','0、1、2、3、5 偏小，字底高'),
                        (right,'修正候选','0–9 统一为大号字形，字底与汉字齐')]:
        draw.rounded_rectangle((x,108,x+cw,194),radius=12,fill='#1b282b')
        draw.text((x+20,119),label,font=heading,fill='#edf3ed')
        draw.text((x+20,156),sub,font=small,fill='#a5b9b8')

    examples=[('全套数字','0123456789'),('截图原句','大约15年前，'),
              ('数字与汉字','15年前年月日'),('数量','还剩5个'),
              ('次数','第1次战斗'),('等级','等级25'),('连续数字','获得了250奥拉姆')]
    for j,(label,text)in enumerate(examples):
        y=208+j*111
        for x,corrected in [(left,False),(right,True)]:
            draw.rounded_rectangle((x,y,x+cw,y+102),radius=10,fill='#182124')
            draw.text((x+16,y+7),label,font=small,fill='#899d9c')
            tx,ty=x+26,y+32
            # Baseline guides sit immediately below foreground row y13.
            by=ty+14*4
            for gx in range(tx,x+cw-20,10):draw.line((gx,by,gx+4,by),fill='#426e65')
            ink=strip(text,corrected)
            canvas.paste('#f5f1e4',(tx,ty),ink)
    draw.text((44,1000),'数字高 10 像素，汉字高 12 像素；墨点底部均对齐在同一行',font=regular,fill='#d2e2d6')
    draw.text((44,1033),'按 4 倍整数放大。字格和字距沿用当前正文；下方虚线用于比较字底',font=small,fill='#92a7a3')
    main_image=Q/'对白数字字形_修正对照.png';canvas.save(main_image)

    # A compact set of corrected-only samples is useful without old forms
    # nearby; it uses exactly the same candidate data and unchanged Chinese.
    texts=['0123456789','大约15年前，','大小年月日前后','还剩5个，第1次战斗','获得了250奥拉姆']
    out=Image.new('RGB',(1120,600),'#171c1b');d=ImageDraw.Draw(out)
    d.text((30,18),'修正候选 · 与当前汉字搭配',font=heading,fill='#e9efde')
    for j,text in enumerate(texts):
        mask=strip(text,True,5);out.paste('#f5f1e4',(40,70+j*98),mask)
    d.text((32,565),'原生数字，统一字底；仅字模预览，尚未写入ROM',font=small,fill='#98b5a6')
    clean_image=Q/'修正候选_汉字搭配.png';out.save(clean_image)
    proof={'schema':'dialogue-digit-preview-v1','status':'PREVIEW_RENDERED_ROM_UNCHANGED',
        'base_ROM':m['latest_test_ROM'],'candidate_data':(F/'candidate_digits.json').relative_to(P).as_posix(),
        'comparison_image':main_image.relative_to(P).as_posix(),
        'corrected_samples':clean_image.relative_to(P).as_posix(),
        'ROM_write_performed':False,'active_mapping_or_manifest_changed':False,
        'height':10,'baseline_y':13,'CJK_height':12,'CJK_glyphs_unchanged':True,
        'native_digit_shapes_preserved':True,'waiting_for_user_review':True}
    assert romfile.read_bytes()==rom and manifest.read_bytes()==manifest_raw
    (P/'qa/DIGIT_FONT_PREVIEW_20261017_01.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(proof,ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
