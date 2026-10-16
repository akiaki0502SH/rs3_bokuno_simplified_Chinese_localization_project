"""Run finite display fixtures in Mesen; private test ROM gets no wait shim."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys
P=Path(__file__).resolve().parents[1]
D=P/'qa/reward_growth_v292_20261017_02'
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
CASES={**{f'weapon{i}':dict(entry=0xcdf7,finish=0xce3f,id=i)for i in range(11)},
       'hp':dict(entry=0xcd7a,finish=0xcda2),
       'tp':dict(entry=0xcdb7,finish=0xcde2,id=0),
       'sp':dict(entry=0xcdb7,finish=0xcde2,id=1),
       **{f'money{n}':dict(entry=0xcf11,finish=0xcf4f,amount=n)for n in [1,4,10,999,9999]},
       'money_cap':dict(entry=0xcf70,finish=0xcfc1,amount=4)}
def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',required=True);p.add_argument('--label',required=True)
 p.add_argument('--cases',default=','.join(CASES));a=p.parse_args()
 D.mkdir(exist_ok=True);b=(P/a.rom).read_bytes();assert b[0x7ff280:0x7ff291]==bytes(17)
 for name in a.cases.split(','):
  c=CASES[name];prefix=D/f'{a.label}_{name}'
  if prefix.with_suffix('.json').exists():
   old=json.loads(prefix.with_suffix('.json').read_text());assert old['source_ROM_SHA256']==sha(b);continue
  casefile=D/f'{name}.lua'
  casefile.write_text('return {'+','.join(f'{k}={v}'for k,v in c.items())+'}\n',encoding='utf8')
  diag=bytearray(b)
  wait=bytes.fromhex('22 a3 b8 fe a9 1e 85 16 22 7a c1 fe 5c')+c['finish'].to_bytes(2,'little')+b'\xc2'
  diag[0x7ff280:0x7ff280+len(wait)]=wait
  rom=D/f'{a.label}_{name}.smc';rom.write_bytes(diag)
  env=os.environ.copy();env.update(CN_V292_SEED=str(P/'qa/bmsg_controlled_native26405_20261008_02_native_ui_before_inject.mss'),
    CN_V292_PREFIX=str(prefix),CN_V292_CASE=str(casefile))
  proc=subprocess.run([str(P/'qa/mesen_isolated_runner/Mesen.exe'),'--testrunner',str(rom),
    str(P/'tools/mesen_v292_reward_growth_probe_v1.lua'),'--timeout=45000'],cwd=P,env=env,capture_output=True,timeout=55,
    creationflags=subprocess.CREATE_NO_WINDOW)
  prefix.with_suffix('.stdout.txt').write_bytes(proc.stdout+proc.stderr)
  proof=dict(case=name,source_ROM=a.rom,source_ROM_SHA256=sha(b),diagnostic_ROM=str(rom.relative_to(P)),
    diagnostic_SHA256=sha(diag),shim_only_in_diagnostic=True,exit=proc.returncode,**c)
  prefix.with_suffix('.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
  assert proc.returncode==0,(name,proc.returncode,proc.stderr[-2000:])
  print(a.label,name,'PASS',flush=True)
if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
