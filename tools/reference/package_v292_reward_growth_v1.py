"""Package the gameplay candidate, unchanged genuine saves and labelled evidence."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
P=Path(__file__).resolve().parents[1];D=P/'qa/reward_growth_v292_20261017_02'
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
def main():
 b=rd('qa/V292_REWARD_GROWTH_BUILD_20261017_02.json');v=rd('qa/V292_REWARD_GROWTH_VERIFICATION_20261017_02.json')
 assert v['status']=='TWENTY_DISPLAY_PAIRS_ABI117_SEVEN_LEGACY_AND_THIRTEEN_NORMAL_ROUTES_PASS_MANUAL_PENDING'
 rom=(P/b['ROM']).read_bytes();assert sha(rom)==b['SHA256']==v['SHA256']
 assert rom[0x7ff280:0x7ff291]==bytes(17)
 dest=(P/'artifacts/private_human_tests/bokuno_cn_v10bl292_20261017_29').resolve()
 assert dest.is_relative_to(P)and dest.is_relative_to(Path('G:/CodexProjects'))and not dest.exists();dest.mkdir()
 for name in ['存档_snes9x','对应画面','原生入口受控检查_不是战后存档']: (dest/name).mkdir()
 stem='bokuno_cn_v10bl292_private_test';(dest/(stem+'.smc')).write_bytes(rom)
 previous=rd('qa/V291_TESTPACKAGE28_PROOF_20261017_01.json');folder=P/previous['package_directory']
 source=rd(folder/'版本与存档来源.json');states=[]
 actions=D/'delivery_idle.json';actions.write_text(json.dumps([[[],0,1]]),encoding='utf8')
 for old in source['states']:
  slot=old['slot'];name=f'{stem}.{slot:03d}';data=(folder/old['file']).read_bytes();assert sha(data)==old['SHA256']
  saved=dest/'存档_snes9x'/name;saved.write_bytes(data)
  prefix=D/f'delivered_slot{slot:03d}'
  z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',str(dest/(stem+'.smc')),str(saved),str(actions),str(prefix)],cwd=P,capture_output=True,timeout=60)
  prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,z.stderr[-1000:]
  assert rd(prefix.with_suffix('.json'))['ROM_SHA']==b['SHA256']
  shutil.copyfile(prefix.with_suffix('.png'),dest/'对应画面'/f'{slot:03d}.png')
  states.append(dict(slot=slot,load_key=old['load_key'],purpose=old['purpose'],file=saved.relative_to(dest).as_posix(),SHA256=sha(data),
   source=(folder/old['file']).relative_to(P).as_posix(),original_normal_input_only=True,loaded_in_v292=True,natural_battle_reward_save=False))
 sram=folder/'bokuno_cn_v10bk291_private_test.srm';shutil.copyfile(sram,dest/(stem+'.srm'))
 evidence=dest/'原生入口受控检查_不是战后存档'
 for name,cn in [('weapon3','弓与铳'),('tp','技力'),('sp','术力'),('money4','获得金钱')]:
  shutil.copyfile(D/f'jp_original_{name}_visible.png',evidence/f'{cn}_日文原版.png')
  shutil.copyfile(P/f'qa/reward_growth_v292_20261017_01/base03_{name}_visible.png',evidence/f'{cn}_旧v291.png')
  shutil.copyfile(D/f'candidate_{name}_visible.png',evidence/f'{cn}_修正v292.png')
 (evidence/'说明.md').write_text('这些图片来自原生显示入口的受控检查，只选择提示类别、数字和名称参数；没有实际获得金钱、提升等级或改变角色与剧情。它们不是朋友原战斗的完整重放，也没有对应的战后即时档。\n',encoding='utf8')
 readme='''# v292 战后提示修复（包29）

在包28/v291基础上修复本次三项反馈，继承311条排版及此前字体、物品和奥义提示修复。

| 提示 | 原因／原文 | 本版 |
| --- | --- | --- |
| 弓体术提升了 | 原版实际是“弓・銃がアップ！”。原生程序从隐藏条目算字数，中文名称包装层恢复到了普通“弓”的地址，三个字读成相邻的“弓＋体术”。 | 弓・铳提升了！ |
| 4获得了奥拉姆 | 原文“4オーラムを手に入れた”，旧程序仍先绘数字，再绘中文整句。 | 获得了4奥拉姆 |
| 技之力提升了 | 原文“技の力がアップ！”，直译未采用现有菜单中的“技力”。 | 技力提升了！ |
| 术之力提升了 | 同类原文“術の力がアップ！”。 | 术力提升了！ |

弓和铳共用原版同一个熟练度类别，只使用弓也会提升该共用等级；不会因为这个提示额外提升体术。为保留这个含义，本版显示“弓・铳”，没有改动成长规则。原版及新旧中文实际画面见“原生入口受控检查_不是战后存档”。

## 使用

打开`bokuno_cn_v10bl292_private_test.smc`，可继续用自己的游戏存档自然触发升级和战后结算。若使用即时档，复制一份并将前缀改为本版ROM名；保留原档。旧档如停在已绘好的提示中，继续显示旧缓存并不代表修复未生效，需重新触发一次提示。

本包沿用包28的五个真实场景即时档，已逐个在v292载入。它们方便回归排版，不是新战后提示档：

| 槽位 | 加载键 | 场景 |
| --- | --- | --- |
| 000 | F1 | 水鸟剑说明 |
| 001 | F2 | 次元断说明 |
| 002 | F3 | 旋转长枪说明 |
| 003 | F4 | 尤里安开场宽框对白 |
| 004 | F5 | 开场“马……借我马……”窄框 |

将“存档_snes9x”里的五档放入所用Snes9x的存档目录。ROM、存档和电池档均为独立副本，原v291文件保留。

## 已核对

20组新旧战后显示对照覆盖全部11个武器／术系标签、HP、技力、术力、1／4／10／999／9999奥拉姆及金额上限分支。后者为“获得了4奥拉姆，但／却装不下”。117个索引取址和长度检查通过，包括空项、边界及寄存器状态。

此前7项物品、普通／识破奥义、长名称、扩展物品与损坏显示回归通过；13组正常按键对照的角色、剧情、姓名、金钱、背包及SRAM一致。311条排版载荷、字体及原版奖励／成长处理保持；ZIP逐文件回读通过。

术语复核覆盖当前2423条分类译稿及12491条对白／说明排版清单，同类统计用语另发现“术之力”并已修正。对白“需要蕴含白虎术之力的武具”是在描述魔法力量，保留原意。

本次没有朋友截图前的自然战斗即时档；提示以原生显示入口复现，正常战斗流程仍需继续手测。没有提供修改角色数据的战后存档。公开版本仍为v0.1.2，尚未发布本次改动。
'''
 (dest/'README_先读.md').write_text(readme,encoding='utf8')
 (dest/'版本与存档来源.json').write_text(json.dumps(dict(version='v292',package=29,ROM_SHA256=b['SHA256'],base_ROM_SHA256=b['base_SHA256'],states=states,
  SRAM_source=sram.relative_to(P).as_posix(),SRAM_SHA256=sha(sram.read_bytes()),controlled_states_or_diagnostic_ROMs_included=False),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (dest/'本轮验证.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (dest/'SHA256_校验.txt').write_text('\n'.join(sha(f.read_bytes())+'  '+f.relative_to(dest).as_posix()for f in sorted(dest.rglob('*'))if f.is_file())+'\n',encoding='utf8')
 zipfile_path=dest.with_name(dest.name+'_with_saves.zip');assert not zipfile_path.exists()
 with zipfile.ZipFile(zipfile_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for f in sorted(dest.rglob('*')):
   if f.is_file():z.write(f,f.relative_to(dest).as_posix())
 with zipfile.ZipFile(zipfile_path)as z:
  assert z.testzip()is None and len([n for n in z.namelist()if n.endswith('.smc')])==1
  for f in dest.rglob('*'):
   if f.is_file():assert z.read(f.relative_to(dest).as_posix())==f.read_bytes()
 proof=dict(status='V292_PACKAGE29_REWARD_GROWTH_FIXED_FIVE_SAVES_LOADED_MANUAL_PENDING',ROM=b['ROM'],ROM_SHA256=b['SHA256'],
  ZIP=zipfile_path.relative_to(P).as_posix(),ZIP_SHA256=sha(zipfile_path.read_bytes()),package_directory=dest.relative_to(P).as_posix(),
  native_display_pairs=20,previous_native_display_cases=7,normal_paired_routes=13,getter_length_ABI_indices=117,delivered_saves_loaded=5,
  ZIP_full_readback=True,controlled_states_or_diagnostic_ROMs_included=False,public_release_unchanged=True,formal_baseline_promoted=False)
 (P/'qa/V292_TESTPACKAGE29_PROOF_20261017_02.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(proof,ensure_ascii=False))
if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
