"""Package the reviewed font-only build and genuine refreshed game snapshots."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import sys
import zipfile
from font_geometry_v1 import glyph_locations, read_glyph
from verify_v288_font_geometry_v1 import run

P=Path(__file__).resolve().parents[1]
D=P/'qa/font_geometry_v288_20261012_01'
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()


def main():
    build=rd('qa/V288_FONT_GEOMETRY_BUILD_20261012_01.json')
    regression=rd('qa/V288_FONT_GEOMETRY_REGRESSION_20261012_01.json')
    pixels=rd('qa/V288_NATIVE_PIXEL_PROOF_20261012_01.json')
    assert regression['protected_pass']and pixels['new_missing_ink']==0
    assert pixels['status']=='RIGHT_EDGE_LOSS_REPRODUCED_AND_FIXED_ALIGNMENT_PASS'
    rom=(P/build['ROM']).read_bytes()
    assert sha(rom)==build['SHA256']
    assert rom==(P/'roms/work/bokuno_cn_diag_v288_independent_20261012_01.smc').read_bytes()
    assert sha((P/build['base_ROM']).read_bytes())==build['base_SHA256']
    # Include the untouched natural welcome route as a sixth protection case.
    a=(D/'welcome_base.ram').read_bytes();c=(D/'welcome_candidate.ram').read_bytes()
    checks={k:a[lo:hi]==c[lo:hi]for k,lo,hi in [('flags',0xF400,0xF800),
        ('actors',0xF561,0xF561+26*48),('extended_actors',0x1F960,0x1F960+33*48),
        ('name',0xF300,0xF308),('money',0xF31A,0xF31C),('inventory',0xF320,0xF400)]}
    checks['SRAM_exact']=(D/'welcome_base.srm').read_bytes()==(D/'welcome_candidate.srm').read_bytes()
    assert all(checks.values())
    regression['rows'].append({'case':'welcome','checks':checks,'protected_pass':True,
        'candidate_image':(D/'welcome_candidate.png').relative_to(P).as_posix(),
        'candidate_state':(D/'welcome_candidate.state').relative_to(P).as_posix(),
        'state_source':'user_saves/snes9x_20261009_2330_v270_tavern_feedback/bokuno_cn_v10ap270_private_test.001',
        'actions':'qa/v272_focused_001_welcome_20261010_01_actions.json'})
    regression.update(cases=len(regression['rows']),status='SIX_NORMAL_ROUTES_PROTECTION_AND_NATIVE_PIXELS_PASS',
        native_pixel_proof='qa/V288_NATIVE_PIXEL_PROOF_20261012_01.json')
    (P/'qa/V288_FONT_GEOMETRY_REGRESSION_20261012_01.json').write_text(json.dumps(regression,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

    dest=(P/'artifacts/private_human_tests/bokuno_cn_v10bh288_20261012_25').resolve()
    assert dest.is_relative_to(Path('G:/CodexProjects'))and dest.is_relative_to(P)and not dest.exists()
    dest.mkdir();(dest/'存档_snes9x').mkdir();(dest/'回归画面').mkdir()
    stem='bokuno_cn_v10bh288_private_test'
    romfile=dest/(stem+'.smc');romfile.write_bytes(rom)
    cases=[('settings','系统设置'),('spells','太阳术与阳字'),('dialogue','寺院外两行对白'),
           ('schools','术系页面'),('technique','技能和说明'),('welcome','酒馆两窗口对白')]
    states=[]
    for i,(case,label)in enumerate(cases):
        row=next(x for x in regression['rows']if x['case']==case)
        raw=(P/row['candidate_state']).read_bytes();assert raw.startswith(b'#!s9xsnp:0012\n')
        z=gzip.compress(raw,compresslevel=9,mtime=0);file=dest/'存档_snes9x'/f'{stem}.{i:03d}';file.write_bytes(z)
        shutil.copyfile(P/row['candidate_image'],dest/'回归画面'/f'{i:03d}.png')
        states.append({'slot':i,'hotkey':f'F{i+1}','purpose':label,'file':file.relative_to(dest).as_posix(),
            'SHA256':sha(z),'source':row['candidate_state'],'original_input':row['state_source'],
            'normal_controller_refresh':True,'controlled_fixture':False})
    sram_source=P/'user_saves/snes9x_20261011_v284_feedback_inputs_02/bokuno_cn_v10bd284_private_test.srm'
    sram=sram_source.read_bytes();(dest/'存档_snes9x'/(stem+'.srm')).write_bytes(sram)
    shutil.copyfile(P/pixels['comparison_image'],dest/'字体问题_实际绘字对照.png')
    readme='''# 测试包25：中文单字的右侧笔画与居中定位

本包在v287上统一中文单字的定位，不改变笔画形状或字号。

## 本轮修复

- 每字存储格一直是16×16；原生字形多数从x1开始，HZK12中文字多数从x2开始，混用后出现一像素的横向错位。
- 对白每格前进14像素，部分缓存菜单前进16像素。某些后续字符会清掉前字的x13列，因此按16×16居中的字形会在特定情况下缺右侧笔画。
- 2673个当前中文单字全部检查，1719个移动到同一字形中线。原有1620个右侧越界风险单字现在全部在安全列内，字形大小、墨点数及每条笔画保持。
- 横向和纵向采用一致的取整方向。奇偶像素宽高不同的字，与公共中线最多相差半像素，不会因字库来源不同再多偏一整像素。

真实酒馆绘字流程的受控检查中，旧版“吗”缺4个墨点、“娜”缺7个；本版均缺0个。同字在两行对白及两行设置界面中逐像素匹配、列位置一致。附对照图标明受控字体替换用途，不是原剧情台词。

## 使用

打开bokuno_cn_v10bh288_private_test.smc，将“存档_snes9x”配套文件放入模拟器存档目录。

|编号|快捷键|场景|
|---|---|---|
|000|F1|系统设置：观察上下标题及各字位置|
|001|F2|太阳术：观察阳字及相邻术名|
|002|F3|寺院外：两行正常对白|
|003|F4|术系页面|
|004|F5|技能列表与两行说明|
|005|F6|酒馆：上下两个正常对白窗口|

以上存档均来自原始游戏存档，通过正常按键刷新后导出；没有放入诊断ROM或受控台词存档。也可以加载自己的存档。已打开的旧窗口可能保存旧字图，关闭并重新打开该窗口后即可重新绘字。

## 验证范围

全部当前中文单字进行像素形状、墨点数、范围和幂等检查；原生字库的完全相同别名同步。独立重建与主ROM逐字节一致；六组正常路线核对角色、剧情标志、姓名、金钱、背包及SRAM；六个交付即时档逐个实际载入；ZIP逐文件回读一致。

字符存储格相同，不代表每个字的笔画包围框也应强制相同：例如“么”的笔画本就比“娜”窄，保留字形比例并按相同中线放置。少数历史长名称的一格两字属于另一个字段宽度限制，本包保留其现有形式；标点、半宽字、图标也保留各自定位。全游戏自然场景继续需要手测。公开v0.1仍为v287，正式基线264-05保持。
'''
    (dest/'README_先读.md').write_text(readme,encoding='utf8')
    source={'version':'v288','package':25,'ROM_SHA256':build['SHA256'],'states':states,
        'SRAM_source':sram_source.relative_to(P).as_posix(),'SRAM_SHA256':sha(sram),
        'diagnostic_ROMS_or_saves_included':False}
    (dest/'版本与存档来源.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    loads=[]
    for x in states:
        prefix=run(romfile,str(dest/x['file']),D/'idle_actions.json',f'delivered_slot{x["slot"]:03d}')
        result=rd(prefix.with_suffix('.json'));assert result['ROM_SHA']==build['SHA256']
        loads.append({'slot':x['slot'],'load_pass':True,'ROM_SHA256':result['ROM_SHA']})
    (dest/'本轮验证.json').write_text(json.dumps({'build_summary':{k:v for k,v in build.items()if k not in ['rows','writes']},
        'normal_regression':regression,'native_pixels':pixels,'states_actually_loaded':loads},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (dest/'SHA256_校验.txt').write_text('\n'.join(sha(f.read_bytes())+'  '+f.relative_to(dest).as_posix()
        for f in sorted(dest.rglob('*'))if f.is_file())+'\n',encoding='utf8')
    zf=dest.with_name(dest.name+'_with_saves.zip');assert not zf.exists()
    with zipfile.ZipFile(zf,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for f in sorted(dest.rglob('*')):
            if f.is_file():z.write(f,f.relative_to(dest).as_posix())
    with zipfile.ZipFile(zf)as z:
        assert z.testzip()is None and len([n for n in z.namelist()if n.endswith('.smc')])==1
        for f in dest.rglob('*'):
            if f.is_file():assert z.read(f.relative_to(dest).as_posix())==f.read_bytes()
    proof={'status':'PACKAGE25_FONT_GEOMETRY_NORMAL_REGRESSION_AND_PIXELS_PASS_MANUAL_PENDING',
        'ROM':build['ROM'],'ROM_SHA256':build['SHA256'],'ZIP':zf.relative_to(P).as_posix(),
        'ZIP_SHA256':sha(zf.read_bytes()),'states_loaded':len(loads),'protection_cases':regression['cases'],
        'CJK_singles_checked':build['CJK_singles_audited'],'CJK_singles_changed':build['CJK_singles_changed'],
        'all_strokes_preserved':True,'right_clip_risk_singles_remaining':0,
        'native_吗_娜_missing_pixels':0,'two_row_alignment_pixels_pass':True,
        'independent_rebuild_identical':True,'diagnostic_fixtures_excluded':True,
        'full_game_natural_scene_coverage_claimed':False,'formal_baseline_promoted':False}
    (P/'qa/V288_TESTPACKAGE25_PROOF_20261012_01.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

    m=rd('text/translations/translation_sources_current.json');assert m['build_revision']=='v287_sheraha_wording01'
    old_typed=m['latest_typed_review'];typed=rd(old_typed)
    typed.update(build_revision='v288_font_geometry01',ROM_SHA256=build['SHA256'],current_test_ROM_SHA256=build['SHA256'],
        status='COMPILED_PRIVATE_TEST_V288_PACKAGE25_MANUAL_PENDING',previous_typed_source=old_typed)
    for x in typed.get('translations',[]):
        x['current_test_ROM_SHA256']=build['SHA256']
        if 'compiled_ROM_SHA256'in x:x['compiled_ROM_SHA256']=build['SHA256']
    tf='text/translations/typed_review_integrated_v288_20261012_01.json';assert not(P/tf).exists()
    (P/tf).write_text(json.dumps(typed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    audit=rd(m['latest_translation_integration_audit'])
    audit.update(ROM_SHA256=build['SHA256'],font_geometry_validation='qa/V288_NATIVE_PIXEL_PROOF_20261012_01.json',
        text_payloads_byte_identical_to_v287=True)
    audit.setdefault('source_evidence',{})['typed']=tf
    ai='qa/V288_TRANSLATION_INTEGRATION_AUDIT_20261012_01.json'
    (P/ai).write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    atlas=rd('docs/SINGLE_GLYPH_ATLAS_V288_GEOMETRY_20261012_01.json')
    for x in atlas['glyphs']:
        raw=read_glyph(rom,glyph_locations(bytes.fromhex(x['code']))[0]);assert sha(raw)==x['glyphSha256']
        if 'glyphHex'in x:x['glyphHex']=raw.hex(' ').upper()
    (P/'docs/SINGLE_GLYPH_ATLAS_V288_GEOMETRY_20261012_01.json').write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    m.update(source_revision='20261012_font_geometry_v288_01',build_revision='v288_font_geometry01',
        status='COMPILED_PRIVATE_TEST_PACKAGE25_MANUAL_PENDING',previous_sources_manifest='text/translations/translation_sources_before_v288_20261012_01.json',
        latest_test_ROM={'file':proof['ROM'],'SHA256':proof['ROM_SHA256']},
        latest_test_package={'file':proof['ZIP'],'SHA256':proof['ZIP_SHA256']},
        latest_validation='qa/V288_TESTPACKAGE25_PROOF_20261012_01.json',
        latest_handoff='docs/HANDOFF_CODEX_20261012_V288_FONT_GEOMETRY_01.md',
        latest_save_slot_mapping=dest.relative_to(P).as_posix()+'/版本与存档来源.json',
        latest_typed_review=tf,latest_translation_integration_audit=ai,
        latest_font_atlas='docs/SINGLE_GLYPH_ATLAS_V288_GEOMETRY_20261012_01.json',
        latest_font_geometry_overlay='qa/V288_FONT_GEOMETRY_BUILD_20261012_01.json',
        latest_font_geometry_pixels='qa/V288_NATIVE_PIXEL_PROOF_20261012_01.json',
        next_action='复测包25：全套中文单字右侧笔画与上下行定位已修；加载旧即时档后重开窗口以刷新字图。')
    m['source_precedence'].append('v288字体最终定位层：全部当前中文单字按公共中线和一致取整方向平移，完整保留笔画；78/7D字库及原生别名同步。旧构建须先复现冻结输入，再应用build_v288_font_geometry_v1，不能回退至HZK12的x2原位置。复字、标点与图标的独立规则保持。')
    (P/'text/translations/translation_sources_current.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(proof,ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8');main()
