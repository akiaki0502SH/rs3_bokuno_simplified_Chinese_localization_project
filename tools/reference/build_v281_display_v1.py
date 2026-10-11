
"""Display-only compatibility for saved original names and formation labels."""
from pathlib import Path
import json,sys,hashlib
P=Path.cwd().resolve();assert P==Path('G:/CodexProjects/Bokuno中文化工程/bokuno_cn')
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'));sha=lambda b:hashlib.sha256(b).hexdigest().upper()
stage=rd(sys.argv[3] if len(sys.argv)>3 else 'qa/V281_SOURCE_BUILD_20261011_01.json');b=(P/stage['ROM']).read_bytes();assert sha(b)==stage['SHA256']
source=(P/'../roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes();r=bytearray(b);writes=[];allowed=set()
arena=int(stage['new_shadow_arena_end'],16)
def put(at,z,why):
 r[at:at+len(z)]=z;allowed.update(range(at,at+len(z)));writes.append({'at':f'{at:06X}','why':why,'bytes':len(z),'before_SHA256':sha(b[at:at+len(z)]),'after_hex':z.hex(' ').upper()})
def alloc(z,why):
 global arena
 at=arena;arena+=len(z);assert arena<0x7ffe00 and not any(b[at:arena]);put(at,z,why);return at-0x400000
def asm(parts):
 out=bytearray();labels={};fix=[];inverse={0xf0:0xd0,0xd0:0xf0,0x90:0xb0,0xb0:0x90}
 for x in parts:
  if isinstance(x,str):out.extend(bytes.fromhex(x))
  elif x[0]=='label':labels[x[1]]=len(out)
  elif x[0]=='jmp':out.append(0x82);fix.append((len(out),x[1]));out.extend(b'\0\0')
  elif x[0]=='br':out.extend(bytes([inverse[x[1]],3,0x82]));fix.append((len(out),x[2]));out.extend(b'\0\0')
 for at,label in fix:
  delta=labels[label]-(at+2);assert -32768<=delta<=32767;out[at:at+2]=delta.to_bytes(2,'little',signed=True)
 return bytes(out)
def w(z):return z.to_bytes(2,'little').hex(' ')
name=bytes.fromhex('11 1A 21 75 14 3B 12 44');assert b[0x3d14b8:0x3d14c0]==name
nameptr=alloc(name,'default Katarina Chinese display string')
forms=rd('text/translations/formation_display_names_current_20261011_02.json')['translations'];rows=[];seen=set()
for x in forms:
 at=int(x['source_offset'],16);raw=source[at:at+10]
 if raw in seen:continue
 seen.add(raw);rows.append(raw+(at&65535).to_bytes(2,'little')+bytes([0xfd,10])+b'\0\0')
table=alloc(b''.join(rows),'original formation name to Chinese fixed-table display aliases')
old=b[0x7fbf00:0x7fbf80];draw_at=old.find(bytes.fromhex('E2 20 A3 0C 48 28'));tail_end=old.find(bytes.fromhex('68 28 6B'),draw_at)+3
assert draw_at>0 and tail_end>draw_at
prefix=old[:24];fdstart=24
assert prefix.hex()=='08c23048da5aa57548e220a57748c220a50629ff00488514'
fdblock=old[fdstart:draw_at];tail=old[draw_at:tail_end]
parts=[prefix.hex(' '),'e2 20 a5 77 c9 7e',('br',0xf0,'native_name'),'c9 7f',('br',0xf0,'native_name'),'c9 5e',('br',0xf0,'native_name'),'c9 5f',('br',0xf0,'native_name'),('jmp','FD'),
 ('label','native_name'),'c2 30 a0 00 00']
jp=bytes.fromhex('87 91 A9 96 50 50 50 50')
for i in range(4):
 parts+=['b7 75 c9 '+jp[i*2:i*2+2].hex(' '),('br',0xd0,'formation'),'c8 c8']
parts+=['a9 '+w(nameptr&65535)+' 85 75 a9 08 00 85 14 e2 20 a9 3f 85 77',('jmp','draw'),
 ('label','formation'),'c2 30 a2 00 00',
 ('label','next'),'a0 00 00',
 ('label','compare'),'b7 75 df '+table.to_bytes(3,'little').hex(' '),('br',0xd0,'mismatch'),
 'c8 c8 e8 e8 c0 0a 00',('br',0x90,'compare'),
 'bf '+table.to_bytes(3,'little').hex(' ')+' 85 75 e2 20 bf '+(table+2).to_bytes(3,'little').hex(' ')+' 85 77 bf '+(table+3).to_bytes(3,'little').hex(' ')+' 85 14',('jmp','draw'),
 ('label','mismatch'),'8a 29 f0 ff 18 69 10 00 aa e0 '+w(len(rows)*16),('br',0x90,'next'),
 ('label','FD'),fdblock.hex(' '),
 ('label','draw'),tail.hex(' ')]
helper=asm(parts);hp=alloc(helper,'fixed display wrapper preserves source pointer, registers, flags and custom names')
# FD block has only local relative branches ending at draw; its distance stays unchanged.
assert b[0x5de2d:0x5de31]==bytes.fromhex('22 00 BF 3F')
put(0x5de2d,b'\x22'+hp.to_bytes(3,'little'),'existing fixed renderer dispatcher target')
for lo,hi in [(0x3e0f00,0x3e1d00),(0x5baa00,0x5bba00),(0x5b34a0,0x5b37a0),(0x5b79b0,0x5b79e0)]:assert r[lo:hi]==b[lo:hi]
assert r[0x7ffe00:0x7ffff0]==bytes(496)
for h in [0xffdc,0x40ffdc]:r[h:h+4]=bytes.fromhex('ff ff 00 00');allowed.update(range(h,h+4))
c=sum(r)&65535
for h in [0xffdc,0x40ffdc]:r[h:h+4]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little')
assert sum(r)&65535==c and all(i in allowed for i,(x,y)in enumerate(zip(b,r))if x!=y)
out=P/(sys.argv[1]if len(sys.argv)>1 else'roms/work/bokuno_cn_diag_v10ba281_display_20261011_01.smc');proof=P/(sys.argv[2]if len(sys.argv)>2 else'qa/V281_DISPLAY_BUILD_20261011_01.json');assert not out.exists()and not proof.exists();out.write_bytes(r)
d={'status':'STATIC_PASS_RUNTIME_PENDING','ROM':str(out.relative_to(P)),'SHA256':sha(r),'base_SHA256':sha(b),'writes':writes,'helper_CPU':f'{hp:06X}','helper_bytes':len(helper),'default_name_guard_hex':jp.hex(' ').upper(),'formation_aliases':len(rows),'arena_end':f'{arena:06X}','no_RAM_SRAM_name_or_world_writes':True,'old14_fixed_fullname_exceptions_inherited':True}
proof.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:d[k]for k in ['ROM','SHA256','helper_bytes','formation_aliases','arena_end']},ensure_ascii=False))

