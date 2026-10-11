
"""Migrate only the exact original default Katarina name in live WRAM."""
from pathlib import Path
import json,hashlib,sys
P=Path.cwd();rd=lambda f:json.loads((P/f).read_text(encoding='utf8'));sha=lambda z:hashlib.sha256(z).hexdigest().upper()
d=rd(sys.argv[3] if len(sys.argv)>3 else 'qa/V281_PROTOTYPE_FORMATIONS_BUILD_20261011_04.json');b=(P/d['ROM']).read_bytes();assert sha(b)==d['SHA256']
r=bytearray(b);sys.path.insert(0,str(P/'tools'));from build_font_renderer_hook import branch_code
prev=rd(sys.argv[4] if len(sys.argv)>4 else 'qa/V281_DISPLAY_BUILD_20261011_03.json')
nameptr=next(int(x['at'],16)-0x400000 for x in prev['writes']if x['why']=='default Katarina Chinese display string')
old=bytes.fromhex('87 91 A9 96 50 50 50 50');new=bytes.fromhex('11 1A 21 75 14 3B 12 44')
parts=['08 c2 20 48']
for i in range(4):
 parts+=['af '+(0x7ef300+i*2).to_bytes(3,'little').hex(' ')+' c9 '+old[i*2:i*2+2].hex(' '),(None,0xd0,'done')]
for i in range(4):parts+=['a9 '+new[i*2:i*2+2].hex(' ')+' 8f '+(0x7ef300+i*2).to_bytes(3,'little').hex(' ')]
parts+=[('label','done'),'68 28 a9 '+(nameptr&65535).to_bytes(2,'little').hex(' ')+' 85 75 6b']
thunk=branch_code(parts);at=int(d['arena_end'],16);assert not any(b[at:at+len(thunk)]);r[at:at+len(thunk)]=thunk
hp=int(d['new_display_helper'],16)+0x400000;n=prev['helper_bytes'];code=bytearray(b[hp:hp+n]);sig=b'\xa9'+(nameptr&65535).to_bytes(2,'little')+b'\x85\x75';assert code.count(sig)==1
call=b'\x22'+(at-0x400000).to_bytes(3,'little')+b'\xea';newcode=code.replace(sig,call);r[hp:hp+n]=newcode
allow=set(range(at,at+len(thunk)))|set(range(hp,hp+n))
for h in [0xffdc,0x40ffdc]:r[h:h+4]=bytes.fromhex('ff ff 00 00');allow.update(range(h,h+4))
c=sum(r)&65535
for h in [0xffdc,0x40ffdc]:r[h:h+4]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little')
assert sum(r)&65535==c and all(i in allow for i,(x,y)in enumerate(zip(b,r))if x!=y)
out=P/(sys.argv[1]if len(sys.argv)>1 else'roms/work/bokuno_cn_candidate_v10ba281_review_feedback_20261011_01.smc');pf=P/(sys.argv[2]if len(sys.argv)>2 else'qa/V281_DEFAULT_NAME_BUILD_20261011_01.json');assert not out.exists()and not pf.exists();out.write_bytes(r)
proof={'ROM':str(out.relative_to(P)),'SHA256':sha(r),'base_ROM':d['ROM'],'base_SHA256':sha(b),
 'status':'STATIC_PASS_RUNTIME_PENDING','writes':[{'at':f'{at:06X}','after_hex':thunk.hex(' ').upper()},{'at':f'{hp:06X}','after_hex':newcode.hex(' ').upper()}],
 'expected_old_default_name_hex':old.hex(' ').upper(),'new_default_name_hex':new.hex(' ').upper(),'WRAM_name_field':'7EF300..7EF307',
 'scope':'Only exact original default name is converted when rendered; player custom strings are retained. Original emulator files are never edited.',
 'reason':'Menu and event dialogue must share the same confirmed Chinese default name.',
 'no_actor_ID_attributes_inventory_flags_RNG_or_SRAM_writes':True,'name_only_RAM_write_authorized_by_translation_request':True,'arena_end':f'{at+len(thunk):06X}'}
pf.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:proof[k]for k in ['ROM','SHA256','arena_end']},ensure_ascii=False))

