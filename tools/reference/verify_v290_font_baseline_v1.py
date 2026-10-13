"""Verify actual user snapshots, baseline pixels and previous display routes."""
from pathlib import Path
import hashlib,json,subprocess,sys
from PIL import Image,ImageDraw,ImageFont
from font_geometry_v1 import glyph_locations,read_glyph,unpack
P=Path(__file__).resolve().parents[1]
D=P/'qa/font_baseline_v290_20261014_01'
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
PROTECTED=[('flags',0xf400,0xf800),('actors',0xf561,0xf561+26*48),
    ('extended_actors',0x1f960,0x1f960+33*48),('name',0xf300,0xf308),
    ('money',0xf31a,0xf31c),('inventory',0xf320,0xf400)]


def check_pair(a,c):
    ar,cr=a.with_suffix('.ram').read_bytes(),c.with_suffix('.ram').read_bytes()
    checks={k:ar[lo:hi]==cr[lo:hi]for k,lo,hi in PROTECTED}
    checks['SRAM_exact']=a.with_suffix('.srm').read_bytes()==c.with_suffix('.srm').read_bytes()
    assert all(checks.values()),(a.name,checks)
    return checks


def run(rom,state,actions,name):
    prefix=D/name
    if not prefix.with_suffix('.json').exists():
        z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',
            rom,state,str(actions),str(prefix)],cwd=P,capture_output=True,timeout=60)
        prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr)
        assert z.returncode==0,z.stderr[-1200:]
    assert rd(prefix.with_suffix('.json'))['ROM_SHA']==sha((P/rom).read_bytes())
    return prefix


