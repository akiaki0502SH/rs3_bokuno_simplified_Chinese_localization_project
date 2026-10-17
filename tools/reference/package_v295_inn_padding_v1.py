"""Deliver the verified inn-padding fix and a naturally reopened quote save."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
P=Path(__file__).resolve().parents[1];D=P/'qa/inn_padding_v295_20261017_01'
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()


def main():
    b=rd('qa/V295_INN_PADDING_BUILD_20261017_01.json');v=rd('qa/V295_INN_PADDING_VERIFICATION_20261017_01.json')
    assert v['status']=='REAL_INN_REOPEN_STAY_DECLINE_CPU38_AND_THIRTEEN_PRIOR_PAIRS_PASS'
    rom=(P/b['ROM']).read_bytes();assert sha(rom)==b['SHA256']==v['SHA256']
    dest=(P/'artifacts/private_human_tests/bokuno_cn_v10bo295_20261017_32').resolve()
    assert dest.is_relative_to(Path('G:/CodexProjects'))and dest.is_relative_to(P)and not dest.exists();dest.mkdir()
    (dest/'存档_snes9x').mkdir();(dest/'对应画面').mkdir()
    stem='bokuno_cn_v10bo295_private_test';romfile=dest/(stem+'.smc');romfile.write_bytes(rom)
    prior=rd('qa/V294_TESTPACKAGE31_PROOF_20261017_01.json');folder=P/prior['package_directory']
    source=rd(folder/'版本与存档来源.json');inputs=[dict(row,origin=folder/row['file'])for row in source['states']]
    inputs.append({'slot':5,'load_key':'F6','purpose':'住宿报价5奥拉姆，旧真实存档正常取消后重新交谈生成；不是用户当前游玩进度',
        'origin':D/'reopen_candidate.state','SHA256':sha((D/'reopen_candidate.state').read_bytes())})
    actions=D/'delivery_idle.json';assert not actions.exists();actions.write_text('[[[],0,1]]',encoding='utf8');states=[]
    for row in inputs:
        slot=row['slot'];data=row['origin'].read_bytes();assert sha(data)==row['SHA256']
        saved=dest/'存档_snes9x'/f'{stem}.{slot:03d}';saved.write_bytes(data);prefix=D/f'delivered_{slot:03d}'
        z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',str(romfile),str(saved),str(actions),str(prefix)],
            cwd=P,capture_output=True,timeout=40)
        prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,z.stderr[-1000:]
        assert rd(prefix.with_suffix('.json'))['ROM_SHA']==b['SHA256']
        shutil.copyfile(prefix.with_suffix('.png'),dest/'对应画面'/f'{slot:03d}.png')
        states.append({'slot':slot,'load_key':row['load_key'],'purpose':row['purpose'],'file':saved.relative_to(dest).as_posix(),
            'SHA256':sha(data),'source':row['origin'].relative_to(P).as_posix(),'loaded_in_v295':True,'normal_input_only':True,
            'world_or_money_injection':False})
    sram=folder/'bokuno_cn_v10bn294_private_test.srm';shutil.copyfile(sram,dest/(stem+'.srm'))
    shutil.copyfile(P/v['comparison_image'],dest/'住宿报价_修正前后.png')
    readme='''# v295 住宿报价前导空白修复（包32）

已单独修复“5奥拉姆”前两格空白。1位、2位、3位价格都从本行起点显示；原金额读取、人数、报价计算、住宿收费和休息流程保持。

## 使用与查看

打开 `bokuno_cn_v10bo295_private_test.smc`，用自己的存档副本重新询问住宿。旧即时档若已显示旧报价，请先取消，再重新交谈，原缓存不会自动重绘。

随包005/F6可直接查看新报价，来自旧真实存档正常取消后重新交谈生成，没有修改队伍、金钱、剧情或价格。它是检查样例，不是你最新的游玩进度；请勿用它覆盖自己的新存档。

| 槽位 | 加载键 | 用途 |
| --- | --- | --- |
| 000 | F1 | 水鸟剑说明 |
| 001 | F2 | 次元断说明 |
| 002 | F3 | 旋转长枪说明 |
| 003 | F4 | 尤里安开场宽框 |
| 004 | F5 | “马……借我马……”窄框 |
| 005 | F6 | 新住宿报价：5奥拉姆从行首显示 |

000–004沿用包31原样档，005为本次正常重开得到的实测档；六档均已在v295载入。需要时复制“存档_snes9x”内文件到所用模拟器存档目录。原v294、包31及个人原始存档保留。

## 修复与验证

根因是原版固定三位数字将前导零改成全角空白。本版只在两处原生住宿报价命令匹配时，复用游戏已有的紧凑数字复制路径；其他数字命令继续原样输出。

两处报价入口共20组0／1／5／9／10／50／99／100／150／255的格式检查通过，0保留为一个数字；18组相邻地址及其他bank的对照证实字节、寄存器、标志和栈均保持。原生日文数字格式器和收费代码未改。

旧真实存档通过正常取消／重新交谈复现并修复，报价前减少28像素（两格），人数位置保持。正常选择住宿前30000、后29995，仍扣5奥拉姆；选择“算了”不扣款。新旧剧情、角色、姓名、背包及SRAM对照一致。

13组既有正常操作回归、六档载入和ZIP逐文件回读通过。继承v294数字字体、v293标题序文、311条排版和此前战后提示修复；没有合并其余待核排版。上述检查不等于全游戏验收。

本次只交付独立本地测试包，公开GitHub仍为v0.1.3（内部v292）；没有额外提交、推送或公开发布。
'''
    (dest/'README_先读.md').write_text(readme,encoding='utf8',newline='\n')
    (dest/'本轮验证.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    (dest/'版本与存档来源.json').write_text(json.dumps({'version':'v295','package':32,'ROM_SHA256':b['SHA256'],
        'base_ROM_SHA256':b['base_SHA256'],'states':states,'SRAM_source':sram.relative_to(P).as_posix(),
        'SRAM_SHA256':sha(sram.read_bytes()),'diagnostic_ROMs_or_synthetic_states_included':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    (dest/'SHA256_校验.txt').write_text('\n'.join(sha(f.read_bytes())+'  '+f.relative_to(dest).as_posix()for f in sorted(dest.rglob('*'))if f.is_file())+'\n',encoding='utf8',newline='\n')
    archive=dest.with_name(dest.name+'_with_saves.zip');assert not archive.exists()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for f in sorted(dest.rglob('*')):
            if f.is_file():z.write(f,f.relative_to(dest).as_posix())
    with zipfile.ZipFile(archive)as z:
        assert z.testzip()is None and len([n for n in z.namelist()if n.endswith('.smc')])==1
        for f in dest.rglob('*'):
            if f.is_file():assert z.read(f.relative_to(dest).as_posix())==f.read_bytes()
    proof={'status':'V295_PACKAGE32_INN_QUOTE_SIX_GENUINE_SAVES_AND_ZIP_PASS_MANUAL_PENDING',
        'ROM':b['ROM'],'ROM_SHA256':b['SHA256'],'ZIP':archive.relative_to(P).as_posix(),'ZIP_SHA256':sha(archive.read_bytes()),
        'package_directory':dest.relative_to(P).as_posix(),'formatter_trials':38,'normal_existing_pairs':13,'natural_inn_pairs':3,
        'delivered_saves_loaded':6,'new_inn_quote_slot':5,'ZIP_full_readback':True,
        'diagnostic_ROMs_or_synthetic_states_included':False,'public_release_unchanged':True}
    (P/'qa/V295_TESTPACKAGE32_PROOF_20261017_01.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(proof,ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
