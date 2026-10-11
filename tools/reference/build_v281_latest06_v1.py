
"""Merge only confirmed type/ID skill fields from source revision06."""
from pathlib import Path
import sys,json,hashlib,copy
P=Path.cwd();rd=lambda f:json.loads((P/f).read_text(encoding='utf8'));sha=lambda z:hashlib.sha256(z).hexdigest().upper()
b=(P/'roms/work/bokuno_cn_candidate_v10ba281_review_feedback_20261011_01.smc').read_bytes();assert sha(b)=='CCF4F590BCC1BCD3A22F4DE7E9CD7637D425DBACDE034A351F97A7E49FB28C33'
r=bytearray(b);m={k:bytes.fromhex(v)for k,v in rd('qa/V281_CURRENT_SINGLE_GLYPH_MAPPING_20261011_02.json').items()};pairs={k:bytes.fromhex(v)for k,v in rd('qa/V281_CURRENT_FIXED_MENU_PAIRS_20261011_02.json').items()}
sys.path.insert(0,str(P/'tools'));from dry_run_encoding_plan import encode
from build_font_payloads import hzk12_glyph
atlas=copy.deepcopy(rd('docs/SINGLE_GLYPH_ATLAS_V281_SOURCE_20261011_02.json'));guard=rd('qa/V281_LATEST06_EXTRA_GLYPH_GUARD_20261011_01.json');writes=[];allowed=set()
def put(at,z,why):
 r[at:at+len(z)]=z;allowed.update(range(at,at+len(z)));writes.append({'at':f'{at:06X}','after_hex':z.hex(' ').upper(),'why':why,'before_SHA256':sha(b[at:at+len(z)])})
hzk=Path('G:/Emu/SFC/修改rom/HZK12').read_bytes();font=[]
for atom,old,code in [('屠','宏',bytes.fromhex('19 5B')),('膝','攀',bytes.fromhex('19 5C'))]:
 q=next(q for q in guard['candidates']if q['old_atom']==old);assert not q['old_atom_in_original_literal_guard']and not q['glyph_used_in_current_compiled_corpus']
 z=hzk12_glyph(atom,hzk);assert z and len(z)==32 and m.pop(old)==code;m[atom]=code
 slot=7*256+code[1];off=slot//8*256+slot%8*16
 for fb in [0x780000,0x7d0000]:put(fb+off,z[:16],'extra confirmed skill glyph upper');put(fb+off+128,z[16:],'extra confirmed skill glyph lower')
 row=next(x for x in atlas['glyphs']if bytes.fromhex(x['code'])==code);row.update(atom=atom,glyphSha256=sha(z),source='v281_confirmed06_skill_sync')
 font.append({'atom':atom,'old_atom':old,'code':code.hex(' ').upper(),'literal_and_active_glyph_guard_pass':True})
def enc(t,compact=False):
 z,miss,err=encode(t,m|(pairs if compact else {}),battle=False);assert not miss and not err,(t,miss,err);return z
changes=rd('qa/V281_LATEST06_DIFF_20261011_01.json')['typed_changes'];full=[]
arena=int(rd('qa/V281_DEFAULT_NAME_BUILD_20261011_01.json')['arena_end'],16)
for x in changes:
 assert x['id'].startswith(('P','E'))
 at=int(x['source_offset'],16);z=enc(x['new'])
 if len(z)>10:
  full.append((at,z,x['id']));z=enc(x['new'],True)
 assert len(z)<=10
 put(at,z+b'\x50'*(10-len(z)),'latest confirmed '+x['id'])
old=rd('text/translations/techniques_spells_category_review_20261011_01.json');new=rd('text/translations/techniques_spells_category_review_20261011_06.json')
prev={x['id']:x for x in old['spells']};spellchanges=[]
for x in new['spells']:
 if x['zh']==prev[x['id']]['zh']:continue
 assert not x['source_glyphs_need_review']
 z=enc(x['zh']);assert len(z)<=10;at=int(x['name_offset'],16);put(at,z+b'\x50'*(10-len(z)),'latest confirmed spell '+x['id']);spellchanges.append({'id':x['id'],'old':prev[x['id']]['zh'],'new':x['zh'],'offset':x['name_offset']})