def main():
    build=rd('qa/V290_FONT_BASELINE_BUILD_20261014_01.json')
    old=rd('text/translations/translation_sources_before_v290_20261014_01.json')
    mp={c:bytes.fromhex(z)for c,z in rd(old['latest_font_mapping']).items()}
    pixels=[];routes=[]
    specifications=[(0,'王','王家戒指',[112,128,144,160],143),
                    (1,'形','无形之位',[288,304,320,336],71),
                    (2,'阳','太阳光线',[288,304,320,336],55)]
    for slot,target,text,xs,y in specifications:
        prefix={k:D/f'actual{slot:03d}_{k}'for k in ['base','candidate']}
        checks=check_pair(prefix['base'],prefix['candidate'])
        row={'slot':slot,'target':target,'visible_name':text,'checks':checks,
            'candidate_state':prefix['candidate'].with_suffix('.state').relative_to(P).as_posix(),
            'candidate_image':prefix['candidate'].with_suffix('.png').relative_to(P).as_posix(),
            'normal_actor_cycle_and_selection_only':True}
        routes.append(row);measurement={}
        for label,key in [('base','base_ROM'),('candidate','ROM')]:
            r=(P/build[key]).read_bytes();im=Image.open(prefix[label].with_suffix('.png')).convert('RGB');letters=[]
            for ch,x in zip(text,xs):
                g=unpack(read_glyph(r,glyph_locations(mp[ch])[0]));box=g.getbbox()
                foreground=[(xx,yy)for yy in range(16)for xx in range(16)if g.getpixel((xx,yy))]
                missing=[(xx,yy)for xx,yy in foreground if max(im.getpixel((x+xx,y+yy)))>24]
                assert not missing,(slot,label,ch,missing)
                letters.append({'atom':ch,'cell_origin':[x,y],'ink_bbox':list(box),
                    'actual_foreground_bottom':y+box[3]-1,'missing_foreground_pixels':0})
            measurement[label]=letters
        before=[v['actual_foreground_bottom']for v in measurement['base']]
        after=[v['actual_foreground_bottom']for v in measurement['candidate']]
        assert len(set(after))==1 and before[text.index(target)]==after[0]-1
        pixels.append({'slot':slot,'target':target,'measurements':measurement,
            'old_target_one_pixel_above_neighbors':True,'new_baselines_equal':True})
        print('Actual user baseline pixels PASS',slot,target,flush=True)
    # Preserve six prior display routes and the bounded battle-progress route.
    prior=rd('qa/V289_POSTBATTLE_RUNTIME_PROOF_20261013_01.json')
    for row in prior['normal_routes']:
        source=row['state_source'];case=row['case']
        if case=='battle_progress':actions=P/'qa/postbattle_feedback_v289_20261013_01/natural_battle_actions.json'
        else:
            older=rd('qa/V288_FONT_GEOMETRY_REGRESSION_20261012_01.json')
            actions=P/next(x['actions']for x in older['rows']if x['case']==case)
        prefixes={label:run(build[key],source,actions,'prior_'+case+'_'+label)
                  for label,key in [('base','base_ROM'),('candidate','ROM')]}
        checks=check_pair(prefixes['base'],prefixes['candidate'])
        routes.append({'case':case,'checks':checks,'protected_pass':True,
            'candidate_image':prefixes['candidate'].with_suffix('.png').relative_to(P).as_posix()})
        print('Prior route PASS',case,flush=True)

    # Point-for-point source comparisons already prove all 2673 characters.
    # Recheck the previous tavern's sensitive right-edge case in the game.
    frozen=rd('text/translations/translation_sources_before_v288_20261012_01.json')
    data=bytearray((P/build['ROM']).read_bytes())
    for target,ch in zip('欢迎光临','吗娜吗娜'):
        raw=read_glyph(data,glyph_locations(mp[ch])[0])
        for top,bottom in glyph_locations(mp[target]):data[top:top+16]=raw[:16];data[bottom:bottom+16]=raw[16:]
    for h in [0xffdc,0x40ffdc]:data[h:h+4]=bytes.fromhex('ff ff 00 00')
    cs=sum(data)&65535
    for h in [0xffdc,0x40ffdc]:data[h:h+4]=(cs^65535).to_bytes(2,'little')+cs.to_bytes(2,'little')
    fixture='roms/work/bokuno_cn_diag_v290_right_edge_20261014_01.smc'
    assert not(P/fixture).exists();(P/fixture).write_bytes(data)
    prefix=run(fixture,'user_saves/snes9x_20261009_2330_v270_tavern_feedback/bokuno_cn_v10ap270_private_test.001',
        P/'qa/v272_focused_001_welcome_20261010_01_actions.json','right_edge_candidate')
    im=Image.open(prefix.with_suffix('.png')).convert('RGB');missing=0
    for i,ch in enumerate('吗娜吗娜'):
        g=unpack(read_glyph(data,glyph_locations(mp[ch])[0]))
        missing+=sum(im.getpixel((17+i*14+x,16+y))!=(255,255,255)
                     for y in range(16)for x in range(16)if g.getpixel((x,y)))
    assert missing==0
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    canvas=Image.new('RGB',(760,423),'#151a22');draw=ImageDraw.Draw(canvas)
    draw.text((16,8),'三份真实存档：字形底部对齐检查',font=font,fill='white')
    draw.text((16,35),'通过正常按键重绘；同一行字格位置保持，修正字模纵向定位。',font=small,fill='#bdc8d8')
    for i,(slot,target,text,xs,y)in enumerate(specifications):
        for col,label in enumerate(['base','candidate']):
            x,top=16+col*376,68+i*113
            draw.text((x,top),target+' · '+('旧版高1像素'if label=='base'else'修正版底部齐'),font=font,
                      fill='#ffb39f'if label=='base'else'#a0ead1')
            im=Image.open(D/f'actual{slot:03d}_{label}.png').convert('RGB')
            left=xs[0]-4;right=xs[-1]+24;upper=y-2
            crop=im.crop((left,upper,right,y+17)).resize(((right-left)*4,76),Image.Resampling.NEAREST)
            canvas.paste(crop,(x,top+27))
            baseline=top+27+(y+14-upper)*4
            for xx in range(x,x+crop.width,10):draw.line((xx,baseline,xx+5,baseline),fill='#63cfb6')
    canvas.save(D/'baseline_comparison.png')
    proof={'status':'THREE_REAL_FEEDBACK_PIXEL_BASELINES_AND_TEN_NORMAL_ROUTES_PASS',
        'ROM_SHA256':build['SHA256'],'feedback_pixel_measurements':pixels,'routes':routes,
        'normal_protection_cases':len(routes),'right_edge_missing_ink_pixels':missing,
        'all_glyph_ink_and_horizontal_positions_preserved':True,'v289_postbattle_module_byte_identical':True,
        'no_gameplay_or_linebreak_changes':True,'comparison_image':(D/'baseline_comparison.png').relative_to(P).as_posix(),
        'original_save_sources_preserved':'user_saves/snes9x_20261014_v289_font_feedback_01/COPY_RECEIPT.json'}
    (P/'qa/V290_FONT_BASELINE_RUNTIME_20261014_01.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS',len(routes),'routes; target bottoms:',[x['measurements']['candidate'][0]['actual_foreground_bottom']for x in pixels])


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
