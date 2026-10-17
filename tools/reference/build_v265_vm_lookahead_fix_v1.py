# Build candidate v265 = v264-05 + VM lookahead classifier fix (non-payload, non-FA..FF banks use original JP classification).
import hashlib,sys
src_path,out_path=sys.argv[1],sys.argv[2]
b=open(src_path,'rb').read(); sha=lambda x:hashlib.sha256(x).hexdigest().upper()
assert sha(b)=='25738D63146123E878097849734FE1ECD2C6083CCDC8E563FBF2D2126BD14234',sha(b)
r=bytearray(b)
BASE_FILE=0x7FC000; BASE_CPU=0x3FC000
# payload ranges (bank, lo_page, hi_page) derived from 264 vs source diff: CN text arenas outside FA..FF
ranges=[(0x3E,0x80,0xFF),(0x3F,0x80,0x9C),(0x69,0x08,0xFF),(0x6D,0x34,0xFF),(0x6E,0x7C,0xFF),(0x6F,0x10,0xFF),(0x75,0xD6,0xFF),(0x76,0x55,0xFF),(0x77,0x00,0xFF),(0x79,0x1C,0xFF),(0x7E,0x00,0xFF),(0x7F,0x00,0xFF)]
table=b''.join(bytes(x) for x in ranges)+b'\xff'
TABLE_CPU=BASE_CPU+0x100; TABLE_FILE=BASE_FILE+0x100
def l24(a): return bytes([a&255,(a>>8)&255,(a>>16)&255])
code=bytearray()
def emit(h): code.extend(bytes.fromhex(h))
labels={};fix=[]
def here(): return BASE_CPU+len(code)
def br(op,label): code.extend(bytes([op,0])); fix.append((len(code)-1,label))
# NR entry
emit('08 c2 30 48 da e2 20')            # PHP REP#30 PHA PHX SEP#20
emit('af 7a 00 7e c9 fa')               # LDA $7E007A ; CMP #$FA
br(0xb0,'CN')                           # BCS CN
emit('a2 00 00')                        # LDX #0000
labels['loop']=len(code)
emit('bf'); code.extend(l24(TABLE_CPU))  # LDA table,X
emit('c9 ff'); br(0xf0,'ORIG')
emit('cf 7a 00 7e'); br(0xd0,'next')
emit('af 79 00 7e')
emit('df'); code.extend(l24(TABLE_CPU+1)); br(0x90,'next')
emit('df'); code.extend(l24(TABLE_CPU+2)); br(0xf0,'CN'); br(0x90,'CN')
labels['next']=len(code)
emit('e8 e8 e8'); br(0x80,'loop')
labels['CN']=len(code)
emit('c2 30 fa 68 28 5c 00 e1 59')       # REP#30 PLX PLA PLP JML $59E100 (current CN-aware classifier)
labels['ORIG']=len(code)
emit('c2 30 fa 68 28')                  # restore, then original JP classification
emit('08 c2 30 48 da e2 20 a9 00 8f f6 ef 7e c2 20 a3 03 29 ff 00 aa e2 20')
emit('c9 10'); br(0x90,'look'); emit('c9 17'); br(0x90,'opc'); emit('c9 19'); br(0xf0,'opc')
labels['look']=len(code)
emit('bf 00 e2 59'); br(0xf0,'opc')
emit('c2 30 fa 68 28 e2 20 18 6b')       # text: CLC RTL
labels['opc']=len(code)
emit('c2 30 fa 68 28 e2 20 38 6b')       # opcode: SEC RTL
for pos,lab in fix:
    off=labels[lab]-(pos+1); assert -128<=off<=127,(lab,off); code[pos]=off&255
assert len(code)<0x100
assert not any(r[BASE_FILE:BASE_FILE+0x200])
r[BASE_FILE:BASE_FILE+len(code)]=code; r[TABLE_FILE:TABLE_FILE+len(table)]=table
assert r[0x7f9f28:0x7f9f2c]==bytes.fromhex('22 00 e1 59')
r[0x7f9f29:0x7f9f2c]=l24(BASE_CPU)
for h in [0xffdc,0x40ffdc]: r[h:h+4]=bytes.fromhex('ffff0000')
c=sum(r)&65535
for h in [0xffdc,0x40ffdc]: r[h:h+4]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little')
assert not any(r[0x7ffe00:0x7ffff0])
changed=[i for i,(x,y) in enumerate(zip(b,r)) if x!=y]
allowed=set(range(BASE_FILE,BASE_FILE+0x200))|set(range(0x7f9f29,0x7f9f2c))|set(range(0xffdc,0xffe0))|set(range(0x40ffdc,0x40ffe0))
assert all(i in allowed for i in changed)
open(out_path,'wb').write(r)
print('SHA',sha(bytes(r)),'changed',len(changed),'code',len(code),'checksum %04X'%c)
print('code',bytes(code).hex(' '))