# One six-character enemy technique receives a full independent string in both renderer paths.
assert len(full)==1 and full[0][2]=='E0146'
at,z,id=full[0];target=arena;assert not any(b[target:target+len(z)]);put(target,z,'full E0146 display string');arena+=len(z)
entry=(at&65535).to_bytes(2,'little')+(target&65535).to_bytes(2,'little')+len(z).to_bytes(2,'little')+b'\0\0'
assert b[0x7fbd68:0x7fbd70]==bytes(8)and b[0x7fbff0:0x7fbff8]==bytes(8)
put(0x7fbd68,entry,'14th battle exact-name entry E0146');put(0x7fbff0,entry,'15th fixed-menu exact-name entry E0146')
for lo,hi in [(0x7fbc00,0x7fbd00),(0x7fb800,0x7fb900)]:
 at=b.find(bytes.fromhex('E0 68 00'),lo,hi);assert at>=lo;put(at,bytes.fromhex('E0 70 00'),'battle name-table end14')
hp=int(rd('qa/V281_PROTOTYPE_FORMATIONS_BUILD_20261011_04.json')['new_display_helper'],16)+0x400000
n=rd('qa/V281_DISPLAY_BUILD_20261011_03.json')['helper_bytes'];at=b.find(bytes.fromhex('E0 70 00'),hp,hp+n);assert at>=hp;put(at,bytes.fromhex('E0 78 00'),'active fixed-menu name-table end15')
for lo,hi in [(0x3e0f00,0x3e1d00),(0x5baa00,0x5bba00),(0x5b34a0,0x5b37a0),(0x5b79b0,0x5b79e0)]:assert r[lo:hi]==b[lo:hi]
assert r[0x7ffe00:0x7ffff0]==bytes(496)
for h in [0xffdc,0x40ffdc]:r[h:h+4]=bytes.fromhex('ff ff 00 00');allowed.update(range(h,h+4))
c=sum(r)&65535
for h in [0xffdc,0x40ffdc]:r[h:h+4]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little')
assert sum(r)&65535==c and all(i in allowed for i,(x,y)in enumerate(zip(b,r))if x!=y)
out=P/(sys.argv[1]if len(sys.argv)>1 else'roms/work/bokuno_cn_candidate_v10ba281_review_feedback_20261011_02.smc');pf=P/(sys.argv[2]if len(sys.argv)>2 else'qa/V281_LATEST06_BUILD_20261011_02.json');assert not out.exists()and not pf.exists();out.write_bytes(r)
proof={'ROM':str(out.relative_to(P)),'SHA256':sha(r),'base_SHA256':sha(b),'status':'STATIC_PASS_RUNTIME_PENDING','writes':writes,'confirmed_typed_changes':changes,'confirmed_spell_changes':spellchanges,'extra_glyphs':font,'full_name_exception':'E0146斯芬克斯谜语,12bytes independent string; compact fixed fallback only','source_manifest':'text/translations/translation_sources_current_20261011_06.json','user_confirmation_priority':True,'never_apply_spell_M_IDs_to_monsters_or_formations':True,'all_gameplay_table_bytes_preserved':True,'arena_end':f'{arena:06X}'}
pf.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
atlas.update(final_ROM_SHA256=sha(r),source_version='v281_latest06_confirmations')
for f,data in [('qa/V281_CURRENT_SINGLE_GLYPH_MAPPING_20261011_06.json',{k:v.hex(' ').upper()for k,v in m.items()}),('docs/SINGLE_GLYPH_ATLAS_V281_FEEDBACK_20261011_06.json',atlas)]:
 p=P/f
 if p.exists():assert rd(f)==data
 else:p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:proof[k]for k in ['ROM','SHA256','arena_end']},ensure_ascii=False));print('latest typed',len(changes),'latest spell',len(spellchanges))

