"""Apply one approved battle clause with identical payload length and controls."""
from pathlib import Path
import hashlib,json,re,sys
from dry_run_encoding_plan import encode
P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
BEFORE='埃罗尔用光之{NEWLINE}钻石封印了吾的{NEWLINE}记忆与黑暗之力。'
AFTER='吾的记忆与{NEWLINE}黑暗之力，一直被{NEWLINE}光之钻石封印着。'

def main():
 out=(P/sys.argv[1]).resolve();pf=(P/sys.argv[2]).resolve();assert out.is_relative_to(P)and pf.is_relative_to(P)and not out.exists()and not pf.exists()
 m=rd('text/translations/translation_sources_before_v287_20261011_01.json');assert m['build_revision']=='v286_four_spell_names01'
 basefile=m['latest_test_ROM']['file'];b=(P/basefile).read_bytes();assert sha(b)=='A02B904CA3E6418A3C8E8B53BBC91933D42CF1D84791B3B661467C2D5AA094BF'
 overlay=rd('text/translations/sheraha_b0028_user_confirmed_v287_20261011_01.json')
 mp={k:bytes.fromhex(v)for k,v in rd(m['latest_font_mapping']).items()}
 def enc(t):
  z,miss,errors=encode(t,mp,battle=True);assert not miss and not errors,(t,miss,errors);return z
 old=enc(BEFORE);new=enc(AFTER);assert len(old)==len(new)==41
 global_index=78;pointer_site=0x3D9800+global_index*2;length_site=0x7F9FD0+global_index*2
 at=0x3D9A00+int.from_bytes(b[pointer_site:pointer_site+2],'little');length=int.from_bytes(b[length_site:length_site+2],'little');assert at==0x3D9F87 and length==259
 payload=b[at:at+length];assert payload.count(old)==1;local=payload.index(old);assert local==33
 updated=payload[:local]+new+payload[local+len(old):];assert len(updated)==259 and enc(overlay['translation_zh_cn'])==updated
 def tokens(z):
  result=[];i=0
  while i<len(z):
   lead=z[i]
   if lead<0x24:i+=2
   elif lead in [0x25,0x2A]:result.append(z[i:i+2].hex(' ').upper());i+=2
   else:
    if lead in [0x24,0x28,0x29]:result.append(f'{lead:02X}')
    i+=1
  assert i==len(z);return result
 assert tokens(payload)==tokens(updated)
 def count(z):
  i=n=0
  while i<len(z):i+=2 if z[i]<0x24 or z[i]in[0x25,0x2A]else 1;n+=1
  assert i==len(z);return n
 assert count(payload)==count(updated)
 r=bytearray(b);site=at+local;r[site:site+41]=new;allowed=set(range(site,site+41))
 assert r[pointer_site:pointer_site+2]==b[pointer_site:pointer_site+2]and r[length_site:length_site+2]==b[length_site:length_site+2]
 assert r[0x3E0000:0x400000]==b[0x3E0000:0x400000]and r[0x5BA000:0x5BBA00]==b[0x5BA000:0x5BBA00]
 assert r[0x780000:0x790000]==b[0x780000:0x790000]and r[0x7D0000:0x800000]==b[0x7D0000:0x800000]
 for h in [0xFFDC,0x40FFDC]:r[h:h+4]=bytes.fromhex('FF FF 00 00');allowed.update(range(h,h+4))
 checksum=sum(r)&65535
 for h in [0xFFDC,0x40FFDC]:r[h:h+4]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
 assert len(r)==0x800000 and sum(r)&65535==checksum
 differences=[i for i,(a,c)in enumerate(zip(b,r))if a!=c];assert all(i in allowed for i in differences)
 assert r[at:at+length]==updated
 out.write_bytes(r)
 report={'schema':'v287-sheraha-b0028-build-v1','status':'STATIC_READBACK_PASS_RUNTIME_PENDING','ROM':out.relative_to(P).as_posix(),'SHA256':sha(r),'base_ROM':basefile,'base_SHA256':sha(b),'record':'B0028','event_index':'1C','global_index':global_index,'message_offset':f'{at:06X}','message_CPU':f'{at+0xC00000:06X}','message_bytes':length,'clause_offset':f'{site:06X}','before':BEFORE,'after':AFTER,'before_hex':old.hex(' ').upper(),'after_hex':new.hex(' ').upper(),'clause_bytes':41,'full_payload_hex':updated.hex(' ').upper(),'draw_iterations':count(updated),'line_glyphs':[len(x)for x in AFTER.split('{NEWLINE}')],'native_controls':tokens(updated),'pointer_and_length_unchanged':True,'all_other_text_code_fonts_effects_and_prior_fixes_preserved':True,'changed_bytes':len(differences),'formal_baseline_promoted':False}
 pf.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:report[k]for k in ['ROM','SHA256','message_bytes','clause_bytes','draw_iterations','line_glyphs','changed_bytes']},ensure_ascii=False))

if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
