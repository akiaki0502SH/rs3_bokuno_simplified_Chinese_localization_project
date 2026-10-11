"""Create translation-only IPS/BPS and verify the complete two-patch chain."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zlib,zipfile
P=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
def metadata(path):
 data=path.read_bytes();return {'file':path.name,'bytes':len(data),'SHA256':sha(data),'CRC32':f'{zlib.crc32(data)&0xffffffff:08X}'}
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--tag',default='20261011_01')
 parser.add_argument('--flips',default='G:/Emu/SFC/flips-windows/flips.exe')
 parser.add_argument('--stock-rom',default=str(P.parent/'roms/source/rs3_v1.1_original_analysis.sfc'))
 parser.add_argument('--bokuno-rom',default=str(P.parent/'roms/source/bokuno_proto_1.123_analysis.sfc'))
 parser.add_argument('--bokuno-patch',default='G:/Emu/SFC/浪漫3bokuno改造版/ぼくの（略更新/ぼくのProto1.123.ips')
 args=parser.parse_args();assert args.tag.replace('_','').isalnum()
 current=json.loads((P/'text/translations/translation_sources_current.json').read_text(encoding='utf8'))
 version=current['build_revision'].split('_',1)[0];assert version.startswith('v')and version[1:].isdigit()
 target=(P/current['latest_test_ROM']['file']).resolve();target_bytes=target.read_bytes();assert sha(target_bytes)==current['latest_test_ROM']['SHA256']
 flips=Path(args.flips).resolve();stock=Path(args.stock_rom).resolve();base=Path(args.bokuno_rom).resolve();original_patch=Path(args.bokuno_patch).resolve()
 assert metadata(stock)['SHA256']=='3EFA91F18CC6CD012BC213FF421813C113DF51E62F68180CC54C782F21616897'
 assert metadata(base)['SHA256']=='4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0'
 assert stock.stat().st_size==4194304 and base.stat().st_size==len(target_bytes)==8388608
 dest=(P/f'artifacts/patches/bokuno_cn_{version}_Proto1.123_{args.tag}').resolve()
 qa=(P/f'qa/patch_chain_{version}_{args.tag}').resolve()
 assert dest.is_relative_to(Path('G:/CodexProjects'))and dest.is_relative_to(P)and not dest.exists()
 assert qa.is_relative_to(P)
 if not qa.exists():qa.mkdir()
 dest.mkdir(parents=True)
 original_inputs={str(f):metadata(f)for f in [flips,stock,base,original_patch,target]}
 def call(label,arguments,expect_success=True):
  result=subprocess.run([str(flips)]+[str(x)for x in arguments],cwd=P,capture_output=True,timeout=180)
  (qa/(label+'.stdout.txt')).write_bytes(result.stdout+result.stderr)
  if expect_success:assert result.returncode==0,(label,result.returncode,result.stdout,result.stderr)
  return {'command':label,'exit':result.returncode,'stdout':result.stdout.decode('utf8','replace').strip(),'stderr':result.stderr.decode('utf8','replace').strip()}
 stage1=qa/'stage1_bokuno_from_rs3.sfc'
 if stage1.exists():
  assert stage1.read_bytes()==base.read_bytes()
  stage1_run={'command':'stage1_reused_verified_original_patch_output','exit':0,'stdout':'','stderr':''}
 else:stage1_run=call('stage1_apply_bokuno',['--apply',original_patch,stock,stage1])
 assert stage1.read_bytes()==base.read_bytes()
 ips=dest/f'bokuno_cn_{version}_for_Proto1.123.ips';bps=dest/f'bokuno_cn_{version}_for_Proto1.123.bps'
 create_ips=call('create_translation_ips',['--create','--ips',base,target,ips])
 create_bps=call('create_translation_bps',['--create','--bps',base,target,bps])
 ips_out=qa/'stage2_cn_from_chain_ips.sfc';bps_out=qa/'stage2_cn_from_chain_bps.sfc';assert not ips_out.exists()and not bps_out.exists()
 ips_run=call('apply_translation_ips',['--apply',ips,stage1,ips_out])
 bps_run=call('apply_translation_bps',['--apply',bps,stage1,bps_out])
 assert ips_out.read_bytes()==bps_out.read_bytes()==target_bytes
 info=call('bps_info',['--info',bps]);raw=bps.read_bytes();assert raw[:4]==b'BPS1'
 source_crc=int.from_bytes(raw[-12:-8],'little');target_crc=int.from_bytes(raw[-8:-4],'little');patch_crc=int.from_bytes(raw[-4:],'little')
 assert source_crc==zlib.crc32(base.read_bytes())&0xffffffff and target_crc==zlib.crc32(target_bytes)&0xffffffff
 assert patch_crc==zlib.crc32(raw[:-4])&0xffffffff
 assert ips.read_bytes().startswith(b'PATCH')
 wrong=qa/'diagnostic_wrong_source.sfc';wrongbytes=bytearray(base.read_bytes());wrongbytes[0x7FFE10]^=1;wrong.write_bytes(wrongbytes)
 rejected=qa/'must_not_be_created_by_wrong_source.sfc';negative=call('reject_wrong_source_bps',['--apply',bps,wrong,rejected],expect_success=False)
 assert negative['exit']!=0 and not rejected.exists(),negative
 proof={'schema':'translation-patch-chain-v1','status':'COMPLETE_RS3_BOKUNO_CN_CHAIN_BYTE_IDENTICAL_PASS','version':version,'build_revision':current['build_revision'],'tool':metadata(flips),'stages':{'source_rs3_v11_headerless':metadata(stock),'original_bokuno_ips':metadata(original_patch),'stage1_bokuno':metadata(stage1),'translation_target':metadata(target),'ips_result':metadata(ips_out),'bps_result':metadata(bps_out)},'patches':[metadata(ips),metadata(bps)],'stage1_matches_verified_bokuno_base':True,'both_stage2_results_byte_identical_to_current_test_ROM':True,'bps_checksums_verified':{'source':f'{source_crc:08X}','target':f'{target_crc:08X}','patch':f'{patch_crc:08X}'},'wrong_source_bps_rejected':True,'diagnostic_wrong_source_ROM_not_delivered':True,'runs':[stage1_run,create_ips,create_bps,ips_run,bps_run,info,negative],'no_ROM_or_original_bokuno_patch_or_tool_in_distribution':True,'manual_gameplay_acceptance_pending':True,'formal_baseline_promoted':False}
 (dest/'补丁链验证.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 readme=f'''# Bokuno Proto1.123 汉化补丁 {version}（测试版）

本包只包含汉化差异补丁、说明与校验记录。适用于日文Bokuno Proto1.123，汉化内容对应当前工程测试版本{version}（{current['build_revision']}）。实际游玩验收仍在进行，正式基线没有提升。

## 正确顺序

1. 准备日文《Romancing SaGa 3》v1.1原版ROM，文件大小4,194,304字节，无512字节拷贝器头。
2. 使用你自行取得的 `ぼくのProto1.123.ips`，得到日文Bokuno Proto1.123 ROM，大小8,388,608字节。
3. 对第二步得到的ROM应用本包汉化补丁。IPS和BPS是同一汉化内容的两种格式，任选一种即可，无需连续打两种。

建议保存每一步的新文件，保留原版ROM。扩展名 `.smc` 或 `.sfc` 不决定内容版本，请以大小和校验值为准。

## 用你现有的Flips

打开 Flips，点 `Apply Patch`：先选Bokuno作者的IPS，再选日文RS3 v1.1 ROM，另存为日文Bokuno。

再次点 `Apply Patch`，选本包 `{bps.name}`，再选上一步的日文Bokuno ROM，另存汉化版。BPS会检查底片是否匹配，推荐使用。你也可以选择 `{ips.name}`；IPS本身不核对底片，请确认使用的是第二步的正确ROM。

不要选择已打其他汉化补丁或其他改造补丁的ROM作为本补丁底片；本次已验证的是作者原始Proto1.123链。其他附加补丁的组合尚未验证。

## 校验值

|步骤|大小|CRC32|
|---|---|---|
|日文RS3 v1.1原版|4,194,304字节|6C50C2CF|
|打完Bokuno Proto1.123|8,388,608字节|7E165025|
|打完汉化补丁|8,388,608字节|{zlib.crc32(target_bytes)&0xffffffff:08X}|

SHA256：

```text
RS3 v1.1
3EFA91F18CC6CD012BC213FF421813C113DF51E62F68180CC54C782F21616897

Bokuno Proto1.123
4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0

汉化输出
{sha(target_bytes)}
```

## 已做的补丁验证

用你现有的Flips，从上述RS3原版实际应用作者Bokuno IPS，输出逐字节符合工程的日文底片；再分别应用汉化IPS和BPS，两者输出都与当前汉化测试ROM逐字节一致。BPS的源、目标及补丁校验均核对通过，另用一个有字节差异的底片验证拒绝错误输入。

这证明补丁链和当前测试ROM一致；实际游戏测试仍以当前汉化版本的验收范围为准。包内不含原版ROM、Bokuno ROM、汉化ROM、原Bokuno补丁或Flips程序。
'''
 (dest/'README_补丁使用说明.md').write_text(readme,encoding='utf8')
 (dest/'SHA256_补丁校验.txt').write_text('\n'.join(metadata(f)['SHA256']+'  '+f.name for f in [ips,bps])+'\n',encoding='utf8')
 zf=dest.with_name(dest.name+'_patches_only.zip');assert not zf.exists()
 with zipfile.ZipFile(zf,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for f in sorted(dest.iterdir()):
   assert f.is_file()and f.suffix.lower()in['.ips','.bps','.md','.json','.txt'];z.write(f,f.name)
 with zipfile.ZipFile(zf)as z:
  assert z.testzip()is None and len(z.namelist())==5
  assert not any(Path(n).suffix.lower()in['.smc','.sfc','.srm','.exe','.dll','.000','.001']for n in z.namelist())
  for f in dest.iterdir():assert z.read(f.name)==f.read_bytes()
 for f,old in original_inputs.items():assert metadata(Path(f))==old,f
 summary={'status':proof['status'],'build_revision':current['build_revision'],'ZIP':zf.relative_to(P).as_posix(),'ZIP_SHA256':sha(zf.read_bytes()),'ZIP_bytes':zf.stat().st_size,'directory':dest.relative_to(P).as_posix(),'patches':[metadata(ips),metadata(bps)],'output_ROM_SHA256':sha(target_bytes),'original_inputs_unchanged':True,'distribution_file_count':5,'distribution_contains_no_ROM':True}
 (P/f'qa/TRANSLATION_PATCH_CHAIN_{version.upper()}_{args.tag}.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 current['latest_translation_patch_package']={'file':summary['ZIP'],'SHA256':summary['ZIP_SHA256'],'source_bokuno_SHA256':metadata(base)['SHA256'],'output_ROM_SHA256':sha(target_bytes),'formats':['IPS','BPS'],'status':'TEST_PATCH_COMPLETE_CHAIN_VERIFIED_MANUAL_PENDING'}
 current['latest_translation_patch_validation']=f'qa/TRANSLATION_PATCH_CHAIN_{version.upper()}_{args.tag}.json'
 (P/'text/translations/translation_sources_current.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
