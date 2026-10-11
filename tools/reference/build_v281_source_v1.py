
"""Build v281 latest confirmed source text, without changing gameplay tables."""
from pathlib import Path
import sys,json,re,hashlib,copy,collections
from PIL import Image,ImageFont
sys.path.insert(0,str(Path(__file__).parent))
from dry_run_encoding_plan import encode
from build_font_payloads import hzk12_glyph,encode_pixels,render_char
P=Path.cwd().resolve();assert P==Path('G:/CodexProjects/Bokuno中文化工程/bokuno_cn')
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'));sha=lambda z:hashlib.sha256(z).hexdigest().upper()
basefile='roms/work/bokuno_cn_candidate_v10az280_feedback_20261010_05.smc'
b=(P/basefile).read_bytes();assert sha(b)=='DA6FE79F62A8937C55760C6F4D8F1F3B97F47803DBF996254A7C4B7AFAFEDAE9'
source=(P/'../roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
r=bytearray(b);allow=set();writes=[]
out=P/(sys.argv[1] if len(sys.argv)>1 else 'roms/work/bokuno_cn_diag_v10ba281_source_20261011_01.smc')
proof=P/(sys.argv[2] if len(sys.argv)>2 else 'qa/V281_SOURCE_BUILD_20261011_01.json')
assert not out.exists() and not proof.exists()
def put(at,z,why,id=None):
 assert 0<=at<=len(b)-len(z)
 r[at:at+len(z)]=z;allow.update(range(at,at+len(z)))
 writes.append({'at':f'{at:06X}','bytes':len(z),'why':why,'id':id,'before_SHA256':sha(b[at:at+len(z)]),'after_hex':z.hex(' ').upper()})
manifest=rd('text/translations/translation_sources_current_20261011_02.json')
typed=rd(manifest['latest_typed_review']);pending=[x for x in typed['translations'] if x.get('compiled_ROM_SHA256') is None];assert len(pending)==121
sp=rd(manifest['latest_techniques_and_spells']);items=rd(manifest['items_snapshot'])
m={k:bytes.fromhex(v) for k,v in rd('qa/V280_CURRENT_SINGLE_GLYPH_MAPPING_20261010_04.json').items() if len(k)==1}
pairs={k:bytes.fromhex(v) for k,v in rd('qa/V280_CURRENT_FIXED_MENU_PAIRS_20261010_04.json').items()}
atlas=copy.deepcopy(rd('docs/SINGLE_GLYPH_ATLAS_V280_FEEDBACK_20261010_05.json'))
oldman=rd('docs/ALINE_V10AJ264_BATCH263B_STORY_20261008_05.json');records={x['id']:x for x in oldman['records']}
def shadowptr(src):
 bank=src>>16;bank=bank|0xc0 if bank<0x40 else bank;desc=0x3ff800+bank*5
 n=int.from_bytes(b[desc:desc+2],'little');tab=int.from_bytes(b[desc+2:desc+5],'little')
 keys=[int.from_bytes(b[tab+i*2:tab+i*2+2],'little') for i in range(n)]
 assert keys==sorted(set(keys)) and src&65535 in keys
 pi=tab+2*n+keys.index(src&65535)*3;at=int.from_bytes(b[pi:pi+3],'little')
 at=at+0x400000 if 0x3e8000<=at<0x400000 else at
 return pi,at,bank
scan=[]
for x in oldman['records']:
 pi,at,bank=shadowptr(int(x['source'],16))
 tail=b'\xff'+((bank<<16)|(int(x['resume'],16)&65535)).to_bytes(3,'little')
 end=b.find(tail,at,at+2048);assert end>=at,(x['id'],hex(at));scan.append(b[at:end])
tables=rd('text/extracted/fixed_tables.json')['tables']
for t in tables.values():
 for x in t['records']:at=int(x['offset'],16);scan.append(b[at:at+x['record_size']])
scan += [b[0x3d6200:0x3d7800],b[0x3d7d00:0x3daa00],b[0x5e69b0:0x5e6f00],b[0x7fc100:0x7fc700],b[0x7fbe00:0x7fbf00]]
compiled=b''.join(scan)
def glyphcodes(z):
 used=set();i=0
 while i<len(z):
  lead=z[i]
  if lead in set(range(0x10,0x1a))|set(range(0x20,0x24))|{0x46}:
   used.add(z[i:i+2]);i+=2
  elif lead in {0x2b,0x30,0x39,0x3a,0x3b,0x4a,0x4b}:i+=2
  else:i+=1
 return used
active_codes=set().union(*(glyphcodes(z)for z in scan))
alltext=rd('qa/V281_FONT_LITERAL_GUARD_20261011_01.json')['known_translation_characters']
free=[{'code':f'19 {v:02X}','old_atom':None}for v in range(0xe7,0xec)]
reuse=[{'code':x['code'],'old_atom':x['atom']} for x in atlas['glyphs'] if x['class']=='single' and x['atom'] not in alltext and bytes.fromhex(x['code']) not in active_codes]
free+=reuse
missing=sorted({c for x in sp['spells'] if not x['source_glyphs_need_review'] for c in re.sub(r'\{[^{}]+\}','',x['zh']) if c not in m})
assert len(missing)==12 and len(free)>=13,(missing,free)
hzk=(Path('G:/Emu/SFC/修改rom/HZK12')).read_bytes();font=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',12);small=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',7)
def bitmap(ch):
 z=hzk12_glyph(ch,hzk);return z if z is not None else encode_pixels(render_char(ch,font,small))
