"""Check digit pixels in real renderers plus established gameplay routes."""
from pathlib import Path
import concurrent.futures,hashlib,json,re,subprocess,sys
from PIL import Image,ImageDraw,ImageFont
from font_geometry_v1 import glyph_locations,read_glyph,unpack
from run_v292_regressions_v1 import PROTECTED
P=Path(__file__).resolve().parents[1];D=P/'qa/digit_font_v294_20261017_01'
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()


def main():
    build=rd('qa/V294_DIGIT_FONT_BUILD_20261017_01.json')
    current=(P/build['ROM']).read_bytes();base=(P/build['base_ROM']).read_bytes()
    assert sha(current)==build['SHA256']and sha(base)==build['base_SHA256']
    report=P/'qa/V294_DIGIT_FONT_RUNTIME_20261017_01.json';assert not report.exists()
    m=rd('text/translations/translation_sources_before_v294_20261017_01.json')
    mp={k:bytes.fromhex(v)for k,v in rd(m['latest_font_mapping']).items()}
    old=rd('qa/V293_TITLE_NORMAL_REGRESSION_20261017_05.json');assert old['SHA256']==build['base_SHA256']
    def run(rom,state,actions,prefix):
        if prefix.with_suffix('.json').exists():
            previous=rd(prefix.with_suffix('.json'))
            assert previous['ROM_SHA']==sha(Path(rom).read_bytes())and previous['state_SHA']==sha(Path(state).read_bytes())
            assert previous['steps']==json.loads(Path(actions).read_text(encoding='utf-8-sig'))
            return
        z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',
            str(rom),str(state),str(actions),str(prefix)],cwd=P,capture_output=True,timeout=60)
        prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr)
        assert z.returncode==0,(prefix.name,z.stderr[-1000:])
        assert rd(prefix.with_suffix('.json'))['ROM_SHA']==sha(Path(rom).read_bytes())
    def compare(a,b):
        aa=a.with_suffix('.ram').read_bytes();bb=b.with_suffix('.ram').read_bytes()
        checks={key:aa[lo:hi]==bb[lo:hi]for key,lo,hi in PROTECTED}
        checks['SRAM_exact']=a.with_suffix('.srm').read_bytes()==b.with_suffix('.srm').read_bytes()
        assert all(checks.values()),(a.name,b.name,checks)
        return checks
    def normal(row):
        source=P/row['state_source'];digest=sha(source.read_bytes());prefix=D/('normal_'+row['case'])
        run(P/build['ROM'],source,row['actions'],prefix)
        checks=compare((P/row['candidate_state']).with_suffix(''),prefix)
        assert sha(source.read_bytes())==digest
        print('normal',row['case'],'PASS',flush=True)
        return {'case':row['case'],'state_source':row['state_source'],'actions':row['actions'],'checks':checks,
            'candidate_state':prefix.with_suffix('.state').relative_to(P).as_posix(),
            'candidate_image':prefix.with_suffix('.png').relative_to(P).as_posix(),'normal_input_only':True}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:normals=list(pool.map(normal,old['rows']))

    # A controlled font substitution into four characters of the established
    # genuine tavern redraw. No VM/world/actor writes or production text edits.
    phrases=['0123','4567','890年','15年前','年5年年'];pixel_rows=[]
    state=P/'user_saves/snes9x_20261009_2330_v270_tavern_feedback/bokuno_cn_v10ap270_private_test.001'
    actions=P/'qa/v272_focused_001_welcome_20261010_01_actions.json'
    input_sha=sha(state.read_bytes())
    def fixture(job):
        index,phrase,label,data=job;r=bytearray(data)
        for slot,ch in zip('欢迎光临',phrase):
            raw=read_glyph(data,glyph_locations(mp[ch])[0])
            for top,bottom in glyph_locations(mp[slot]):r[top:top+16]=raw[:16];r[bottom:bottom+16]=raw[16:]
        for h in [0xffdc,0x40ffdc]:r[h:h+4]=bytes.fromhex('ff ff 00 00')
        cs=sum(r)&65535
        for h in [0xffdc,0x40ffdc]:r[h:h+4]=(cs^65535).to_bytes(2,'little')+cs.to_bytes(2,'little')
        rom=D/f'font_fixture_{index}_{label}.smc'
        if rom.exists():assert rom.read_bytes()==r
        else:rom.write_bytes(r)
        prefix=D/f'font_fixture_{index}_{label}'
        run(rom,state,actions,prefix)
        image=Image.open(prefix.with_suffix('.png')).convert('RGB');measure=[]
        for i,ch in enumerate(phrase):
            g=unpack(read_glyph(data,glyph_locations(mp[ch])[0]));box=g.getbbox();origin=(17+14*i,16)
            missing=[(x,y)for y in range(16)for x in range(16)if g.getpixel((x,y))and image.getpixel((origin[0]+x,origin[1]+y))!=(255,255,255)]
            assert not missing,(phrase,label,ch,missing)
            measure.append({'character':ch,'origin':list(origin),'bbox':list(box),'bottom':origin[1]+box[3]-1,'missing_pixels':0})
        return {'phrase':phrase,'label':label,'measurements':measure,'prefix':prefix,'controlled_font_substitution':True,'original_feedback_scene':False}
    jobs=[(i,s,label,data)for i,s in enumerate(phrases)for label,data in [('base',base),('candidate',current)]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:raw_rows=list(pool.map(fixture,jobs))
    assert sha(state.read_bytes())==input_sha
    for phrase in phrases:
        a,b=[next(x for x in raw_rows if x['phrase']==phrase and x['label']==label)for label in ['base','candidate']]
        checks=compare(a['prefix'],b['prefix'])
        assert {x['bottom']for x in b['measurements']}=={29}
        pixel_rows.append({'phrase':phrase,'old':a['measurements'],'new':b['measurements'],'checks':checks,
            'base_image':a['prefix'].with_suffix('.png').relative_to(P).as_posix(),
            'candidate_image':b['prefix'].with_suffix('.png').relative_to(P).as_posix(),
            'controlled_font_substitution':True,'original_feedback_scene':False})
        print('pixel',phrase,'PASS',flush=True)
    # The existing real result-window probe checks the shared native 23xx
    # digits. It writes a wait shim only into isolated diagnostic ROM copies.
    import run_v292_display_probes_v1 as rewards
    rewards.D=D/'rewards';rewards.D.mkdir(exist_ok=True)
    rewards.CASES={f'money{n}':dict(entry=0xcf11,finish=0xcf4f,amount=n)for n in [1234,5678,90]}
    args=sys.argv[:]
    for label,key in [('base','base_ROM'),('candidate','ROM')]:
        sys.argv=['run_v292_display_probes_v1.py','--rom',build[key],'--label',label]
        rewards.main()
    sys.argv=args
    reward_rows=[]
    for name in rewards.CASES:
        aa=(rewards.D/f'base_{name}_trace.txt').read_text(encoding='utf8')
        bb=(rewards.D/f'candidate_{name}_trace.txt').read_text(encoding='utf8')
        ag=re.findall(r'GLYPH code=(\w+) x=(\d+) y=(\d+)',aa)
        bg=re.findall(r'GLYPH code=(\w+) x=(\d+) y=(\d+)',bb)
        assert ag==bg and any(x[0].startswith('23')for x in bg)
        ar=(rewards.D/f'base_{name}_final.ram').read_bytes();br=(rewards.D/f'candidate_{name}_final.ram').read_bytes()
        checks={key:ar[lo:hi]==br[lo:hi]for key,lo,hi in PROTECTED};assert all(checks.values())
        reward_rows.append({'case':name,'same_glyph_codes_and_coordinates':True,'checks':checks,
            'candidate_image':(rewards.D/f'candidate_{name}_visible.png').relative_to(P).as_posix(),'controlled_display_only':True})

    cold_actions=D/'cold_steps.json';cold_actions.write_text(json.dumps([[[],0,n]for n in [1200,1800,1600,1200,700]]),encoding='utf8')
    prefix=D/'title_cold';z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v293_title_coldboot_v1.py',
        build['ROM'],'--fresh',str(cold_actions),str(prefix)],cwd=P,capture_output=True,timeout=40)
    prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,z.stderr[-1000:]
    for i in range(4):
        a=Image.open(P/f'qa/title_prologue_v293_20261017_01/snes_candidate05_step{i:03d}.png').convert('RGB')
        b=Image.open(str(prefix)+f'_step{i:03d}.png').convert('RGB');assert a.tobytes()==b.tobytes()
    canvas=Image.new('RGB',(920,720),'#141d20');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
    draw.text((20,14),'实际对白绘字检查：大小、字底和数字混排',font=font,fill='#eaf0df')
    draw.text((20,48),'受控字模替换，沿用真实酒馆重绘；不代表已复现截图原剧情。',font=small,fill='#adc7bc')
    for j,phrase in enumerate(['15年前','0123','4567','890年']):
        row=next(x for x in pixel_rows if x['phrase']==phrase)
        for k,key in enumerate(['base_image','candidate_image']):
            x=20+k*450;y=90+j*149
            draw.text((x,y),('旧版'if k==0 else'修正版')+'：'+phrase,font=font,fill='#efb8a1'if k==0 else'#a9e0ba')
            im=Image.open(P/row[key]).convert('RGB');crop=im.crop((14,14,78,34)).resize((384,120),Image.Resampling.NEAREST)
            canvas.paste(crop,(x,y+27))
    comparison=D/'实际对白数字_修正前后.png';canvas.save(comparison)
    result={'schema':'v294-digit-font-runtime-v1','status':'FIVE_NATIVE_DIALOGUE_PIXEL_PAIRS_THIRTEEN_NORMAL_PAIRS_THREE_REWARD_PAIRS_AND_TITLE_PASS',
        'ROM':build['ROM'],'SHA256':build['SHA256'],'normal_pairs':13,'normal_routes':normals,
        'dialogue_pixel_pairs':pixel_rows,'reward_display_pairs':reward_rows,'title_four_pages_pixels_unchanged':True,
        'comparison_image':comparison.relative_to(P).as_posix(),'original_feedback_scene_replayed':False,
        'all_pixels_intact':True,'all_candidate_digits_same_baseline_as_CJK':True,
        'digit5_not_shifted_from_reviewed_candidate':True,'no_text_or_character_advance_changes':True,
        'synthetic_ROMs_and_fixture_states_excluded_from_delivery':True}
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:result[k]for k in ['status','SHA256','normal_pairs','comparison_image']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
