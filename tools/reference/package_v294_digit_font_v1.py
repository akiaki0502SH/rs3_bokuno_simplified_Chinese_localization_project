"""Deliver the verified digit font candidate with unchanged genuine saves."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
P=Path(__file__).resolve().parents[1];D=P/'qa/digit_font_v294_20261017_01'
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()


def main():
    b=rd('qa/V294_DIGIT_FONT_BUILD_20261017_01.json');v=rd('qa/V294_DIGIT_FONT_VERIFICATION_20261017_01.json')
    runtime=rd('qa/V294_DIGIT_FONT_RUNTIME_20261017_01.json')
    assert v['status']=='EXACT_APPROVED_DIGITS_BYTE_DIFF_AND_RUNTIME_CHECKS_PASS_MANUAL_PENDING'
    rom=(P/b['ROM']).read_bytes();assert sha(rom)==b['SHA256']==v['SHA256']
    dest=(P/'artifacts/private_human_tests/bokuno_cn_v10bn294_20261017_31').resolve()
    assert dest.is_relative_to(Path('G:/CodexProjects'))and dest.is_relative_to(P)and not dest.exists()
    dest.mkdir()
    for name in ['存档_snes9x','对应画面','数字字形检查_受控非原截图场景']:(dest/name).mkdir()
    stem='bokuno_cn_v10bn294_private_test';romfile=dest/(stem+'.smc');romfile.write_bytes(rom)
    previous=rd('qa/V293_TESTPACKAGE30_PROOF_20261017_05.json');folder=P/previous['package_directory']
    source=rd(folder/'版本与存档来源.json');states=[]
    actions=D/'delivery_idle.json';assert not actions.exists();actions.write_text('[[[],0,1]]',encoding='utf8')
    for row in source['states']:
        slot=row['slot'];data=(folder/row['file']).read_bytes();assert sha(data)==row['SHA256']
        file=dest/'存档_snes9x'/f'{stem}.{slot:03d}';file.write_bytes(data)
        prefix=D/f'delivered_{slot:03d}'
        z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',
            str(romfile),str(file),str(actions),str(prefix)],cwd=P,capture_output=True,timeout=40)
        prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,z.stderr[-1000:]
        assert rd(prefix.with_suffix('.json'))['ROM_SHA']==b['SHA256']
        shutil.copyfile(prefix.with_suffix('.png'),dest/'对应画面'/f'{slot:03d}.png')
        states.append({'slot':slot,'load_key':row['load_key'],'purpose':row['purpose'],
            'file':file.relative_to(dest).as_posix(),'SHA256':sha(data),'source':(folder/row['file']).relative_to(P).as_posix(),
            'original_normal_input_only':True,'loaded_in_v294':True,'numeric_feedback_scene':False})
    sram=folder/'bokuno_cn_v10bm293_private_test.srm';shutil.copyfile(sram,dest/(stem+'.srm'))
    evidence=dest/'数字字形检查_受控非原截图场景'
    shutil.copyfile(P/runtime['comparison_image'],evidence/'实际对白数字_修正前后.png')
    for row in runtime['dialogue_pixel_pairs']:
        shutil.copyfile(P/row['candidate_image'],evidence/(row['phrase']+'_绘字检查.png'))
    for row in runtime['reward_display_pairs']:
        shutil.copyfile(P/row['candidate_image'],evidence/(row['case']+'_金额显示检查.png'))
    (evidence/'说明.txt').write_text('对白图通过替换真实酒馆窗口的四个显示字形来检查像素，未改剧情或角色。金额图使用既有原生结果窗口的受控显示入口。它们不是原“捡到男婴”场景的自然重放；诊断ROM和状态不随包交付。\n',encoding='utf8')
    readme='''# v294 数字字形修正（包31）

按已确认的预览统一0–9的字形大小与字底：数字高10像素，与正文汉字字底对齐。原生字形笔画保留，字格仍按原有宽度前进；“5”左右各留3像素，没有单独挪偏。

## 使用

打开 `bokuno_cn_v10bn294_private_test.smc`，可继续使用原有存档的副本。若旧即时档停在已画好的文字上，请关闭重开窗口或重新触发对白；缓存中的旧数字不会在载入时自动重绘。

旧v293、个人原始存档和包30保留。五个随包档为包30的原样副本，已在v294载入，用来回归原说明／开场场景，并非新“15”反馈场景：000/F1水鸟剑说明，001/F2次元断说明，002/F3旋转长枪说明，003/F4尤里安开场宽框，004/F5“马……借我马……”窄框。

## 修正范围

原来ASCII 0、1、2、3、5使用8像素小号字，4、6、7、8、9使用较大的原生数字，且字底位置不一致。本版按预览统一这两套数字及全角数字的对应字形，兼顾正文和共用的原生金额数字。

只修改数字字模及ROM校验和；汉字、文本字节、换行、剧情命令、数字数值、绘字程序和字距均保持。继承v293四屏标题序文、311条排版和此前战后提示修复。

## 已检查

5组真实对白绘字流程的受控像素对照，覆盖0–9、“15年前”和数字／汉字混排；所有墨点完整，字底与汉字一致。13组既有正常按键新旧对照的角色、剧情、姓名、金钱、背包及SRAM一致；3组原生金额显示对照通过。v293标题四屏逐像素保持，五档载入及ZIP逐文件回读通过。

“数字字形检查_受控非原截图场景”包含检查图。这些图不代表已取得并自然重放用户截图原剧情；全游戏流程仍需继续手测。

当前公开GitHub仍是v0.1.3（内部v292）；本次只交付本地测试包，没有额外提交、推送或公开发布。
'''
    (dest/'README_先读.md').write_text(readme,encoding='utf8',newline='\n')
    (dest/'本轮验证.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    (dest/'版本与存档来源.json').write_text(json.dumps({'version':'v294','package':31,'ROM_SHA256':b['SHA256'],
        'base_ROM_SHA256':b['base_SHA256'],'states':states,'SRAM_source':sram.relative_to(P).as_posix(),
        'SRAM_SHA256':sha(sram.read_bytes()),'diagnostic_ROMs_or_synthetic_states_included':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    (dest/'SHA256_校验.txt').write_text('\n'.join(sha(f.read_bytes())+'  '+f.relative_to(dest).as_posix()
        for f in sorted(dest.rglob('*'))if f.is_file())+'\n',encoding='utf8',newline='\n')
    archive=dest.with_name(dest.name+'_with_saves.zip');assert not archive.exists()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for f in sorted(dest.rglob('*')):
            if f.is_file():z.write(f,f.relative_to(dest).as_posix())
    with zipfile.ZipFile(archive)as z:
        assert z.testzip()is None and len([n for n in z.namelist()if n.endswith('.smc')])==1
        for f in dest.rglob('*'):
            if f.is_file():assert z.read(f.relative_to(dest).as_posix())==f.read_bytes()
    proof={'status':'V294_PACKAGE31_REVIEWED_DIGITS_FIVE_GENUINE_SAVES_AND_ZIP_PASS_MANUAL_PENDING',
        'ROM':b['ROM'],'ROM_SHA256':b['SHA256'],'ZIP':archive.relative_to(P).as_posix(),
        'ZIP_SHA256':sha(archive.read_bytes()),'package_directory':dest.relative_to(P).as_posix(),
        'normal_input_pairs':13,'dialogue_pixel_pairs':5,'reward_display_pairs':3,'delivered_saves_loaded':5,
        'ZIP_full_readback':True,'diagnostic_ROMs_or_synthetic_states_included':False,'public_release_unchanged':True}
    (P/'qa/V294_TESTPACKAGE31_PROOF_20261017_01.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(proof,ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
