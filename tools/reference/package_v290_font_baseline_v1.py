"""Package the three real font feedback snapshots with the baseline fix."""
from pathlib import Path
import gzip,hashlib,json,shutil,subprocess,sys,zipfile
P=Path(__file__).resolve().parents[1]
D=P/'qa/font_baseline_v290_20261014_01'
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))


def main():
    build=rd('qa/V290_FONT_BASELINE_BUILD_20261014_01.json')
    runtime=rd('qa/V290_FONT_BASELINE_RUNTIME_20261014_01.json')
    assert runtime['status']=='THREE_REAL_FEEDBACK_PIXEL_BASELINES_AND_TEN_NORMAL_ROUTES_PASS'
    rom=(P/build['ROM']).read_bytes();assert sha(rom)==build['SHA256']
    assert rom==(P/'roms/work/bokuno_cn_diag_v290_independent_20261014_01.smc').read_bytes()
    dest=(P/'artifacts/private_human_tests/bokuno_cn_v10bj290_20261014_27').resolve()
    assert dest.is_relative_to(Path('G:/CodexProjects'))and dest.is_relative_to(P)and not dest.exists()
    dest.mkdir();(dest/'存档_snes9x').mkdir();(dest/'回归画面').mkdir()
    stem='bokuno_cn_v10bj290_private_test';(dest/(stem+'.smc')).write_bytes(rom)
    states=[]
    for i,label in enumerate(['物品／装备栏王字基线','无形之位形字基线','太阳光线阳字基线']):
        row=next(x for x in runtime['routes']if x.get('slot')==i)
        raw=(P/row['candidate_state']).read_bytes();assert raw.startswith(b'#!s9xsnp:0012\n')
        data=gzip.compress(raw,compresslevel=9,mtime=0);f=dest/'存档_snes9x'/f'{stem}.{i:03d}';f.write_bytes(data)
        shutil.copyfile(P/row['candidate_image'],dest/'回归画面'/f'{i:03d}.png')
        states.append({'slot':i,'hotkey':f'F{i+1}','purpose':label,'file':f.relative_to(dest).as_posix(),
            'SHA256':sha(data),'source':row['candidate_state'],
            'original_input':f'user_saves/snes9x_20261014_v289_font_feedback_01/bokuno_cn_v10bi289_private_test.{i:03d}',
            'normal_input_refresh_only':True})
    sram_source='user_saves/snes9x_20261014_v289_font_feedback_01/bokuno_cn_v10bi289_private_test.srm'
    sram=(P/sram_source).read_bytes();(dest/'存档_snes9x'/(stem+'.srm')).write_bytes(sram)
    shutil.copyfile(P/runtime['comparison_image'],dest/'字形基线_真实存档对照.png')
    readme='''# 测试包27：王、形、阳的纵向位置

本版修复你在000、001、002中指出的字形偏高问题，继承v289战后提示语序和v288右侧笔画修复。

## 原因与修复

v288把每个字的墨点包围框裁出，再单独垂直居中。王、形、阳的字形是11像素高，原位置为y3～y13；居中后被上移为y2～y12，而相邻12像素高字仍在y2～y13，所以底部高出1像素。

本版改用正文汉字的统一底部基线y13，王、形、阳下移1像素。全套2673个中文单字检查后，60个正文汉字需要同类修正；一、二恢复原字体的短笔画设计位置。16×16存储格、字号、笔画形状与墨点数、横向位置保持，右侧安全范围仍为x0～x12。没有拉伸字形。

## 使用

打开bokuno_cn_v10bj290_private_test.smc，将“存档_snes9x”配套文件放入模拟器存档目录。

|编号|快捷键|检查内容|
|---|---|---|
|000|F1|原物品／装备场景：王字与家、戒、指的底部|
|001|F2|无形之位：形字与无、之、位的底部|
|002|F3|太阳光线：阳字与太、光、线的底部|

三份档都来自你此次提供的真实存档，通过正常切换角色、返回原角色及选择目标技能刷新字图后导出，没有改角色、装备、技能或进度。字体反馈中的实际名称按存档原画面保留，没有修改译名。你也可以加载自己的原存档，关闭重开界面或切换角色刷新旧字图后检查。

## 已做的验证

三份存档实际绘出的每个墨点与新字模完整匹配。000王及邻字的屏幕底部同为y156，001形及邻字同为y84，002阳及邻字同为y68；旧版目标字都比邻字高1像素。三条反馈和七条之前的正常路线共10组角色、剧情、姓名、金钱、背包及SRAM保护对照通过。原右侧裁笔画的酒馆路径复查缺点为0。

全部字形保留原墨点和横向位置，非中文单字字形保持；v289战后语序模块逐字节保持。独立重建一致，三份交付即时档逐个实际载入，ZIP回读一致。全游戏自然场景仍继续手测。

文本换行问题按你的要求继续登记到最后集中修复，本版没有调整换行、行距或文本内容。公开v0.1.1仍是v288；本包是本地v290复测版，正式264-05基线保持。
'''
    (dest/'README_先读.md').write_text(readme,encoding='utf8')
    (dest/'版本与存档来源.json').write_text(json.dumps({'version':'v290','package':27,'ROM_SHA256':build['SHA256'],
        'states':states,'SRAM_source':sram_source,'SRAM_SHA256':sha(sram),'original_files_not_overwritten':True},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    actions=D/'delivered_load_actions.json';actions.write_text(json.dumps([[[],0,1]]));loads=[]
    for row in states:
        prefix=D/f'delivered_slot{row["slot"]:03d}'
        z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',
            str(dest/(stem+'.smc')),str(dest/row['file']),str(actions),str(prefix)],cwd=P,capture_output=True,timeout=60)
        prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,z.stderr[-1200:]
        assert rd(prefix.with_suffix('.json'))['ROM_SHA']==build['SHA256'];loads.append({'slot':row['slot'],'load_pass':True})
    (dest/'本轮验证.json').write_text(json.dumps({'build_summary':{k:v for k,v in build.items()if k not in ['rows','writes']},
        'runtime':runtime,'actual_loaded_states':loads,'independent_rebuild_identical':True},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
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
    proof={'status':'PACKAGE27_REAL_USER_FONT_BASELINES_FIXED_MANUAL_PENDING','ROM':build['ROM'],
        'ROM_SHA256':build['SHA256'],'ZIP':zf.relative_to(P).as_posix(),'ZIP_SHA256':sha(zf.read_bytes()),
        'states_loaded':3,'normal_protection_cases':10,'feedback_pixel_baseline_cases':3,
        'body_glyphs_corrected':60,'short_stroke_glyphs_restored':['一','二'],
        'independent_rebuild_identical':True,'right_edge_fix_and_postbattle_order_preserved':True,
        'text_linebreaks_still_deferred':True,'formal_baseline_promoted':False}
    (P/'qa/V290_TESTPACKAGE27_PROOF_20261014_01.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    m=rd('text/translations/translation_sources_current.json');assert m['build_revision']=='v289_postbattle_word_order01'
    policy=m['layout_work_policy'].copy();typed=rd(m['latest_typed_review'])
    typed.update(build_revision='v290_font_baseline01',ROM_SHA256=build['SHA256'],current_test_ROM_SHA256=build['SHA256'],
        status='COMPILED_PRIVATE_TEST_V290_PACKAGE27_MANUAL_PENDING')
    for x in typed['translations']:
        x['current_test_ROM_SHA256']=build['SHA256']
        if 'compiled_ROM_SHA256'in x:x['compiled_ROM_SHA256']=build['SHA256']
    tf='text/translations/typed_review_integrated_v290_20261014_01.json';assert not(P/tf).exists()
    (P/tf).write_text(json.dumps(typed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    audit=rd(m['latest_translation_integration_audit']);audit.update(ROM_SHA256=build['SHA256'],
        font_geometry_validation='qa/V290_FONT_BASELINE_RUNTIME_20261014_01.json',
        all_text_payloads_and_postbattle_composition_identical_to_v289=True)
    audit.setdefault('source_evidence',{})['typed']=tf
    ai='qa/V290_TRANSLATION_INTEGRATION_AUDIT_20261014_01.json'
    (P/ai).write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    overlay={'schema':'v290-font-baseline-feedback-v1','user_cases':[
        {'slot':0,'issue':'物品／装备栏王字偏高'},{'slot':1,'issue':'无形之位形字偏高'},
        {'slot':2,'issue':'太阳光线阳字偏高'}],
        'root_cause':'v288对墨点包围框垂直居中，11像素高字被上移1像素，底部比12像素高邻字高1像素。',
        'repair':'正文统一底部y13，短笔画一、二保留原字体设计位置，横向和笔画不变。',
        'build':'qa/V290_FONT_BASELINE_BUILD_20261014_01.json','runtime':'qa/V290_FONT_BASELINE_RUNTIME_20261014_01.json'}
    ov='text/translations/font_baseline_feedback_v290_20261014_01.json'
    (P/ov).write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    m.update(source_revision='20261014_font_baseline_v290_01',build_revision='v290_font_baseline01',
        status='COMPILED_PRIVATE_TEST_PACKAGE27_MANUAL_PENDING',previous_sources_manifest='text/translations/translation_sources_before_v290_20261014_01.json',
        latest_test_ROM={'file':build['ROM'],'SHA256':build['SHA256']},latest_test_package={'file':proof['ZIP'],'SHA256':proof['ZIP_SHA256']},
        latest_validation='qa/V290_TESTPACKAGE27_PROOF_20261014_01.json',latest_handoff='docs/HANDOFF_CODEX_20261014_V290_FONT_BASELINE_01.md',
        latest_typed_review=tf,latest_font_atlas='docs/SINGLE_GLYPH_ATLAS_V290_BASELINE_20261014_01.json',
        latest_translation_integration_audit=ai,latest_font_geometry_overlay='qa/V290_FONT_BASELINE_BUILD_20261014_01.json',
        latest_font_geometry_pixels='qa/V290_FONT_BASELINE_RUNTIME_20261014_01.json',latest_font_baseline_overlay=ov,
        latest_save_slot_mapping=dest.relative_to(P).as_posix()+'/版本与存档来源.json',
        next_action='复测包27：原000王、001形、002阳的底部已对齐；文本换行问题继续留到最后集中修复。')
    m['source_precedence'].append('v290字体纵向定位最终层：正文汉字统一底部y13，60个正文字修正，一、二恢复原字体短笔画设计位置；保持v288横向与右侧安全列和v289语序模块。替代逐个墨点包围框垂直居中，重建须最后应用build_v290_font_baseline_v1；换行仍延期，不调整文本排版。')
    assert m['layout_work_policy']==policy
    (P/'text/translations/translation_sources_current.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(proof,ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
