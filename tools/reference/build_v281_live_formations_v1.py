
"""Translate the live prototype formation text blocks; preserve all attributes."""
from pathlib import Path
import json,hashlib,sys,copy
P=Path.cwd();rd=lambda f:json.loads((P/f).read_text(encoding='utf8'));sha=lambda z:hashlib.sha256(z).hexdigest().upper()
d=rd(sys.argv[3] if len(sys.argv)>3 else 'qa/V281_DISPLAY_BUILD_20261011_03.json');b=(P/d['ROM']).read_bytes();assert sha(b)==d['SHA256'];r=bytearray(b)
s=(P/'../roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
sys.path.insert(0,str(P/'tools'));from scan_rom_inventory import decode_bytes
from dry_run_encoding_plan import encode
m={k:bytes.fromhex(v)for k,v in rd('qa/V281_CURRENT_SINGLE_GLYPH_MAPPING_20261011_02.json').items()}
names={x['source']:x['translation_zh_cn']for x in rd('text/translations/formations_batch_001.json')['source_translations']}
# Current approved review takes precedence over older floating source batches.
names.update({x['source_jp']:x['translation_zh_cn']for x in rd('text/translations/formation_display_names_current_20261011_02.json')['translations']})
names.update({'アタックモ一ド':'进攻模式','ディフェンスモ一ド':'防御模式','トリックモ一ド':'诡计模式','ノ一マルモ一ド':'普通模式',
 'インペリアルクロス':'帝国十字阵','インペリアルアロ一':'帝国箭阵','フリ一ファイト{EXT18:A6}１':'自由战斗１','デザ一トフォックス':'沙漠狐阵',
 'ホ一リ一ウォ一ル':'圣墙阵','教授の陣':'教授阵','ラピッドストリ一ム':'急流阵','不動陣':'不动阵','ショックアブソ一バ':'冲击吸收阵','マジカルシャワ一':'法术雨阵','五爪四角の陣':'五爪四角阵'})
descs={'みんなで好き勝手に戦う陣形':'所有人各自随意战斗的阵型',
'前列の攻撃力がアップする陣形':'提高前列攻击力的阵型',
'全員が素早く行動できる陣形':'让全员快速行动的阵型',
'中心メンバ一をオトリにする陣形':'以中央成员为诱饵的阵型',
'強い術結界で全員を守る陣形':'以强力法术结界保护全员的阵型',
'後列の術攻撃力をアップさせる陣形':'提高后列法术攻击力的阵型',
'先頭から順に行動していく連続攻撃に向いた陣形':'从领头者起依次行动，适合连续攻击',
'コンビ攻撃に向いた陣形':'适合组合攻击的阵型',
'防御にすぐれた陣形':'防御出色的阵型',
'メンバ一全員の射撃能力を高める陣形':'提高全员射击能力的阵型',
'前列１人が盾となる戦いやすい陣形':'由前列一人充当盾牌的易战阵型',
'攻守にすぐれたバランスの良い陣形':'攻守兼备、平衡良好的阵型',
'中心メンバ一の術を全員で増幅する陣形':'由全员增幅中央成员的法术',
'攻撃にすぐれたスタイル':'擅长进攻的模式',
'防御にすぐれたスタイル':'擅长防御的模式',
'素早く行動して敵を惑わすスタイル':'迅速行动，迷惑敌人的模式',
'攻撃にすぐれた三角陣形':'擅长攻击的三角阵型',
'防御にすぐれた三角陣形':'擅长防御的三角阵型',
'攻める者と守る者を分けた陣形':'让攻击者与防守者分开的阵型',
'これといった効果のないスタイル':'没有特殊效果的模式',
'先頭が攻撃を引き付け最後尾を守る陣形':'领头者吸引攻击，保护最后方的阵型',
'敵の攻撃のほとんどを先頭が受け止める陣形':'由领头者承受大部分敌人攻击的阵型',
'前列が後列を隠す陣形':'前列掩护后列的阵型',
'前列が後列を守る陣形':'前列保护后列的阵型',
'戦闘ごとに位置を計算する教授にしかできない究極の陣形':'每战由教授计算站位的终极阵型',
'敵より早く行動することに特化した陣形':'专为抢在敌人之前行动的阵型',
'敵の攻撃を耐えた後反撃する陣形':'承受敌人攻击后反击的阵型',
'敵の物理攻撃から全員を守る陣形':'保护全员免受敌人物理攻击的阵型',
'精霊力の加護を受けて戦う陣形':'受精灵力加护进行战斗的阵型',
'全員の攻撃力と素早さが上がる陣形':'提高全员攻击力与速度的阵型'}
def enc(t):
 z,miss,err=encode(t,m,battle=False);assert not miss and not err,(t,miss,err);return z
def wrap(t):
 if len(t)<=14:return[t]if t else[]
 out=[]
 while len(t)>14:
  i=t.rfind('，',0,14)+1;i=i if i>=6 else 14;out.append(t[:i]);t=t[i:]
 return out+[t]
allowed=set();writes=[]
def put(at,z,why):
 assert len(b)==len(r);r[at:at+len(z)]=z;allowed.update(range(at,at+len(z)));writes.append({'at':f'{at:06X}','before_SHA256':sha(b[at:at+len(z)]),'after_hex':z.hex(' ').upper(),'why':why})
rows=[]
for idx in range(55):
 base=0x5ea000+idx*128;at=base+71;raw=s[at:at+46];jp=decode_bytes(raw,native46_glyphs=True).rstrip()
 jname,_,jdesc=jp.partition(' ');zh=names[jname];dc=descs[jdesc.replace(' ','')] if jdesc.strip() else ''
 lines=wrap(dc);payload=enc(zh)+b'\x50'+b'\x50'.join(enc(x)for x in lines)
 assert len(payload)<=46,(idx,zh,dc,len(payload));assert len(enc(zh))<=10
 put(at,payload+b'\x50'*(46-len(payload)),'prototype formation name and native wrapped description')
 assert r[base:at]==b[base:at] and r[at+46:base+128]==b[at+46:base+128]
 rows.append({'id':f'PF{idx:03d}','prototype_index':idx,'name_description_offset':f'{at:06X}',
 'text_capacity_bytes':46,'record_bytes':128,'source_jp_name':jname,'source_jp_description':jdesc,
 'translation_zh_cn':zh,'description_zh_cn':dc,'description_display_lines':lines,
 'name_raw_original_hex':raw.split(b'\x50')[0].hex(' ').upper(),'name_encoded_hex':enc(zh).hex(' ').upper(),
 'payload_hex':bytes(r[at:at+46]).hex(' ').upper(),'all_position_and_attribute_bytes_preserved':True})
# Add newly discovered original default names to the display-only compatibility table.
old_table=next(int(x['at'],16) for x in d['writes']if x['why']=='original formation name to Chinese fixed-table display aliases')
table=bytearray(b[old_table:old_table+d['formation_aliases']*16]);keys={bytes(table[i:i+10])for i in range(0,len(table),16)}
arena=int(d['arena_end'],16)
def alloc(z,why):
 global arena
 at=arena;arena+=len(z);assert arena<0x7ffe00 and not any(b[at:arena]);put(at,z,why);return at-0x400000
for x in rows:
 raw=bytes.fromhex(x['name_raw_original_hex']);key=(raw+b'\x50'*10)[:10]
 if key in keys:continue
 keys.add(key);z=bytes.fromhex(x['name_encoded_hex']);ptr=alloc(z,'extra prototype formation default display name')
 table+=key+(ptr&65535).to_bytes(2,'little')+bytes([ptr>>16,len(z)])+b'\0\0'
newtable=alloc(table,'expanded default formation alias table');newcount=len(table)//16
hp=int(d['helper_CPU'],16);oldhelper=b[hp+0x400000:hp+0x400000+d['helper_bytes']];helper=bytearray(oldhelper)
oldCPU=old_table-0x400000
for opcode,delta in [(0xdf,0),(0xbf,0),(0xbf,2),(0xbf,3)]:
 pat=bytes([opcode])+(oldCPU+delta).to_bytes(3,'little');assert helper.count(pat)==1;helper=helper.replace(pat,bytes([opcode])+(newtable+delta).to_bytes(3,'little'))
pat=b'\xe0'+(d['formation_aliases']*16).to_bytes(2,'little');assert helper.count(pat)==1
helper=helper.replace(pat,b'\xe0'+(newcount*16).to_bytes(2,'little'));newhelper=alloc(helper,'expanded display-only aliases retain original wrapper ABI')
put(0x5de2d,b'\x22'+newhelper.to_bytes(3,'little'),'fixed display wrapper with extra prototype aliases')
# Formation page caption has its own short native label.
jp=bytes.fromhex('21 76 21 AC');hits=[];i=b.find(jp,0x3dfcee,0x3dfd00)
while i>=0:hits.append(i);i=b.find(jp,i+1,0x3dfd00)
assert len(hits)==1;put(hits[0],enc('阵型'),'formation page short caption')
for idx in range(55,64):
 lo=0x5ea000+idx*128;assert r[lo:lo+128]==b[lo:lo+128]
for h in [0xffdc,0x40ffdc]:r[h:h+4]=bytes.fromhex('ff ff 00 00');allowed.update(range(h,h+4))
c=sum(r)&65535
for h in [0xffdc,0x40ffdc]:r[h:h+4]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little')
assert sum(r)&65535==c and all(i in allowed for i,(x,y)in enumerate(zip(b,r))if x!=y)
out=P/(sys.argv[1] if len(sys.argv)>1 else 'roms/work/bokuno_cn_diag_v10ba281_formations_20261011_04.smc');pf=P/(sys.argv[2] if len(sys.argv)>2 else 'qa/V281_PROTOTYPE_FORMATIONS_BUILD_20261011_04.json');assert not out.exists()and not pf.exists();out.write_bytes(r)
artifact={'schema':'prototype-live-formation-translations-v1','source_revision':'20261011_03','status':'COMPILED_RUNTIME_VALIDATION_PENDING',
 'base_ROM_SHA256':sha(b),'translations':rows,'name_description_capacity_bytes':46,
 'source_metadata_ranges_per_record':['00..46 positions attributes','75..7F flags attributes'],
 'source_dash_18A6_checked_from_bitmap':True,'dash_in_variant_name_normalized':'自由战斗１',
 'no_formation_position_or_attributes_or_unlock_flags_changed':True}
fn=P/'text/translations/prototype_formations_live_20261011_03.json'
if fn.exists():assert rd(str(fn.relative_to(P)))==artifact
else:fn.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
proof={'ROM':str(out.relative_to(P)),'SHA256':sha(r),'status':'STATIC_PASS_RUNTIME_PENDING','writes':writes,
 'translated_live_formation_records':55,'expanded_aliases':newcount,'new_display_helper':f'{newhelper:06X}',
 'arena_end':f'{arena:06X}','all128byte_records_only46byte_text_changed':True,
 'unused9_records_unchanged':True,'new_source':str(fn.relative_to(P))}
pf.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:proof[k]for k in ['ROM','SHA256','translated_live_formation_records','expanded_aliases','arena_end']},ensure_ascii=False))

