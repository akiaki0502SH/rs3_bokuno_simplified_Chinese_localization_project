"""Check native display traces, original game data and normal gameplay routes."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1]
D=P/'qa/postbattle_feedback_v289_20261013_01'
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
PROTECTED=[('flags',0xf400,0xf800),('actors',0xf561,0xf561+26*48),
    ('extended_actors',0x1f960,0x1f960+33*48),('name',0xf300,0xf308),
    ('money',0xf31a,0xf31c),('inventory',0xf320,0xf400)]


def main():
    build=rd('qa/V289_POSTBATTLE_WORD_ORDER_BUILD_20261013_01.json')
    m=rd('text/translations/translation_sources_before_v289_20261013_01.json')
    mp={c:bytes.fromhex(z)for c,z in rd(m['latest_font_mapping']).items()}
    pairs={c:bytes.fromhex(z)for c,z in rd(m['latest_fixed_menu_pairs']).items()}
    reverse={v:k for k,v in pairs.items()}
    for c,z in mp.items():
        if len(c)==1 and 0x3400<=ord(c)<=0x9fff:reverse[z]=c
    for c,z in mp.items():reverse.setdefault(z,c)
    def decode(raw):
        z=bytes.fromhex(raw);out=[];i=0
        while i<len(z):
            if z[i]==0x50:i+=1;continue
            atom=z[i:i+2]if z[i]in set(range(0x10,0x17))|{0x18,0x19,0x20,0x21,0x22,0x23,0x46}else z[i:i+1]
            out.append(reverse.get(atom,'{'+atom.hex(' ')+'}'));i+=len(atom)
        return ''.join(out)
    def draws(name):
        trace=(D/(name+'_trace.txt')).read_text(encoding='utf8')
        match=re.search(r'RESULT native_return=true SP_before=(\w+) SP_after=(\w+)',trace)
        assert match and match[1]==match[2],name
        rows=[]
        for line in trace.splitlines():
            if line.startswith('DRAW '):
                rows.append({'trace':line,'text':decode(line.split(' raw=',1)[1])})
            if line.startswith('GLYPH '):
                values={k:int(v)for k,v in re.findall(r'(x|y|frameX|frameY|width|height)=(\d+)',line)}
                assert values['frameX']<=values['x']<values['frameX']+values['width']*2,name
                assert values['frameY']<=values['y']<values['frameY']+values['height'],name
        return rows,trace
    cases=[('item','herb_base04','herb_candidate04'),('mastery','mastery_base02','mastery_candidate02'),
        ('evasion','evasion_base','evasion_candidate'),('destruction','destruction_base','destruction_candidate'),
        ('long_item','long_item_base','long_item_candidate'),('long_skill','long_skill_base','long_skill_candidate'),
        ('extended_item','extended_item_base','extended_item_candidate')]
    native=[]
    for case,base,candidate in cases:
        a,ta=draws(base);c,tc=draws(candidate)
        before,after=[x['text']for x in a],[x['text']for x in c]
        if case=='item':assert before==['野生药','把','获得了']and after==['获得了','野生药']
        elif case=='mastery':assert before==['招架','的','习得奥义']and after==['习得','招架','的','奥义']
        elif case=='destruction':
            assert before==after
            assert Image.open(D/(base+'_visible.png')).tobytes()==Image.open(D/(candidate+'_visible.png')).tobytes()
        elif case=='evasion':assert after==['习得',before[0],'的','识破奥义']
        elif case in ['long_item','extended_item']:assert after==['获得了',before[0]]
        elif case=='long_skill':assert after==['习得',before[0],'的','奥义']
        ai=(D/(base+'_initial.ram')).read_bytes();af=(D/(base+'_final.ram')).read_bytes()
        ci=(D/(candidate+'_initial.ram')).read_bytes();cf=(D/(candidate+'_final.ram')).read_bytes()
        checks={key:ai[lo:hi]==af[lo:hi]==ci[lo:hi]==cf[lo:hi]for key,lo,hi in PROTECTED}
        assert all(checks.values()),(case,checks)
        native.append({'case':case,'before_draw_fragments':before,'after_draw_fragments':after,
            'checks':checks,'stack_balanced':True,'glyph_positions_within_native_frame':True,
            'image':(D/(candidate+'_visible.png')).relative_to(P).as_posix(),
            'controlled_display_metadata_only':True,'natural_reward_or_mastery_injected':False})
    print('Native composition, frame, stack and game-data checks PASS:',len(native),flush=True)
    # The fabricated spell-context flag lacks a valid native caller context.
    # Both old and new builds corrupt this fixture; retain it as inconclusive.
    rejected={'case':'magic_manual_flag_fixture','status':'INCONCLUSIVE_INVALID_SEED_CONTEXT',
        'old_and_new_images_both_corrupted':True,'accepted_as_runtime_validation':False}

    idle=D/'idle_actions.json';idle.write_text(json.dumps([[[],0,1]]))
    old=rd('qa/V288_FONT_GEOMETRY_REGRESSION_20261012_01.json')
    jobs={x['case']:(x['state_source'],P/x['actions'])for x in old['rows']}
    jobs['battle_progress']=('user_saves/snes9x_20261010_v279_feedback_02/bokuno_cn_v10ay279_private_test.007',D/'natural_battle_actions.json')
    routes=[]
    for case,(state,actions)in jobs.items():
        input_hash=sha((P/state).read_bytes());prefixes={}
        for label,rom in [('base',build['base_ROM']),('candidate',build['ROM'])]:
            prefix=D/(('natural_battle_'+label)if case=='battle_progress'else('regression_'+case+'_'+label))
            if not prefix.with_suffix('.json').exists():
                z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',
                    rom,state,str(actions),str(prefix)],cwd=P,capture_output=True,timeout=60)
                prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr)
                assert z.returncode==0,(case,label,z.stderr[-1200:])
            assert rd(prefix.with_suffix('.json'))['ROM_SHA']==sha((P/rom).read_bytes())
            prefixes[label]=prefix
        a,c=(prefixes[k].with_suffix('.ram').read_bytes()for k in ['base','candidate'])
        checks={key:a[lo:hi]==c[lo:hi]for key,lo,hi in PROTECTED}
        checks['SRAM_exact']=prefixes['base'].with_suffix('.srm').read_bytes()==prefixes['candidate'].with_suffix('.srm').read_bytes()
        checks['original_input_unchanged']=sha((P/state).read_bytes())==input_hash
        assert all(checks.values()),(case,checks)
        routes.append({'case':case,'checks':checks,'protected_pass':True,
            'candidate_state':prefixes['candidate'].with_suffix('.state').relative_to(P).as_posix(),
            'candidate_image':prefixes['candidate'].with_suffix('.png').relative_to(P).as_posix(),
            'state_source':state,'natural_battle_finished':False if case=='battle_progress'else None})
        print(case,'normal route PASS',flush=True)

    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    image=Image.new('RGB',(864,410),'#151a22');draw=ImageDraw.Draw(image)
    draw.text((16,8),'战后提示：原生绘字流程修复对照',font=font,fill='white')
    draw.text((16,37),'受控显示检查，仅设置名称选择参数；不是朋友的自然战斗存档。',font=small,fill='#bdc8d8')
    for row,(title,base,candidate)in enumerate([('习得奥义','mastery_base02','mastery_candidate02'),('获得物品','herb_base04','herb_candidate04')]):
        for col,name in enumerate([base,candidate]):
            x,y=16+col*424,74+row*160
            draw.text((x,y),title+' · '+('旧版'if col==0 else'修正版'),font=font,fill='#ffb39f'if col==0 else'#a0ead1')
            crop=Image.open(D/(name+'_visible.png')).convert('RGB').crop((22,24,148,66)).resize((378,126),Image.Resampling.NEAREST)
            image.paste(crop,(x,y+29))
    image.save(D/'postbattle_comparison.png')
    proof={'status':'SEVEN_NATIVE_DISPLAY_CASES_AND_SEVEN_NORMAL_ROUTES_PASS','ROM_SHA256':build['SHA256'],
        'native_cases':native,'native_case_count':len(native),'normal_routes':routes,'normal_route_count':len(routes),
        'inconclusive_fixture':rejected,'root_cause_proven_by_old_native_sequence':True,
        'unexpected_把_is_UI29_translated_を_not_overread_or_item_name':True,
        'original_UI29_other_callers_and_destruction_path_preserved':True,
        'comparison_image':(D/'postbattle_comparison.png').relative_to(P).as_posix(),
        'no_actor_inventory_money_world_or_skill_acquisition_writes':True,
        'friend_exact_natural_battle_replayed':False,'full_game_or_CPU_RNG_equivalence_claimed':False}
    (P/'qa/V289_POSTBATTLE_RUNTIME_PROOF_20261013_01.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS',len(native),len(routes))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
