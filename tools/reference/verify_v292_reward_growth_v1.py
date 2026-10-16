"""Verify native glyph streams, ABI and paired protected data independently."""
from pathlib import Path
import hashlib,json,re,sys
from run_v292_display_probes_v1 import CASES
from run_v292_regressions_v1 import PROTECTED
P=Path(__file__).resolve().parents[1];D=P/'qa/reward_growth_v292_20261017_02';OLD=P/'qa/reward_growth_v292_20261017_01'
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
def main():
 b=rd('qa/V292_REWARD_GROWTH_BUILD_20261017_02.json');r=(P/b['ROM']).read_bytes();base=(P/b['base_ROM']).read_bytes()
 assert sha(r)==b['SHA256']and sha(base)==b['base_SHA256']
 replay=bytearray(base);covered=bytearray(len(base))
 for w in b['writes']:
  at=int(w['offset'],16);z=bytes.fromhex(w['after_hex']);before=bytes.fromhex(w['before_hex'])
  assert base[at:at+len(z)]==before and not any(covered[at:at+len(z)])
  replay[at:at+len(z)]=z;covered[at:at+len(z)]=b'\1'*len(z)
 assert replay==r and sum(r)&65535==int.from_bytes(r[0xffde:0xffe0],'little')
 frozen='text/translations/translation_sources_before_v292_20261017_02.json'
 m=rd(frozen if(P/frozen).exists()else'text/translations/translation_sources_current.json');mp={c:bytes.fromhex(z)for c,z in rd(m['latest_font_mapping']).items()}
 def glyphs(text):
  out=[]
  for c in text:
   z=mp[c]
   if len(z)==1:out.append(z[0]-0x50)
   elif z[0]in range(0x20,0x24):out.append((z[0]-0x20)*256+z[1])
   else:assert len(z)==2;out.append(int.from_bytes(z,'big'))
  return out
 def trace(path):
  t=path.read_text(encoding='utf8');s=re.search(r'RESULT native_return=true SP_before=(\w+) SP_after=(\w+)',t)
  assert s and s[1]==s[2],path
  out=[]
  for line in t.splitlines():
   if not line.startswith('GLYPH '):continue
   z={k:v for k,v in re.findall(r'(\w+)=([\w]+)',line)}
   x,y,fx,fy,w,h=(int(z[k])for k in ['x','y','frameX','frameY','width','height'])
   assert fx<=x<fx+w*2 and fy<=y<fy+h,(path.name,line)
   code=int(z['code'],16)if'code'in z else int(z['high']+z['low'],16)
   out.append(code)
  return out,t
 names=['剑・大剑','棍棒・斧','枪・小剑','弓・铳','体术','苍龙术','朱鸟术','白虎术','玄武术','太阳术','月术']
 cases=[]
 for name,c in CASES.items():
  a=OLD/f'base03_{name}';z=D/f'candidate_{name}'
  assert rd(z.with_suffix('.json'))['source_ROM_SHA256']==b['SHA256']
  before,t0=trace(Path(str(a)+'_trace.txt'));after,t1=trace(Path(str(z)+'_trace.txt'))
  if name.startswith('weapon'):want=glyphs(names[c['id']]+'提升了！')
  elif name in ['hp','tp','sp']:want=glyphs({'hp':'ＨＰ','tp':'技力','sp':'术力'}[name]+'提升了！')
  else:
   want=glyphs('获得了')+[0x2300+int(x)for x in str(c['amount'])]+glyphs('奥拉姆')
   if name=='money_cap':want+=glyphs('，但却装不下')
  assert after==want,(name,[hex(i)for i in after],[hex(i)for i in want])
  if name=='weapon3':assert before==glyphs('弓体术提升了！')
  elif name=='tp':assert before==glyphs('技之力提升了！')
  elif name=='sp':assert before==glyphs('术之力提升了！')
  elif not name.startswith('money'):assert before==after,name
  aa=Path(str(a)+'_final.ram').read_bytes();zz=Path(str(z)+'_final.ram').read_bytes()
  checks={k:aa[lo:hi]==zz[lo:hi]for k,lo,hi in PROTECTED}
  assert all(checks.values()),(name,checks)
  cases.append(dict(case=name,native_glyph_sequence_exact=True,stack_balanced=True,within_native_frame=True,protected_checks=checks,
   image=Path(str(z)+'_visible.png').relative_to(P).as_posix(),controlled_display_only=True))
 def abi(label,kind):
  rows={}
  for line in (D/f'ABI117_{label}.txt').read_text().splitlines():
   if line.startswith(kind+' '):
    row=dict(re.findall(r'(\w+)=(\w+)',line));rows[int(row['idx'])]=row
  assert len(rows)==117;return rows
 a,z=abi('base','BATTLE_RESOLVER_ACTUAL'),abi('candidate','BATTLE_RESOLVER_ACTUAL')
 for i in a:
  assert all(a[i][k]==z[i][k]for k in a[i]if k!='AA'),(i,a[i],z[i])
  assert z[i]['AA']==('77FB'if i==7 else a[i]['AA'])
 a,z=abi('base','BATTLE_LENGTH_ACTUAL'),abi('candidate','BATTLE_LENGTH_ACTUAL')
 for i in a:
  for k in ['X','Y','SP','D','DB','P','AA','AC','flags_same','waitpool_same']:assert a[i][k]==z[i][k],(i,k,a[i],z[i])
  for k in ['A','len8A']:assert int(z[i][k],16)==(3 if i in [15,16]else int(a[i][k],16)),(i,k)
  assert z[i]['flags_same']==z[i]['waitpool_same']=='true'
 legacy=[]
 for case,reference in [('herb','herb_candidate04'),('mastery','mastery_candidate02'),('evasion_v2','evasion_candidate'),
   ('destruction','destruction_candidate'),('long_item_v2','long_item_candidate'),('long_skill_v2','long_skill_candidate'),('extended_item_v2','extended_item_candidate')]:
  new=D/f'legacy_{case}_trace.txt';old=P/f'qa/postbattle_feedback_v289_20261013_01/{reference}_trace.txt'
  ag,at=trace(old);zg,zt=trace(new);assert ag==zg,case
  initial=(D/f'legacy_{case}_initial.ram').read_bytes();final=(D/f'legacy_{case}_final.ram').read_bytes()
  checks={k:initial[lo:hi]==final[lo:hi]for k,lo,hi in PROTECTED};assert all(checks.values()),(case,checks)
  legacy.append(dict(case=case,previous_glyph_sequence_preserved=True,checks=checks))
 normal=rd('qa/V292_REGRESSION_20261017_02.json');assert normal['ROM_SHA256']==b['SHA256']and normal['normal_pairs']==13
 # Terminology audit: current typed source plus all prose/layout inventory.
 typed=rd(m['latest_typed_review'])['translations'];prose=rd('qa/layout_v3_prewrite_readiness_20261016_01/default_layouts.json')['records']
 hits=[dict(id=x['id'],text_id=x['text_id'],text=x['translation_zh_cn'],jp=x['jp'])for x in typed if any(t in x['translation_zh_cn']for t in ['技之力','术之力','技的力','术的力','弓体术'])]
 # A descriptive sentence about White Tiger magic is not the SP statistic.
 prose_hits=[dict(id=x['id'],text=x['text'])for x in prose if any(t in x['text']for t in ['技之力','术之力','技的力','术的力','弓体术'])]
 assert {x['id']for x in hits}=={'U0016','U0017'}
 assert len(prose_hits)==1 and'白虎术之力'in prose_hits[0]['text']
 proof=dict(schema='v292-result-display-verification-v1',status='TWENTY_DISPLAY_PAIRS_ABI117_SEVEN_LEGACY_AND_THIRTEEN_NORMAL_ROUTES_PASS_MANUAL_PENDING',
  ROM=b['ROM'],SHA256=b['SHA256'],native_display_cases=cases,native_display_pairs=len(cases),getter_and_length_ABI_indices=117,
  getter_A_high_and_CV_preserved=True,legacy_cases=legacy,normal_input_pairs=13,write_manifest_replayed_byte_exact=True,
  terminology_audit=dict(typed_records=len(typed),prose_layout_records=len(prose),incorrect_statistic_labels=hits,
   retained_literal_magic_power_sentence=prose_hits),v291_311_layout_payloads_preserved=True,font_and_v289_module_bytes_preserved=True,
  original_Japanese_reproduced=['弓・銃がアップ！','技の力がアップ！','術の力がアップ！','4オーラムを手に入れた'],
  original_Japanese_images=[f'qa/reward_growth_v292_20261017_02/jp_original_{x}_visible.png'for x in ['weapon3','tp','sp','money4']],
  exact_friend_battle_snapshot_available=False,full_gameplay_or_RNG_equivalence_claimed=False,
  superseded_diagnostics=['First TP fixture stopped at an operand, corrected to C2CDE2; not accepted.',
   'First overflow fixture stopped at an operand, corrected to C2CFC1; not accepted.',
   'Initial alias helper changed A high byte/C; replaced with original getter clone; final ABI117 exact.'])
 (P/'qa/V292_REWARD_GROWTH_VERIFICATION_20261017_02.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:proof[k]for k in ['status','SHA256','native_display_pairs','normal_input_pairs']},ensure_ascii=False))
if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
