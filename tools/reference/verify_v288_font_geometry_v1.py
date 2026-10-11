"""Normal-input regression plus explicitly labelled native font fixtures."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont
from font_geometry_v1 import glyph_locations, read_glyph, unpack

P = Path(__file__).resolve().parents[1]
D = P / 'qa/font_geometry_v288_20261012_01'
rd = lambda f: json.loads((P/f).read_text(encoding='utf8'))
sha = lambda z: hashlib.sha256(z).hexdigest().upper()


def run(rom, state, actions, name):
    prefix = D/name
    assert not prefix.with_suffix('.json').exists()
    z = subprocess.run([sys.executable,'-B','-X','utf8',
        'tools/snes9x_v266_regression_runner_v1.py',str(rom),state,
        str(actions),str(prefix)],cwd=P,capture_output=True,timeout=60)
    prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr)
    assert z.returncode == 0,(name,z.stderr[-1800:])
    return prefix


def main():
    build = rd('qa/V288_FONT_GEOMETRY_BUILD_20261012_01.json')
    base, candidate = P/build['base_ROM'], P/build['ROM']
    settings = 'user_saves/snes9x_20261011_v284_feedback_inputs_02/bokuno_cn_v10bd284_private_test.000'
    spells = 'user_saves/snes9x_20261011_v284_feedback_inputs_02/bokuno_cn_v10bd284_private_test.001'
    dialogue = 'user_saves/snes9x_20261011_v282_feedback_inputs_01/bokuno_cn_v10ba281_private_test.004'
    schools = 'user_saves/snes9x_20261011_v282_feedback_inputs_01/bokuno_cn_v10ba281_private_test.003'
    tech = 'user_saves/snes9x_20261011_v283_feedback_inputs_01/bokuno_cn_v10bc283_extra_test.000'
    cases = {
        'settings':(settings,D/'refresh_settings_actions.json'),
        'spells':(spells,P/'qa/v287_refresh001_20261011_01_actions.json'),
        'dialogue':(dialogue,P/'qa/v282_dialogue_refresh_actions_20261011_01.json'),
        'schools':(schools,P/'qa/v282_moon_reopen_actions_20261011_01.json'),
        'technique':(tech,D/'refresh_technique_actions.json'),
    }
    (D/'refresh_technique_actions.json').write_text(json.dumps([[['DOWN'],4,60],[['UP'],4,120]]))
    rows=[]
    protected=[('flags',0xF400,0xF800),('actors',0xF561,0xF561+26*48),
        ('extended_actors',0x1F960,0x1F960+33*48),('name',0xF300,0xF308),
        ('money',0xF31A,0xF31C),('inventory',0xF320,0xF400)]
    for name,(state,actions) in cases.items():
        input_hash=sha((P/state).read_bytes())
        prefixes={}
        for label,rom in [('base',base),('candidate',candidate)]:
            prefix=D/(name+'_'+label)
            if not prefix.with_suffix('.json').exists():
                run(rom,state,actions,name+'_'+label)
            prefixes[label]=prefix
        a,c=(prefixes[k].with_suffix('.ram').read_bytes() for k in ('base','candidate'))
        checks={key:a[lo:hi]==c[lo:hi] for key,lo,hi in protected}
        checks['SRAM_exact']=prefixes['base'].with_suffix('.srm').read_bytes()==prefixes['candidate'].with_suffix('.srm').read_bytes()
        checks['original_state_unchanged']=sha((P/state).read_bytes())==input_hash
        assert all(checks.values()),(name,checks)
        rows.append({'case':name,'checks':checks,'protected_pass':True,
            'candidate_image':prefixes['candidate'].with_suffix('.png').relative_to(P).as_posix(),
            'candidate_state':prefixes['candidate'].with_suffix('.state').relative_to(P).as_posix(),
            'state_source':state,'actions':actions.relative_to(P).as_posix()})
        print(name,'PASS',flush=True)

    # Fixtures change only bounded existing display strings and checksums.
    # They exercise the game's drawing code, but are not natural scene evidence
    # and must never be packaged as a gameplay ROM or user save.
    m=rd('text/translations/translation_sources_before_v288_20261012_01.json')
    mp={k:bytes.fromhex(v) for k,v in rd(m['latest_font_mapping']).items()}
    enc=lambda t:b''.join(mp[c] for c in t)
    fixture_rows=[]
    for label,rom in [('base',base),('candidate',candidate)]:
        original=rom.read_bytes();r=bytearray(original)
        sound_at,speed_at=0x3DBA74,0x3DBB00
        assert r[sound_at:sound_at+6]==b'\x50'+enc('声音')+b'\x50'
        assert r[speed_at:speed_at+18]==b'\x50'*3+enc('菜单光标速度')+b'\x50'*3
        r[sound_at:sound_at+6]=b'\x50'+enc('吗娜')+b'\x50'
        r[speed_at:speed_at+18]=b'\x50'*3+enc('吗娜么捧阳冠')+b'\x50'*3
        old=enc('你们是从西方');new=enc('吗娜捧么阳冠')
        assert len(old)==len(new)==12 and original.count(old)==1
        at=original.index(old);r[at:at+len(old)]=new
        tail=enc('来的？');assert original[at+len(old)+1:at+len(old)+1+len(tail)]==tail
        assert len(enc('吗娜'))==len(tail)
        r[at+len(old)+1:at+len(old)+1+len(tail)]=enc('吗娜')
        for site in [0xFFDC,0x40FFDC]:r[site:site+4]=bytes.fromhex('FF FF 00 00')
        cs=sum(r)&65535
        for site in [0xFFDC,0x40FFDC]:r[site:site+4]=(cs^65535).to_bytes(2,'little')+cs.to_bytes(2,'little')
        fixture=P/f'roms/work/bokuno_cn_diag_v288_font_geometry_{label}_20261012_01.smc'
        assert not fixture.exists();fixture.write_bytes(r)
        for name,state,actions in [('menu',settings,D/'refresh_settings_actions.json'),
                                    ('dialogue',dialogue,P/'qa/v282_dialogue_refresh_actions_20261011_01.json')]:
            prefix=run(fixture,state,actions,'fixture_'+name+'_'+label)
            fixture_rows.append({'type':name,'label':label,'image':prefix.with_suffix('.png').relative_to(P).as_posix(),
                'controlled_display_strings':True,'natural_scene':False})
    report={'schema':'v288-font-geometry-regression-v1','status':'NORMAL_ROUTES_PROTECTION_PASS_PIXEL_REVIEW_PENDING',
        'ROM_SHA256':build['SHA256'],'cases':len(rows),'rows':rows,
        'protected_pass':True,'fixtures':fixture_rows,'gameplay_memory_injection':False,
        'diagnostic_ROMs_excluded_from_delivery':True,'full_game_coverage_claimed':False}
    (P/'qa/V288_FONT_GEOMETRY_REGRESSION_20261012_01.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