def unpack(z):
 im=Image.new('1',(16,16),0)
 for y in range(16):
  for x in range(16):
   if z[(y//8*2+x//8)*8+y%8]>>(7-x%8)&1:im.putpixel((x,y),1)
 return im
allocations=[]
for atom in missing+['风与']:
 q=free.pop(0);code=bytes.fromhex(q['code']);old_atom=q['old_atom']
 assert code not in active_codes
 if old_atom:
  assert old_atom not in alltext and m.pop(old_atom)==code
  atlas['glyphs']=[x for x in atlas['glyphs']if bytes.fromhex(x['code'])!=code]
 if len(atom)==1:z=bitmap(atom);m[atom]=code;kind='single'
 else:
  im=Image.new('1',(16,16),0)
  for i,c in enumerate(atom):im.paste(unpack(bitmap(c)).crop((2,2,14,14)).resize((7,12),Image.Resampling.NEAREST),(i*7+1,2))
  z=encode_pixels(im);pairs[atom]=code;kind='composite_pair'
 h,l=code;slot=(7 if h==0x19 else h-0x10)*256+l;off=slot//8*256+slot%8*16
 old=b[0x780000+off:0x780010+off]+b[0x780080+off:0x780090+off]
 for base in [0x780000,0x7d0000]:
  assert b[base+off:base+off+16]+b[base+off+128:base+off+144]==old
  put(base+off,z[:16],'font_upper',atom);put(base+off+128,z[16:],'font_lower',atom)
 atlas['glyphs'].append({'atom':atom,'code':code.hex(' ').upper(),'class':kind,'glyphSha256':sha(z),'source':'v281_source_integration','fixed_menu_only':len(atom)>1})
 allocations.append({'atom':atom,'code':code.hex(' ').upper(),'reclaimed_atom':old_atom,'old_glyph_SHA256':sha(old),'new_glyph_SHA256':sha(z),'guard_current_literals_and_compiled_names_unused':True})
def enc(t,fixed=False,battle=False):
 t=re.sub(r'\{原字([0-9A-F]{2}):([0-9A-F]{2})\}',lambda a:'{CODE:'+a[1]+a[2]+'}',t)
 z,mis,err=encode(t,m|(pairs if fixed else {}),battle=battle);assert not mis and not err,(t,mis,err);return z
# This single zero-filled range is outside all current code, tables, and fonts.
arena=0x7fc700;assert b[arena:0x7ffe00]==bytes(0x7ffe00-arena)
def allocate(data,why,id):
 global arena
 at=arena;arena+=len(data);assert arena<0x7ffe00 and not any(b[at:arena])
 put(at,data,why,id);return at
applied=[]
for x in pending:
 if not x['id'].startswith('C'):continue
 rec=records[x['text_id']];src=int(rec['source'],16);pi,old,bank=shadowptr(src)
 tail=b'\xff'+((bank<<16)|(int(rec['resume'],16)&65535)).to_bytes(3,'little')
 assert b.find(tail,old,old+2048)>=old
 z=enc(x['translation_zh_cn']);at=allocate(z+tail,'shadow_payload',x['id'])
 put(pi,(at-0x400000).to_bytes(3,'little'),'existing_shadow_pointer',x['id'])
 applied.append({'id':x['id'],'text_id':x['text_id'],'kind':'shadow','offset':f'{at:06X}','bytes':len(z),'pointer_offset':f'{pi:06X}','return_hex':tail.hex(' ').upper()})
cat={x['text_id']:x for x in rd('text/translation_catalog_propagated.json')['entries']}
for x in pending:
 if x['id'].startswith('C') or x['file'].endswith(('10_descriptions_stars.md','11_menu_trade_system.md','12_battle_messages.md','13_battle_ui_steal.md')):continue
 at=int(x['source_offset'],16);cap=cat[x['text_id']]['metadata']['record_size'];z=enc(x['translation_zh_cn'])
 if len(z)>cap:z=enc(x['translation_zh_cn'],True)
 assert len(z)<=cap,(x['id'],x['translation_zh_cn'],len(z),cap)
 put(at,z+b'\x50'*(cap-len(z)),'fixed_record',x['id']);applied.append({'id':x['id'],'text_id':x['text_id'],'kind':'fixed','offset':f'{at:06X}','bytes':len(z)})
# Rebuild descriptions with their native space-separated line format.
descs=[x for x in typed['translations']if x['file'].endswith('10_descriptions_stars.md')];assert len(descs)==185
def splitlines(t):
 if ' 'in t:return t.split(' ')
 if len(t)<=14:return[t]
 result=[]
 while len(t)>14:
  cut=14
  punctuation=[i+1 for i,c in enumerate(t[:14])if c in '，、；：。']
  if punctuation and punctuation[-1]>=6:cut=punctuation[-1]
  if cut<len(t) and t[cut-1] in 'ＨＴＷＬＳ' and t[cut] in 'Ｐ':cut-=1
  result.append(t[:cut]);t=t[cut:]
 result.append(t);return result
descrows=[];blob=bytearray();offsets=[0]
for x in sorted(descs,key=lambda x:int(x['text_id'].rsplit('_',1)[1],16)):
 text=x['translation_zh_cn'];lines=x.get('display_layout',{}).get('display_lines')or splitlines(text)
 assert ''.join(lines)==text.replace(' ','') and all(len(v)<=14 for v in lines)
 z=enc(' '.join(lines));at=0x3d6200+len(blob);blob.extend(z);offsets.append(len(blob))
 descrows.append({'id':x['id'],'index':len(descrows),'lines':lines,'encoded_hex':z.hex(' ').upper(),'offset':f'{at:06X}'})
assert len(blob)<=0x1400
put(0x3d6000,b''.join(i.to_bytes(2,'little')for i in offsets),'description_pointers')
put(0x3d6200,blob+b'\xff'*(0x15fb-len(blob)),'native_wrapped_description_pool')
# v277 placed the 57-cell menu glyph stream inside former description padding.
# Preserve that allocation when rebuilding the shared pool.
put(0x3d7600,b[0x3d7600:0x3d7680],'preserve_existing_57_cell_menu_preload_inside_padding')
applied += [{'id':x['id'],'kind':'description','offset':x['offset']} for x in descrows if any(y['id']==x['id']for y in pending)]
# Tavern option grows from five to six bytes; use a bounded shadow entry
# returning to the unchanged choice terminator rather than truncating the name.
for x in pending:
 if x['text_id']=='ui_companion_cancel_3CC5B9':
  z=enc(x['translation_zh_cn']);assert b[0x3cc5b9:0x3cc5be]==enc('取消')+b'\x50'
  at=allocate(z+bytes.fromhex('FF BE C5 FC'),'tavern_cancel_shadow',x['id'])
  d=0x3ff800+0xfc*5;n=int.from_bytes(b[d:d+2],'little');tab=int.from_bytes(b[d+2:d+5],'little')
  keys=[int.from_bytes(b[tab+2*i:tab+2*i+2],'little')for i in range(n)]
  values=[bytes(r[tab+2*n+3*i:tab+2*n+3*i+3])for i in range(n)]
  assert 0xc5b9 not in keys
  rows=sorted(list(zip(keys,values))+[(0xc5b9,(at-0x400000).to_bytes(3,'little'))])
  table=b''.join(k.to_bytes(2,'little')for k,v in rows)+b''.join(v for k,v in rows)
  newtab=allocate(table,'FC_shadow_directory_with_one_new_key',x['id'])
  put(d,(n+1).to_bytes(2,'little')+(newtab-0x400000).to_bytes(3,'little'),'FC_directory_descriptor')
  applied.append({'id':x['id'],'text_id':x['text_id'],'kind':'new_shadow_key','offset':f'{at:06X}','source':'3CC5B9','resume':'FCC5BE'})
# Update only the changed indexed menu entry and keep all other encoded entries.
ptrs=[int.from_bytes(b[0x3d7800+i*2:0x3d7802+i*2],'little')for i in range(566)]
menu_changes={int(x['text_id'].rsplit('_',1)[1],16):x for x in pending if x['file'].endswith('11_menu_trade_system.md') and x['text_id'].startswith('indexed_indexed_pool_3d7d00_')}
pool=bytearray();offs=[0]
for i in range(565):
 if i in menu_changes:
  x=menu_changes[i];z=enc(x['translation_zh_cn'],True);applied.append({'id':x['id'],'text_id':x['text_id'],'kind':'indexed_menu','offset':f'{0x3d7d00+len(pool):06X}'})
 else:z=b[0x3d7d00+ptrs[i]:0x3d7d00+ptrs[i+1]]
 pool.extend(z);offs.append(len(pool))
assert len(pool)<=0x1b00
put(0x3d7800,b''.join(v.to_bytes(2,'little')for v in offs),'menu_pointers');put(0x3d7d00,pool+b'\xff'*(0x1b00-len(pool)),'menu_pool')
for x in pending:
 if x['file'].endswith('13_battle_ui_steal.md'):
  idx=int(x['text_id'].rsplit('_',1)[1],16);lo=int.from_bytes(b[0x3d9800+idx*2:0x3d9802+idx*2],'little')+0x3d9a00
  n=int.from_bytes(b[0x7f9fd0+idx*2:0x7f9fd2+idx*2],'little');z=enc(x['translation_zh_cn']);assert len(z)==n
  put(lo,z,'battle_UI_same_length',x['id']);applied.append({'id':x['id'],'text_id':x['text_id'],'kind':'battle_UI','offset':f'{lo:06X}'})
 elif x['file'].endswith('12_battle_messages.md'):
  idx=50+int(x['text_id'].rsplit('_',1)[1],16);lo=int.from_bytes(b[0x3d9800+idx*2:0x3d9802+idx*2],'little')+0x3d9a00
  n=int.from_bytes(b[0x7f9fd0+idx*2:0x7f9fd2+idx*2],'little');z=enc(x['translation_zh_cn'],battle=True);assert len(z)==n
  put(lo,z,'battle_message_same_length',x['id']);applied.append({'id':x['id'],'text_id':x['text_id'],'kind':'battle','offset':f'{lo:06X}'})
itemrows=[]
for x in items['translations']:
 if x.get('compiled_ROM_SHA256','old')is not None:continue
 at=int(x['offset'],16);cap=x['record_bytes'];z=enc(x['translation_zh_cn']);assert len(z)<=cap
 put(at,z+b'\x50'*(cap-len(z)),'latest_item_name',x['complete_review_id']);itemrows.append({'id':x['complete_review_id'],'offset':x['offset'],'zh':x['translation_zh_cn'],'hex':z.hex(' ').upper()})
assert len(itemrows)==4
spellrows=[];held=[]
for x in sp['spells']:
 at=int(x['name_offset'],16);assert b[at:at+10]==source[at:at+10]
 if x['source_glyphs_need_review']:held.append({'id':x['id'],'zh_proposal':x['zh'],'raw_original_hex':b[at:at+10].hex(' ').upper(),'reason':'original_source_glyph_unconfirmed'});continue
 z=enc(x['zh'])
 if len(z)>10:z=enc(x['zh'],True)
 assert len(z)<=10
 put(at,z+b'\x50'*(10-len(z)),'independent_spell_name',x['id']);spellrows.append({'id':x['id'],'offset':x['name_offset'],'category':x['category'],'zh':x['zh'],'hex':z.hex(' ').upper(),'bytes':len(z)})
assert len(spellrows)==232 and len(held)==4
for empty in sp['empty_spell_slots']:idx=int(empty,16);at=0x5ba000+idx*10;assert r[at:at+10]==b[at:at+10]
# Both live menu preload and original text labels must agree; the money template had pointed to 物.
ui=rd(manifest['latest_ui_overlay'])
for x in ui['main_menu_labels']:
 at=int(x['at'],16);z=bytes.fromhex(x['pending_hex']);assert len(z)==x['capacity_bytes'];put(at,z,'main_menu_label',x['id'])
assert b[0x3d7630:0x3d7632]==bytes.fromhex('21 AC')
put(0x3d7630,enc('型'),'relocated_57_cell_menu_formation')
assert b[0x3d7640:0x3d7646]==bytes.fromhex('20 D7 21 51 20 D2')
put(0x3d7640,enc('所持金'),'relocated_57_cell_menu_money')
moneyat=b.find(bytes.fromhex('32 26 34 1A'),0x3df897,0x3df8c0);assert moneyat>=0
put(moneyat,bytes.fromhex('32 33 34'),'money_three_cached_cell_template')
from build_aline_m4_creation_ui_v1 import display_cells
school=b''.join(m[c]for c in'苍龙朱鸟白虎玄武太阳月')+b'\x50'
assert display_cells(school)==12 and len(school)<=23
put(0x3dfc33,school+b'\xff'*(23-len(school)),'Chinese six schools and Moon left alignment; same12cells')
# Preserve source VM control sites, gameplay tables, font-independent adjacent icon data.
for site in rd('build/source_control_table264_20261008_05.json')['sites']:
 at=site['CPU']-0xc00000;assert r[at:at+2]==b[at:at+2]
for lo,hi in [(0x3e0f00,0x3e1d00),(0x5baa00,0x5bba00),(0x5b34a0,0x5b37a0),(0x5b79b0,0x5b79e0)]:assert r[lo:hi]==b[lo:hi]
assert r[0x7ffe00:0x7ffff0]==bytes(496)
for h in [0xffdc,0x40ffdc]:r[h:h+4]=bytes.fromhex('ff ff 00 00');allow.update(range(h,h+4))
checksum=sum(r)&65535
for h in [0xffdc,0x40ffdc]:r[h:h+4]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
assert sum(r)&65535==checksum and all(i in allow for i,(x,y)in enumerate(zip(b,r))if x!=y)
assert len(applied)==121,(len(applied),collections.Counter(x['kind']for x in applied))
out.write_bytes(r)
atlas['summary'].update(singles=sum(x['class']=='single'for x in atlas['glyphs']),composites=sum(x['class']=='composite_pair'for x in atlas['glyphs']),free=1792-len(atlas['glyphs']))
atlas.update(source_version='v281_source_01',final_ROM_SHA256=sha(r))
d={'status':'SOURCE_STATIC_PASS_RUNTIME_PENDING','ROM':str(out.relative_to(P)),'SHA256':sha(r),'base_ROM':basefile,'base_SHA256':sha(b),'writes':writes,'applied_typed_records':applied,'items':itemrows,'spells':spellrows,'held_spells':held,'new_font_allocations':allocations,'unused_font_slots':atlas['summary']['free'],'description_rows':descrows,'description_pool_bytes':len(blob),'wrapped_description_count':sum(len(x['lines'])>1 for x in descrows),'menu_pool_bytes':len(pool),'new_shadow_arena_end':f'{arena:06X}','money_template_offset':f'{moneyat:06X}','gameplay_data_and_957_control_sites_preserved':True,'formal_baseline_promoted':False}
proof.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
tag=sys.argv[3] if len(sys.argv)>3 else '01'
for fn,data in [('qa/V281_CURRENT_SINGLE_GLYPH_MAPPING_20261011_01.json',{k:v.hex(' ').upper()for k,v in m.items()}),('qa/V281_CURRENT_FIXED_MENU_PAIRS_20261011_01.json',{k:v.hex(' ').upper()for k,v in pairs.items()}),('docs/SINGLE_GLYPH_ATLAS_V281_SOURCE_20261011_01.json',atlas)]:
 fn=fn.replace('_20261011_01.json','_20261011_'+tag+'.json')
 f=P/fn;assert not f.exists();f.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:d[k]for k in ['ROM','SHA256','unused_font_slots','wrapped_description_count','description_pool_bytes','new_shadow_arena_end']},ensure_ascii=False))

