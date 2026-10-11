"""Compile the four newly authorized independent spell-name records only."""
from pathlib import Path
import hashlib,json,sys
from dry_run_encoding_plan import encode
P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
CONFIRMED={'M0024':('黒猫','黑猫'),'M0080':('硝子の盾','玻璃之盾'),'M0104':('魔道板解読','魔道板解读'),'M0105':('魔道板解読','魔道板解读')}

def main():
 out=(P/sys.argv[1]).resolve();pf=(P/sys.argv[2]).resolve()
 assert out.is_relative_to(P)and pf.is_relative_to(P)and not out.exists()and not pf.exists()
 m=rd('text/translations/translation_sources_before_v286_20261011_01.json');assert m['build_revision']=='v285_center_and_yang01'
 b=(P/m['latest_test_ROM']['file']).read_bytes();assert sha(b)==m['latest_test_ROM']['SHA256']=='38BABFEF7CF71DFB14DD5836ECE9BD7E140795761A3C07D556A2370E71FE117A'
 r=bytearray(b);allowed=set();rows=[]
 mapping={k:bytes.fromhex(v)for k,v in rd(m['latest_font_mapping']).items()}
 source=rd(m['latest_techniques_and_spells']);new=rd('text/translations/techniques_spells_category_review_v286_20261011_01.json')
 new_by={x['id']:x for x in new['spells']}
 for x in source['spells']:
  at=int(x['name_offset'],16)
  if x['id']not in CONFIRMED:continue
  jp,zh=CONFIRMED[x['id']];nx=new_by[x['id']]
  assert nx['jp']==jp and nx['zh']==zh and not nx['source_glyphs_need_review']
  assert b[at:at+10]==bytes.fromhex(x['raw_jp_hex'])and at==0x5BA000+int(x['spell_ID'],16)*10
  z,miss,errors=encode(zh,mapping,battle=False);assert not miss and not errors and len(z)<=10
  payload=z+b'\x50'*(10-len(z));r[at:at+10]=payload;allowed.update(range(at,at+10))
  rows.append({'id':x['id'],'spell_ID':x['spell_ID'],'jp':jp,'zh':zh,'offset':f'{at:06X}','capacity_bytes':10,'encoded_bytes':len(z),'before_hex':b[at:at+10].hex(' ').upper(),'after_hex':payload.hex(' ').upper(),'font_mapping_unchanged':True})
 assert len(rows)==4
 for x in source['spells']:
  at=int(x['name_offset'],16)
  if x['id']not in CONFIRMED:assert r[at:at+10]==b[at:at+10]
 for idx in source['empty_spell_slots']:
  at=0x5BA000+int(idx,16)*10;assert r[at:at+10]==b[at:at+10]
 assert r[0x5BAA00:0x5FF000]==b[0x5BAA00:0x5FF000]
 assert r[0x780000:0x790000]==b[0x780000:0x790000]and r[0x7D0000:0x7E0000]==b[0x7D0000:0x7E0000]
 for at in [0xFFDC,0x40FFDC]:r[at:at+4]=bytes.fromhex('FF FF 00 00');allowed.update(range(at,at+4))
 checksum=sum(r)&65535
 for at in [0xFFDC,0x40FFDC]:r[at:at+4]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
 assert len(r)==0x800000 and sum(r)&65535==checksum
 diffs=[i for i,(a,c)in enumerate(zip(b,r))if a!=c];assert all(i in allowed for i in diffs)
 for x in rows:
  at=int(x['offset'],16);assert r[at:at+10]==bytes.fromhex(x['after_hex'])
 out.write_bytes(r)
 proof={'schema':'v286-four-confirmed-spell-names-build-v1','status':'STATIC_READBACK_PASS_RUNTIME_PENDING','ROM':out.relative_to(P).as_posix(),'SHA256':sha(r),'base_ROM':m['latest_test_ROM']['file'],'base_SHA256':sha(b),'rows':rows,'name_records_changed':4,'changed_bytes':len(diffs),'only_four_name_records_and_checksums_changed':True,'other232_spell_names_preserved':True,'empty20_name_slots_preserved':True,'all_effects_learning_rules_descriptions_native_code_and_fonts_preserved':True,'all_v284_v285_display_fixes_preserved':True,'formal_baseline_promoted':False}
 pf.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(proof,ensure_ascii=False))

if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
