"""Create/verify translation patches or apply v0.1 through an external Flips."""
from pathlib import Path
import argparse,hashlib,json,subprocess
BASE='4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0'
TARGET='D3F4B6300D811DC9B707CB85286573E43C2EB93DE729DA990AE5AD09ACE20E0E'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def run(flips,args):
 r=subprocess.run([str(flips)]+[str(x)for x in args],capture_output=True)
 if r.returncode:raise SystemExit(r.stderr.decode('utf8','replace')or r.stdout.decode('utf8','replace')or f'Flips failed: {r.returncode}')
def main():
 parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
 apply=sub.add_parser('apply');apply.add_argument('--flips',required=True);apply.add_argument('--patch',required=True);apply.add_argument('--input',required=True);apply.add_argument('--output',required=True)
 create=sub.add_parser('create');create.add_argument('--flips',required=True);create.add_argument('--base',required=True);create.add_argument('--target',required=True);create.add_argument('--output-dir',required=True)
 args=parser.parse_args()
 if args.command=='apply':
  if sha(args.input)!=BASE:raise SystemExit('Input must be the exact headerless Japanese Bokuno Proto1.123. Run verify_rom.py first.')
  if Path(args.output).exists():raise SystemExit('Output already exists; choose a new name.')
  run(args.flips,['--apply',args.patch,args.input,args.output])
  if sha(args.output)!=TARGET:raise SystemExit('Output SHA256 does not match the v0.1 target; retain the input and inspect this output.')
  print('PASS: output matches simplified Chinese v0.1')
 else:
  if sha(args.base)!=BASE or sha(args.target)!=TARGET:raise SystemExit('The base or target does not match v0.1.')
  dest=Path(args.output_dir).resolve()
  if dest.exists():raise SystemExit('Output directory already exists; choose a new directory.')
  dest.mkdir(parents=True);result=[]
  for fmt in ['ips','bps']:
   patch=dest/f'bokuno_cn_v0.1_Proto1.123.{fmt}';check=dest/f'private_verification_{fmt}.sfc'
   run(args.flips,['--create','--'+fmt,args.base,args.target,patch]);run(args.flips,['--apply',patch,args.base,check])
   if sha(check)!=TARGET:raise SystemExit('Roundtrip failed; do not distribute these outputs.')
   # Delete only the exact generated verification file after a checked roundtrip.
   assert check.resolve().parent==dest;check.unlink()
   result.append({'file':patch.name,'bytes':patch.stat().st_size,'SHA256':sha(patch)})
  (dest/'SHA256SUMS').write_text('\n'.join(x['SHA256']+'  '+x['file']for x in result)+'\n',encoding='utf8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
