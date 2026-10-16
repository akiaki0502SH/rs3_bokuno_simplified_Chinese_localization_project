"""Correct native result composition and the pre-existing UI07 alias mismatch."""
from pathlib import Path
import hashlib,json,sys
from build_font_renderer_hook import branch_code
P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
def main():
 frozen='text/translations/translation_sources_before_v292_20261017_02.json'
 m=rd(frozen if(P/frozen).exists()else'text/translations/translation_sources_current.json')
 assert m['build_revision']=='v291_layout_v3_pilot01'
 b=(P/m['latest_test_ROM']['file']).read_bytes()
 assert sha(b)=='A7D4CBF833D04AD698DA232FBE4007E5ADFE112814C2545C02C517A99C29CC7F'
 s=(P/'../roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
 r=bytearray(b);mask=bytearray(len(b));writes=[]
 mp={c:bytes.fromhex(z)for c,z in rd(m['latest_font_mapping']).items()}
 enc=lambda z:b''.join(mp[c]for c in z)
 def put(at,z,why,expected=None):
  if expected is None:assert b[at:at+len(z)]==s[at:at+len(z)]==bytes(len(z)),hex(at)
  else:assert b[at:at+len(z)]==expected,(hex(at),why)
  assert not any(mask[at:at+len(z)])
  r[at:at+len(z)]=z;mask[at:at+len(z)]=b'\1'*len(z)
  writes.append(dict(offset=f'{at:06X}',bytes=len(z),reason=why,before_hex=b[at:at+len(z)].hex(' ').upper(),after_hex=z.hex(' ').upper()))
 # The original length routine aliases UI07 to FD77FB (弓・銃).
 # Full-name wrappers correctly restore AA; resolve the alias BEFORE them.
 getter=branch_code(['a5 65 c9 07',(None,0xd0,'ordinary'),
  # Reuse the verified original getter clone to retain A high byte and C/V.
  '22 00 f5 3f a2 fb 77 86 aa a2 0e 00 5c 26 07 c2',
  ('label','ordinary'),'a5 65 c2 20 5c 0b 07 c2'])
 put(0x7ff610,getter,'resolve native bow/gun UI07 alias before bounded count/draw wrappers')
 put(0x20707,bytes.fromhex('5c 10 f6 3f'),'UI getter alias hook',bytes.fromhex('a5 65 c2 20'))
 # The new shorter labels retain their allocation; accurate lengths exclude
 # the two unused trailing bytes. Existing explicit lengths cover UI0F..72.
 for i,new in [(15,'技力'),(16,'术力')]:
  at=0x3d9a00+int.from_bytes(b[0x3d9800+2*i:0x3d9802+2*i],'little')
  data=enc(new);assert len(data)==3
  put(at,data,'standard TP/SP terminology '+new,b[at:at+len(data)])
  put(0x7f9fd0+2*i,len(data).to_bytes(2,'little'),'exact byte length '+new,(5).to_bytes(2,'little'))
 assert b[0x7f9f82:0x7f9f84]==bytes.fromhex('c9 31')
 put(0x7f9f83,b'\x0f','use authoritative UI byte lengths from UI0F onward',b'\x31')
 put(0x2cdb8,b'\x08','TP/SP frame width for two-character label',b'\x09')
 put(0x2cdd4,b'\x04','suffix follows two-character TP/SP label',b'\x06')
 # Preserve original number formatter and both reward branches. Only draw order
 # changes: prefix, original decimal digits, currency, optional overflow suffix.
 common=bytes.fromhex('a6 aa da a5 ac 48 a5 1a 48 a5 4b 48 a9 13 85 65 22 00 f5 3f 22 da aa fe 68 85 4b 68 85 1a 68 85 ac fa 86 aa a5 7e 18 69 06 85 7e 22 fa ab fe a5 1a 0a 18 65 7e 85 7e a5 4b 48 a2 00 f7 86 aa a9 3f 85 ac a9 06 85 4b a5 1e 29 ef 85 1e 22 da aa fe 68 85 4b 6b')
 normal=bytes.fromhex('22 90 f6 3f 5c 4f cf c2')
 suffix=enc('，但');assert len(suffix)==4
 cap=bytes.fromhex('22 90 f6 3f a5 7e 18 69 06 85 7e a5 4b 48 a2 06 f7 86 aa a9 04 85 4b 22 da aa fe 68 85 4b 5c ae cf c2')
 assert 0x7ff690+len(common)<=0x7ff700 and 0x7ff660+len(cap)<=0x7ff690
 put(0x7ff650,normal,'normal money draw then original cleanup')
 put(0x7ff660,cap,'overflow money draw then original second-row warning')
 put(0x7ff690,common,'shared money prefix/digits/currency display only')
 put(0x7ff700,enc('奥拉姆')+suffix,'currency and overflow display literals')
 put(0x2cf38,bytes.fromhex('5c 50 f6 3f'),'normal reward display hook',bytes.fromhex('22 fa ab fe'))
 put(0x2cf97,bytes.fromhex('5c 60 f6 3f'),'overflow reward display hook',bytes.fromhex('22 fa ab fe'))
 for at in [0xffdc,0x40ffdc]:
  put(at,bytes.fromhex('ff ff 00 00'),'checksum normalization',b[at:at+4])
 checksum=sum(r)&65535
 for at in [0xffdc,0x40ffdc]:r[at:at+4]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
 # Record the final checksum bytes for independent replay.
 for w in writes:
  at=int(w['offset'],16);w['after_hex']=r[at:at+w['bytes']].hex(' ').upper()
 assert sum(r)&65535==checksum and len(r)==0x800000
 assert all(mask[i]for i,(x,y)in enumerate(zip(b,r))if x!=y)
 for lo,hi in [(0x2c0000,0x2c8000),(0x608000,0x60c000),(0x780000,0x790000),(0x7d0000,0x7e0000),
   (0x3a0000,0x3d0000),(0x7ff300,0x7ff610),(0x7ff800,0x7ffe00)]:assert r[lo:hi]==b[lo:hi]
 assert r[0x7ffe00:0x7ffff0]==bytes(496) and r[0x7ff280:0x7ff291]==bytes(17)
 layout=rd(m['latest_layout_build'])
 for x in layout['rows']:
  at=int(x['new_payload_file'],16);n=64 if x['mode']=='fixed64'else len(bytes.fromhex(x['new_encoded_hex']))+4
  assert r[at:at+n]==b[at:at+n]
 out=P/'roms/work/bokuno_cn_candidate_v10bl292_reward_growth_20261017_02.smc'
 proof=P/'qa/V292_REWARD_GROWTH_BUILD_20261017_02.json'
 assert not out.exists()and not proof.exists();out.write_bytes(r)
 report=dict(schema='v292-reward-growth-v1',status='STATIC_PASS_RUNTIME_PENDING',ROM=out.relative_to(P).as_posix(),SHA256=sha(r),
  base_ROM=m['latest_test_ROM']['file'],base_SHA256=sha(b),writes=writes,changed_bytes=sum(a!=z for a,z in zip(b,r)),
  original_effective_bow_label='弓・銃',current_bow_label='弓・铳',bow_and_gun_share_existing_category=True,
  raw_UI07_table_label='弓',TP_label='技力',SP_label='术力',normal_money='获得了{AMOUNT}奥拉姆',overflow_money='获得了{AMOUNT}奥拉姆，但／却装不下',
  gameplay_progression_unchanged=True,v291_layout_records_preserved=311,v289_display_modules_preserved=True,font_bytes_unchanged=True,
  source_events_unchanged=True,diagnostic_shim_absent=True,reserved496_preserved=True,formal_baseline_promoted=False)
 proof.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:report[k]for k in ['ROM','SHA256','changed_bytes']},ensure_ascii=False))
if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
