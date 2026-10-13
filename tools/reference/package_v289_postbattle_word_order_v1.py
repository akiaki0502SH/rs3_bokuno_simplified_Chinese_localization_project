"""Deliver v289 gameplay ROM; diagnostic ROMs and constructed results stay out."""
from pathlib import Path
import gzip,hashlib,json,shutil,subprocess,sys,zipfile
P=Path(__file__).resolve().parents[1]
D=P/'qa/postbattle_feedback_v289_20261013_01'
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))


def main():
    build=rd('qa/V289_POSTBATTLE_WORD_ORDER_BUILD_20261013_01.json')
    runtime=rd('qa/V289_POSTBATTLE_RUNTIME_PROOF_20261013_01.json')
    assert runtime['status']=='SEVEN_NATIVE_DISPLAY_CASES_AND_SEVEN_NORMAL_ROUTES_PASS'
    rom=(P/build['ROM']).read_bytes();assert sha(rom)==build['SHA256']
    assert rom==(P/'roms/work/bokuno_cn_diag_v289_independent_20261013_01.smc').read_bytes()
    assert rom[0x7ff280:0x7ff290]==bytes(16),'Diagnostic shim must not enter gameplay build'
    dest=(P/'artifacts/private_human_tests/bokuno_cn_v10bi289_20261013_26').resolve()
    assert dest.is_relative_to(Path('G:/CodexProjects'))and dest.is_relative_to(P)and not dest.exists()
    dest.mkdir();(dest/'存档_snes9x').mkdir();(dest/'回归画面').mkdir()
    stem='bokuno_cn_v10bi289_private_test';(dest/(stem+'.smc')).write_bytes(rom)
    shutil.copyfile(P/runtime['comparison_image'],dest/'战后提示_原生绘字对照.png')
    labels=[('settings','系统设置'),('spells','太阳术'),('dialogue','寺院外对白'),
            ('schools','术系'),('technique','技能说明'),('welcome','酒馆对白')]
    states=[]
    for i,(case,label)in enumerate(labels):
        row=next(x for x in runtime['normal_routes']if x['case']==case)
        raw=(P/row['candidate_state']).read_bytes();assert raw.startswith(b'#!s9xsnp:0012\n')
        state=gzip.compress(raw,compresslevel=9,mtime=0)
        f=dest/'存档_snes9x'/f'{stem}.{i:03d}';f.write_bytes(state)
        shutil.copyfile(P/row['candidate_image'],dest/'回归画面'/f'{i:03d}.png')
        states.append({'slot':i,'hotkey':f'F{i+1}','purpose':label,'file':f.relative_to(dest).as_posix(),
            'SHA256':sha(state),'source':row['candidate_state'],'original_input':row['state_source'],
            'normal_input_only':True,'natural_postbattle_prompt_save':False})
    sram_source='user_saves/snes9x_20261011_v284_feedback_inputs_02/bokuno_cn_v10bd284_private_test.srm'
    sram=(P/sram_source).read_bytes();(dest/'存档_snes9x'/(stem+'.srm')).write_bytes(sram)
    readme='''# 测试包26：战后习得奥义与获得物品的语序

修复朋友截图中的两种提示，继承v288的全套字体定位：

```text
习得招架的
奥义

获得了
野生药
```

名称继续由游戏读取实际技能或实际物品，以上“招架／野生药”仅是本次反馈例子。

## 原因

旧提示保留日文的“名称→助词→动作”拼接顺序。日语助词「を」在索引片段中被单独译成“把”，所以动态物品名后会出现“把”，再在下一行显示“获得了”；这不是物品名里带了“把”，也不是读取越界。奥义提示同样先输出名称和“的”，再在下一行输出“习得奥义”。

本版修正显示拼接顺序：习得先于技能名，获得了先于物品名。为较长技能名计入两个新增前置字的框宽，识破奥义保持原类别判断。原物品损坏分支保持。字库、名称表、物品属性、技能属性、掉落和习得处理保持。

## 使用

打开bokuno_cn_v10bi289_private_test.smc。可以备份后使用自己的游戏存档，自然触发战后掉落或奥义习得来复测。

包内000/F1设置、001/F2太阳术、002/F3寺院外对白、003/F4术系、004/F5技能说明、005/F6酒馆对白是六份原真实场景的正常按键回归档，适合检查此前修复是否保持。它们不是朋友截图的战后存档。旧窗口缓存可关闭再重开。

附图明确标注原生绘字的受控显示检查，分别复现旧“招架的／习得奥义”和“野生药把／获得了”，并核对新顺序；没有把受控名称选择参数伪装成实际获得物品或技能，也没有交付诊断ROM或伪造战后即时档。

## 验证范围

七组原生显示检查覆盖两条反馈、识破奥义、五字长技能名、长物品名、扩展物品及原物品损坏分支。读到的名称、动作和助词片段顺序核对通过，栈归还、文字在原生框内、角色、剧情、姓名、金钱与背包保护检查通过。损坏分支的旧新画面相同。

六处正常菜单／对白路线和一处有限正常战斗推进的保护对照通过。该战斗推进仍在战斗中，不当作朋友的完整结算复现。独立重建逐字节相同，六份交付即时档逐个载入，ZIP逐文件回读通过。完整自然战斗及全游戏仍需要实际游玩验收。

公开v0.1.1仍是v288；本包为新v289本地候选，正式264-05基线保持。
'''
    (dest/'README_先读.md').write_text(readme,encoding='utf8')
    source={'version':'v289','package':26,'ROM_SHA256':build['SHA256'],'states':states,
        'SRAM_source':sram_source,'SRAM_SHA256':sha(sram),'diagnostic_ROMS_or_controlled_states_included':False}
    (dest/'版本与存档来源.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    idle=D/'delivered_idle_actions.json';idle.write_text(json.dumps([[[],0,1]]))
    loads=[]
    for row in states:
        prefix=D/f'delivered_slot{row["slot"]:03d}'
        z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',
            str(dest/(stem+'.smc')),str(dest/row['file']),str(idle),str(prefix)],cwd=P,capture_output=True,timeout=60)
        prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr)
        assert z.returncode==0,z.stderr[-1200:]
        assert rd(prefix.with_suffix('.json'))['ROM_SHA']==build['SHA256']
        loads.append({'slot':row['slot'],'actual_load_pass':True})
    (dest/'本轮验证.json').write_text(json.dumps({'build':build,'runtime':runtime,'actual_loaded_states':loads,
        'independent_rebuild_identical':True,'friend_exact_natural_battle_save_available':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
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
    proof={'status':'PACKAGE26_NATIVE_POSTBATTLE_COMPOSITION_FIXED_MANUAL_PENDING','ROM':build['ROM'],
        'ROM_SHA256':build['SHA256'],'ZIP':zf.relative_to(P).as_posix(),'ZIP_SHA256':sha(zf.read_bytes()),
        'native_display_cases':7,'normal_route_cases':7,'real_regression_states_loaded':6,
        'UI29_把_root_cause_confirmed':True,'independent_rebuild_identical':True,
        'diagnostic_ROMS_and_constructed_reward_saves_excluded':True,'formal_baseline_promoted':False}
    (P/'qa/V289_TESTPACKAGE26_PROOF_20261013_01.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    m=rd('text/translations/translation_sources_current.json');assert m['build_revision']=='v288_font_geometry01'
    typed=rd(m['latest_typed_review']);typed.update(build_revision='v289_postbattle_word_order01',
        ROM_SHA256=build['SHA256'],current_test_ROM_SHA256=build['SHA256'],
        status='COMPILED_PRIVATE_TEST_V289_PACKAGE26_MANUAL_PENDING')
    for x in typed['translations']:
        x['current_test_ROM_SHA256']=build['SHA256']
        if 'compiled_ROM_SHA256'in x:x['compiled_ROM_SHA256']=build['SHA256']
        if x.get('text_id')in ['indexed_battle_ui_strings_3d9a00_012','indexed_battle_ui_strings_3d9a00_013',
                             'indexed_battle_ui_strings_3d9a00_01D','indexed_battle_ui_strings_3d9a00_029',
                             'indexed_battle_ui_strings_3d9a00_02B']:
            x['runtime_composition_overlay']='text/translations/postbattle_feedback_v289_20261013_01.json'
    tf='text/translations/typed_review_integrated_v289_20261013_01.json';assert not(P/tf).exists()
    (P/tf).write_text(json.dumps(typed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    atlas=rd(m['latest_font_atlas']);atlas.update(source_version='v289_postbattle_word_order01',final_ROM_SHA256=build['SHA256'])
    atlas.setdefault('notes',[]).append('v289只改战后提示拼接及相关显示框宽，v288全部字形与编码逐字节保持。')
    af='docs/SINGLE_GLYPH_ATLAS_V289_POSTBATTLE_20261013_01.json'
    (P/af).write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    audit=rd(m['latest_translation_integration_audit']);audit.update(ROM_SHA256=build['SHA256'],
        postbattle_composition_validation='qa/V289_POSTBATTLE_RUNTIME_PROOF_20261013_01.json',
        all_existing_text_payloads_and_fonts_identical_to_v288=True)
    audit.setdefault('source_evidence',{})['typed']=tf
    ai='qa/V289_TRANSLATION_INTEGRATION_AUDIT_20261013_01.json'
    (P/ai).write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    overlay={'schema':'v289-postbattle-feedback-v1','user_confirmed_patterns':
        ['习得{ACTUAL_SKILL_NAME}的奥义','获得了{ACTUAL_ITEM_NAME}'],
        'original_images':['qa/postbattle_feedback_v289_20261013_01/skill_feedback_original.png',
                           'qa/postbattle_feedback_v289_20261013_01/item_feedback_original.png'],
        'unexpected_把_source':'UI29 standalone Japanese を translated to 把 in indexed_ambiguities.json; native name-first order remained.',
        'implementation':'tools/build_v289_postbattle_word_order_v1.py','build_proof':'qa/V289_POSTBATTLE_WORD_ORDER_BUILD_20261013_01.json',
        'other_UI29_consumers_not_globally_rewritten':True,'natural_manual_review_pending':True}
    ov='text/translations/postbattle_feedback_v289_20261013_01.json'
    (P/ov).write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    m.update(source_revision='20261013_postbattle_word_order_v289_01',build_revision='v289_postbattle_word_order01',
        status='COMPILED_PRIVATE_TEST_PACKAGE26_MANUAL_PENDING',previous_sources_manifest='text/translations/translation_sources_before_v289_20261013_01.json',
        latest_test_ROM={'file':build['ROM'],'SHA256':build['SHA256']},latest_test_package={'file':proof['ZIP'],'SHA256':proof['ZIP_SHA256']},
        latest_validation='qa/V289_TESTPACKAGE26_PROOF_20261013_01.json',
        latest_handoff='docs/HANDOFF_CODEX_20261013_V289_POSTBATTLE_WORD_ORDER_01.md',latest_typed_review=tf,
        latest_font_atlas=af,latest_translation_integration_audit=ai,latest_postbattle_composition_overlay=ov,
        latest_save_slot_mapping=dest.relative_to(P).as_posix()+'/版本与存档来源.json',
        next_action='复测包26：战后奥义先习得后技能名，物品先获得了后实际名称；朋友自然战斗即时档尚未提供。')
    m['source_precedence'].append('v289最终战后提示显示层：原索引片段及名称保持，C2CE72获得分支先输出获得了、再输出实际物品名，跳过该处旧UI29把；原损坏分支保持。C2D0D4先习得、实际技名、的，再换行奥义或识破奥义，按新增前置两字计算框宽。不得由旧日文名称优先拼接回退。')
    (P/'text/translations/translation_sources_current.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(proof,ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
