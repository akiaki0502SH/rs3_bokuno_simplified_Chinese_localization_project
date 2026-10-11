"""Reproduce right-edge loss in the original tavern drawing path.

Only font/display fixtures are changed, not gameplay state. The first three
full glyphs survive intact in the old build; the final one loses x13 when the
following native full stop is drawn. Two fixtures separately prove 吗 and 娜.
"""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image, ImageDraw, ImageFont
from font_geometry_v1 import glyph_locations, read_glyph, unpack
from verify_v288_font_geometry_v1 import run

P = Path(__file__).resolve().parents[1]
D = P/'qa/font_geometry_v288_20261012_01'
rd = lambda f: json.loads((P/f).read_text(encoding='utf8'))
sha = lambda z: hashlib.sha256(z).hexdigest().upper()


def missing_pixels(image, raw, origin, color=(255,255,255)):
    glyph=unpack(raw)
    return [(x,y) for y in range(16) for x in range(16)
            if glyph.getpixel((x,y)) and image.getpixel((origin[0]+x,origin[1]+y))!=color]


def main():
    build=rd('qa/V288_FONT_GEOMETRY_BUILD_20261012_01.json')
    m=rd('text/translations/translation_sources_before_v288_20261012_01.json')
    mp={k:bytes.fromhex(v) for k,v in rd(m['latest_font_mapping']).items()}
    state='user_saves/snes9x_20261009_2330_v270_tavern_feedback/bokuno_cn_v10ap270_private_test.001'
    actions=P/'qa/v272_focused_001_welcome_20261010_01_actions.json'
    tests=[]
    for last,phrase in [('娜','吗娜吗娜'),('吗','娜吗娜吗')]:
        for label,key in [('base','base_ROM'),('candidate','ROM')]:
            b=(P/build[key]).read_bytes();r=bytearray(b);allowed=set()
            for target,ch in zip('欢迎光临',phrase):
                raw=read_glyph(b,glyph_locations(mp[ch])[0])
                for top,bottom in glyph_locations(mp[target]):
                    r[top:top+16]=raw[:16];r[bottom:bottom+16]=raw[16:]
                    allowed.update(range(top,top+16));allowed.update(range(bottom,bottom+16))
            for site in [0xFFDC,0x40FFDC]:
                r[site:site+4]=bytes.fromhex('FF FF 00 00');allowed.update(range(site,site+4))
            cs=sum(r)&65535
            for site in [0xFFDC,0x40FFDC]:r[site:site+4]=(cs^65535).to_bytes(2,'little')+cs.to_bytes(2,'little')
            assert all(i in allowed for i,(x,y)in enumerate(zip(b,r))if x!=y)
            fixture=P/f'roms/work/bokuno_cn_diag_v288_native_{last}_{label}_20261012_01.smc'
            if fixture.exists():assert fixture.read_bytes()==r
            else:fixture.write_bytes(r)
            prefix=D/('native_'+last+'_'+label)
            if not prefix.with_suffix('.json').exists():
                prefix=run(fixture,state,actions,'native_'+last+'_'+label)
            assert rd(prefix.with_suffix('.json'))['ROM_SHA']==sha(r)
            image=Image.open(prefix.with_suffix('.png')).convert('RGB')
            glyphs=[]
            for i,ch in enumerate(phrase):
                origin=[17+i*14,16]
                raw=read_glyph(b,glyph_locations(mp[ch])[0]);missing=missing_pixels(image,raw,origin)
                expected=(4 if last=='吗' else 7)if label=='base'and i==3 else 0
                assert len(missing)==expected,(last,label,i,missing)
                assert all(x==13 for x,y in missing)
                glyphs.append({'atom':ch,'origin':origin,'source_ink':sum(unpack(raw).get_flattened_data()),
                    'missing_ink_pixels':len(missing),'missing_positions':missing,
                    'bbox':list(unpack(raw).getbbox())})
            tests.append({'case':last,'version':label,'glyphs':glyphs,
                'image':prefix.with_suffix('.png').relative_to(P).as_posix(),
                'controlled_font_substitution':True,'natural_text_claimed':False})

    # Independent three-column alignment fixture in a genuine dialogue box.
    c=(P/build['ROM']).read_bytes()
    image=Image.open(D/'fixture_dialogue_candidate.png').convert('RGB')
    align=[]
    for i,ch in enumerate('吗娜'):
        raw=read_glyph(c,glyph_locations(mp[ch])[0])
        for y in [144,160]:assert not missing_pixels(image,raw,[65+i*14,y])
        box=unpack(raw).getbbox()
        align.append({'atom':ch,'first_row_origin':[65+i*14,144],
            'second_row_origin':[65+i*14,160],
            'horizontal_ink_center_both_rows':65+i*14+(box[0]+box[2]-1)/2,
            'whole_bitmap_matches_on_both_rows':True})
    raw=read_glyph(c,glyph_locations(mp['捧'])[0])
    assert not missing_pixels(image,raw,[93,144])  # width13 reaches x0, stays intact.

    # Cached settings use a different 16px step. Confirm the same full glyph
    # pixel pattern survives that path, with vertically aligned columns.
    r=bytearray(c);enc=lambda t:b''.join(mp[ch]for ch in t)
    r[0x3DBA74:0x3DBA7A]=b'\x50'+enc('吗娜')+b'\x50'
    r[0x3DBB00:0x3DBB12]=b'\x50'*3+enc('么捧吗娜阳冠')+b'\x50'*3
    for h in [0xFFDC,0x40FFDC]:r[h:h+4]=bytes.fromhex('FF FF 00 00')
    cs=sum(r)&65535
    for h in [0xFFDC,0x40FFDC]:r[h:h+4]=(cs^65535).to_bytes(2,'little')+cs.to_bytes(2,'little')
    fixture=P/'roms/work/bokuno_cn_diag_v288_menu_columns_20261012_01.smc'
    assert not fixture.exists();fixture.write_bytes(r)
    prefix=run(fixture,'user_saves/snes9x_20261011_v284_feedback_inputs_02/bokuno_cn_v10bd284_private_test.000',
               D/'refresh_settings_actions.json','menu_columns')
    im=Image.open(prefix.with_suffix('.png')).convert('RGB')
    menus=[]
    for ch,x in [('吗',240),('娜',256)]:
        raw=read_glyph(c,glyph_locations(mp[ch])[0])
        for y in [95,143]:assert not missing_pixels(im,raw,[x,y],color=(8,8,8))
        menus.append({'atom':ch,'origins':[[x,95],[x,143]],'missing_pixels':0,
                      'cached_menu_advance':16})

    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    canvas=Image.new('RGB',(880,470),'#151a22');draw=ImageDraw.Draw(canvas)
    draw.text((16,10),'游戏实际绘字对照：右侧笔画与上下行定位',font=font,fill='white')
    draw.text((16,39),'受控字体替换检查；使用真实酒馆绘字流程，不代表原剧情台词。',font=small,fill='#bdc8d8')
    for row,last in enumerate(['吗','娜']):
        for col,label in enumerate(['base','candidate']):
            test=next(x for x in tests if x['case']==last and x['version']==label)
            im=Image.open(P/test['image']).convert('RGB')
            crop=im.crop((57,14,88,34)).resize((186,120),Image.Resampling.NEAREST)
            x,y=16+col*432,80+row*172
            text=('旧版：'+last+'缺'+str(test['glyphs'][3]['missing_ink_pixels'])+'个墨点')if label=='base'else('修正版：'+last+'全部笔画保留')
            draw.text((x,y),text,font=font,fill='#ffb39f'if label=='base'else'#a0ead1')
            canvas.paste(crop,(x,y+32))
            raw=read_glyph((P/build['base_ROM']).read_bytes(),glyph_locations(mp[last])[0])
            display=unpack(raw).convert('RGB').resize((96,96),Image.Resampling.NEAREST)
            # PIL binary->RGB makes foreground white and background black.
            canvas.paste(display,(x+216,y+43));draw.text((x+210,y+145),'原字模',font=small,fill='#bdc8d8')
    comparison=D/'right_edge_comparison.png';canvas.save(comparison)
    report={'schema':'v288-native-pixel-proof-v1','status':'RIGHT_EDGE_LOSS_REPRODUCED_AND_FIXED_ALIGNMENT_PASS',
        'ROM_SHA256':build['SHA256'],'tests':tests,'dialogue_alignment':align,
        'cached_menu_alignment':menus,'thirteen_pixel_wide_glyph_intact':True,
        'old_吗_missing_ink':4,'old_娜_missing_ink':7,'new_missing_ink':0,
        'diagnosis':'The following glyph can clear x13 of the preceding full glyph in the native drawing path. Original 16x16-centred HZK12 glyphs extend into that column; native glyphs usually stop at x12. Some paths preserve x13, so this is context dependent.',
        'comparison_image':comparison.relative_to(P).as_posix(),
        'controlled_fixtures_excluded_from_playable_package':True,
        'user_screenshot_exact_scene_replayed':False}
    (P/'qa/V288_NATIVE_PIXEL_PROOF_20261012_01.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k]for k in ['status','old_吗_missing_ink','old_娜_missing_ink','new_missing_ink']},ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
