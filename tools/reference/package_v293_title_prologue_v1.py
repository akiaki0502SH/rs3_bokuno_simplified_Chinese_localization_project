"""Package only the verified v293 title ROM and unchanged genuine saves."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
P=Path(__file__).resolve().parents[1]
D=P/'qa/title_prologue_v293_20261017_01'
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))


def main():
    b=rd('qa/V293_TITLE_PROLOGUE_BUILD_20261017_05.json')
    v=rd('qa/V293_TITLE_PROLOGUE_VERIFICATION_20261017_05.json')
    assert v['status']=='FOUR_NATIVE_TITLE_PAGES_TWO_CORES_AND_THIRTEEN_NORMAL_PAIRS_PASS'
    rom=(P/b['ROM']).read_bytes();assert sha(rom)==b['SHA256']==v['SHA256']
    dest=(P/'artifacts/private_human_tests/bokuno_cn_v10bm293_20261017_30').resolve()
    assert dest.is_relative_to(Path('G:/CodexProjects'))and dest.is_relative_to(P)and not dest.exists()
    dest.mkdir();(dest/'存档_snes9x').mkdir();(dest/'对应画面').mkdir();(dest/'标题动画四屏').mkdir()
    stem='bokuno_cn_v10bm293_private_test';romfile=dest/(stem+'.smc');romfile.write_bytes(rom)
    previous=rd('qa/V292_TESTPACKAGE29_PROOF_20261017_02.json');folder=P/previous['package_directory']
    source=rd(folder/'版本与存档来源.json');states=[]
    actions=D/'delivery05_idle.json';assert not actions.exists();actions.write_text('[[[],0,1]]',encoding='utf8')
    for old in source['states']:
        slot=old['slot'];data=(folder/old['file']).read_bytes();assert sha(data)==old['SHA256']
        saved=dest/'存档_snes9x'/f'{stem}.{slot:03d}';saved.write_bytes(data)
        prefix=D/f'delivered05_{slot:03d}'
        z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',
            str(romfile),str(saved),str(actions),str(prefix)],cwd=P,capture_output=True,timeout=40)
        prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,z.stderr[-1000:]
        assert rd(prefix.with_suffix('.json'))['ROM_SHA']==b['SHA256']
        shutil.copyfile(prefix.with_suffix('.png'),dest/'对应画面'/f'{slot:03d}.png')
        states.append({'slot':slot,'load_key':old['load_key'],'purpose':old['purpose'],
            'file':saved.relative_to(dest).as_posix(),'SHA256':sha(data),
            'source':(folder/old['file']).relative_to(P).as_posix(),'loaded_in_v293':True,
            'natural_title_snapshot':False,'original_normal_input_only':True})
        assert (folder/old['file']).read_bytes()==data
    sram=folder/'bokuno_cn_v10bl292_private_test.srm';shutil.copyfile(sram,dest/(stem+'.srm'))
    for row in v['native_display_pages']:
        shutil.copyfile(P/row['image'],dest/'标题动画四屏'/f"{row['page']:02d}.png")
    text='标题动画序文：用户确认版（v293）\n行尾逗号、句号已去除，句内标点与省略号保留。\n'
    for page in b['pages']:text+=f"\n第{page['page']}屏\n"+'\n'.join(page['lines'])+'\n'
    (dest/'标题动画序文_确认译文.txt').write_text(text,encoding='utf8',newline='\n')
    (P/'docs/标题动画序文_用户确认版_20261017.txt').write_text(text,encoding='utf8',newline='\n')
    readme='''# v293 标题动画序文汉化（包30）

本包采用你确认的四屏译文：死食、魔王、圣王、新的宿命之子。中文行尾不带逗号、句号，保留句内标点与省略号，按原版16字格居中。

## 查看新序文

打开 `bokuno_cn_v10bm293_private_test.smc`，重新开机播放标题动画，先不要加载即时档或按Start跳过。完整序文约两分钟；四屏实际画面见“标题动画四屏”，确认文字见“标题动画序文_确认译文.txt”。Start仍可正常跳过动画并进入标题菜单。

旧即时档保存的是当时已绘制的画面，加载后不会自动变成新标题动画；查看本次修改请重新开机。

## 本版修复

标题序文走独立的全屏绘字入口，绕过正文中文取文入口。现仅将四个序文事件切换到新译文，并在结束时恢复原来的指针、边界和字库选择。另修复这条入口对扩展字丢失字形编号低字节的问题，包括“踪”等原生扩展字。

继承包29的311条排版、战后弓／铳成长、技力／术力、金钱语序，以及此前字体和菜单修复。原剧情、奖励处理、原生脚本和旧译文载荷保留。

## 随包五份旧场景档

这些是包29的原样副本，均已在v293载入；用于继续回归，并非标题动画即时档：

| 槽位 | 加载键 | 场景 |
| --- | --- | --- |
| 000 | F1 | 水鸟剑说明 |
| 001 | F2 | 次元断说明 |
| 002 | F3 | 旋转长枪说明 |
| 003 | F4 | 尤里安开场宽框对白 |
| 004 | F5 | 开场“马……借我马……”窄框 |

如需使用，复制“存档_snes9x”内文件到模拟器存档目录。原个人存档、v292 ROM及包29保留。可为自己的存档副本改为本版ROM前缀后继续游玩。

## 已验证

Mesen与Snes9x 1.63均从冷启动播放四屏，448次绘字（含居中空格）的字形编号和行列位置完全符合确认稿；109个虚拟字的实际字体取址检查通过，包含新译文的原生扩展字也逐字核对。两个核心的四屏文字像素一致，四次结束边界与寄存器／栈检查通过。

13组既有正常操作新旧对照的剧情、角色、姓名、金钱、背包和SRAM一致，Start跳过进入标题菜单正常，五档逐个载入及ZIP回读通过。以上是本次修改及既有有限路线的检查，不代表全游戏流程已验收。

当前公开GitHub仍为v0.1.3（内部v292）；本次仅交付独立本地测试包，没有提交、推送或更新公开发行。
'''
    (dest/'README_先读.md').write_text(readme,encoding='utf8',newline='\n')
    (dest/'版本与存档来源.json').write_text(json.dumps({'version':'v293','package':30,'ROM_SHA256':b['SHA256'],
        'base_ROM_SHA256':b['base_SHA256'],'states':states,'SRAM_source':sram.relative_to(P).as_posix(),
        'SRAM_SHA256':sha(sram.read_bytes()),'diagnostic_ROMs_or_synthetic_states_included':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    (dest/'本轮验证.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    (dest/'SHA256_校验.txt').write_text('\n'.join(sha(f.read_bytes())+'  '+f.relative_to(dest).as_posix()
        for f in sorted(dest.rglob('*'))if f.is_file())+'\n',encoding='utf8',newline='\n')
    zip_path=dest.with_name(dest.name+'_with_saves.zip');assert not zip_path.exists()
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for f in sorted(dest.rglob('*')):
            if f.is_file():z.write(f,f.relative_to(dest).as_posix())
    with zipfile.ZipFile(zip_path)as z:
        assert z.testzip()is None and len([n for n in z.namelist()if n.endswith('.smc')])==1
        for f in dest.rglob('*'):
            if f.is_file():assert z.read(f.relative_to(dest).as_posix())==f.read_bytes()
    proof={'status':'V293_PACKAGE30_FOUR_TITLE_PAGES_AND_FIVE_GENUINE_SAVES_VERIFIED_MANUAL_PENDING',
        'ROM':b['ROM'],'ROM_SHA256':b['SHA256'],'ZIP':zip_path.relative_to(P).as_posix(),
        'ZIP_SHA256':sha(zip_path.read_bytes()),'package_directory':dest.relative_to(P).as_posix(),
        'natural_title_pages_verified':4,'normal_input_pairs':13,'delivered_saves_loaded':5,
        'ZIP_full_readback':True,'diagnostic_ROMs_or_synthetic_states_included':False,'public_release_unchanged':True}
    (P/'qa/V293_TESTPACKAGE30_PROOF_20261017_05.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(proof,ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
