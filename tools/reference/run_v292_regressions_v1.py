"""Normal-input regression pairs plus unchanged native result branches."""
from pathlib import Path
import concurrent.futures,hashlib,json,os,subprocess,sys
P=Path(__file__).resolve().parents[1];D=P/'qa/reward_growth_v292_20261017_02'
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
PROTECTED=[('flags',0xf400,0xf800),('actors',0xf561,0xf561+26*48),('extended',0x1f960,0x1f960+33*48),
 ('name',0xf300,0xf308),('money',0xf31a,0xf31c),('inventory',0xf320,0xf400)]
def main():
 b=rd('qa/V292_REWARD_GROWTH_BUILD_20261017_02.json');old=rd('qa/V291_NORMAL_REGRESSION_20261017_01.json')
 assert old['ROM_SHA256']==b['base_SHA256'];rom=P/b['ROM'];data=rom.read_bytes()
 rows=[]
 def normal(row):
  prefix=D/('normal_'+row['case']);state=P/row['state_source'];digest=sha(state.read_bytes())
  if not prefix.with_suffix('.json').exists():
   z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',str(rom),str(state),row['actions'],str(prefix)],cwd=P,capture_output=True,timeout=60)
   prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,z.stderr[-1000:]
  assert rd(prefix.with_suffix('.json'))['ROM_SHA']==b['SHA256']
  a=(P/row['candidate_state']).with_suffix('.ram').read_bytes();c=prefix.with_suffix('.ram').read_bytes()
  checks={k:a[lo:hi]==c[lo:hi]for k,lo,hi in PROTECTED}
  checks['SRAM_exact']=(P/row['candidate_state']).with_suffix('.srm').read_bytes()==prefix.with_suffix('.srm').read_bytes()
  checks['input_unchanged']=sha(state.read_bytes())==digest
  assert all(checks.values()),(row['case'],checks)
  print('normal',row['case'],'PASS',flush=True)
  return dict(case=row['case'],checks=checks,state_source=row['state_source'],actions=row['actions'],
   candidate_state=prefix.with_suffix('.state').relative_to(P).as_posix(),candidate_image=prefix.with_suffix('.png').relative_to(P).as_posix(),normal_input_only=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(normal,old['rows']))
 # Run the existing getter/length ABI fixture against all 117 indices, including
 # empty/sentinel fallback boundaries. No draw or actor/world edits.
 for label,key in [('base','base_ROM'),('candidate','ROM')]:
  trace=D/f'ABI117_{label}.txt'
  if not trace.exists():
   env=os.environ.copy();env.update(CN_BMSG_STATE=str(P/'qa/bmsg_controlled_native26405_20261008_02_native_ui_before_inject.mss'),CN_SMOKE_TRACE=str(trace))
   z=subprocess.run([str(P/'qa/mesen_isolated_runner/Mesen.exe'),'--testrunner',str(P/b[key]),str(P/'tools/mesen_battle_length_ABI_native_callframe_v1.lua'),'--timeout=45000'],cwd=P,env=env,capture_output=True,timeout=55,creationflags=subprocess.CREATE_NO_WINDOW)
   (D/f'ABI117_{label}.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,(label,z.stderr[-1000:])
  assert 'trials=117 completed=117'in trace.read_text()
  print('ABI117',label,'PASS',flush=True)
 # Existing v289 fixtures remain controlled display tests, never save files.
 cases=[('item','herb',234,False,False,False),('mastery','mastery',15,False,False,False),
  ('mastery','evasion_v2',221,False,False,False),('item','destruction',234,False,True,False),
  ('item','long_item_v2',203,False,False,False),('mastery','long_skill_v2',48,False,False,False),
  ('item','extended_item_v2',218,False,False,True)]
 for kind,name,id,special,destroyed,extended in cases:
  prefix=D/f'legacy_{name}'
  if prefix.with_suffix('.json').exists():continue
  diag=bytearray(data);finish=0xceea if kind=='item'else 0xd14a
  wait=bytes.fromhex('22 a3 b8 fe a9 1e 85 16 22 7a c1 fe 5c')+finish.to_bytes(2,'little')+b'\xc2'
  diag[0x7ff280:0x7ff280+len(wait)]=wait;path=D/f'legacy_{name}.smc';path.write_bytes(diag)
  env=os.environ.copy();env.update(CN_REWARD_SEED=str(P/'qa/bmsg_controlled_native26405_20261008_02_native_ui_before_inject.mss'),CN_REWARD_PREFIX=str(prefix),
   CN_REWARD_KIND=kind,CN_REWARD_ID=str(id),CN_REWARD_SPECIAL=str(int(special)),CN_REWARD_DESTROYED=str(int(destroyed)),CN_REWARD_EXTENDED=str(int(extended)))
  z=subprocess.run([str(P/'qa/mesen_isolated_runner/Mesen.exe'),'--testrunner',str(path),str(P/'tools/mesen_v289_postbattle_probe_v1.lua'),'--timeout=45000'],cwd=P,env=env,capture_output=True,timeout=55,creationflags=subprocess.CREATE_NO_WINDOW)
  prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,(name,z.stderr[-1000:])
  prefix.with_suffix('.json').write_text(json.dumps(dict(source_SHA256=b['SHA256'],diagnostic_SHA256=sha(diag),kind=kind,id=id,special=special,destroyed=destroyed,extended=extended,display_only=True),indent=2)+'\n')
  print('legacy',name,'PASS',flush=True)
 proof=dict(status='THIRTEEN_NORMAL_ROUTES_PROTECTED_PASS_ABI117_AND_SEVEN_LEGACY_FIXTURES_COMPLETE',ROM_SHA256=b['SHA256'],normal_routes=rows,
  normal_pairs=len(rows),getter_length_indices=117,legacy_display_cases=7,full_natural_battle_completion_claimed=False)
 (P/'qa/V292_REGRESSION_20261017_02.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
