"""Build the user-approved missing-text tables on verified package19."""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys
from PIL import Image, ImageFont
from audit_missing_review_global_impact_20261011_v1 import parse_review, norm
from build_font_payloads import hzk12_glyph, render_char, encode_pixels
from dry_run_encoding_plan import encode

P = Path(__file__).resolve().parents[1]
rd = lambda f: json.loads((P/f).read_text(encoding='utf-8-sig'))
sha = lambda z: hashlib.sha256(z).hexdigest().upper()
TWO = set(range(0x10,0x17)) | {0x18,0x19,0x46,0x20,0x21,0x22,0x23}

def atoms(z):
    out=[];i=0
    while i<len(z):
        n=2 if z[i] in TWO else 1
        assert i+n<=len(z)
        out.append(z[i:i+n]);i+=n
    return out

def unpack(z):
    im=Image.new('1',(16,16),0)
    for y in range(16):
        for x in range(16):
            if z[(y//8*2+x//8)*8+y%8] >> (7-x%8)&1:im.putpixel((x,y),1)
    return im

# Explicit subfield cell budgets from the original native glyph stream.
FIELDS = {
 3:[('游戏时间',5),('未使用',3),('读档',3)],
 4:[('武器',2),('卸下',3),('威力',2),('力',1),('固有技',3),('防御力',3),('回避率',3),('％',1),('物理',2),('魔法',2),('状态',2)],
 23:[('物理防御',4),('魔法防御',4)],
 24:[('有效性',3),(' ',1),('斩',1),('打',1),('突',1),('射',1),('热',1),('冷',1),('雷',1),('状',1)],
 25:[('道具店',3),('  ',2),('持有物品',3)],
 27:[('性',1),('角色',6)],
 28:[('男',1),('女',1),('姓名',2),('性别',2),('人物',2),('宿星',2)],
 37:[('平假名',4),('片假名',4)],
 43:[('是',2),('否',3)],
 44:[(bytes.fromhex('31'),1),('键',3),('：',1),('←',1),(' ',1)],
 46:[('当前进行的事件',10),('继续',2)],
 57:[('苍龙',2),('朱鸟',2),('白虎',2),('玄武',2),('太阳',2),('月',2)],
 58:[('学会此术后，将遗忘',8),(bytes.fromhex('F2 F2'),2),('的全部术。',9)],
 59:[('是否确认？',6),('是',2),('否',3)],
 60:[('武器',2),(bytes.fromhex('45 47 9E'),3),('威力',2),('力',1),('固有技',3),('防御力',3),('回避率',3),('％',1),('物理',2),('魔法',2),('状态',2)],
 61:[('确定要存档吗？',15),('是',2),('否',3)],
 62:[('系统设置',4),('声音',4),('立体声',4),('单声道',4)],
 63:[('仓库',2),('持有物品',3),('取出',4),('存入',3)],
 64:[('买',2),('来出售',5),(bytes.fromhex('8B 30 50 50 50'),5),('卖出',2),('…',1),('装备中',3),('需要',3)],
 65:[('…',1),('阵型',2),('作战',2),('指挥官战术',6)],
 67:[(bytes.fromhex('30 50'),2),('需要',4),(bytes.fromhex('32'),1),('键',3),('：',1),('状态画面',7)],
 70:[('菜单光标速度',12),('普通',2),('快速',2)],
}

def main():
    out=P/(sys.argv[1] if len(sys.argv)>1 else 'roms/work/bokuno_cn_candidate_v10bc283_missing_translations_20261011_01.smc')
    proof=P/(sys.argv[2] if len(sys.argv)>2 else 'qa/V283_MISSING_TRANSLATIONS_BUILD_20261011_01.json')
    auxiliary=(len(sys.argv)<4 or sys.argv[3]!='independent')
    assert out.is_relative_to(P) and proof.is_relative_to(P) and not out.exists() and not proof.exists()
    frozen='text/translations/translation_sources_before_v283_20261011_01.json'
    manifest=rd(frozen if (P/frozen).exists() else 'text/translations/translation_sources_current.json')
    assert manifest['build_revision']=='v282_two_display_fixes01'
    basefile=manifest['latest_test_ROM']['file'];b=(P/basefile).read_bytes()
    assert sha(b)==manifest['latest_test_ROM']['SHA256']=='F5958F254213D942A10F64351F9745ED00E232A2B3756116D5681853E2FACA1A'
    s=(P/'../roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
    audit=rd('qa/MISSING_TRANSLATION_GLOBAL_IMPACT_20261011_01.json')
    for f,h in audit['input_SHA256'].items():
        path=P/(frozen if f=='text/translations/translation_sources_current.json' and (P/frozen).exists() else f)
        assert sha(path.read_bytes())==h,f
    inventory=rd('text/extracted/missing_menu_inventory_v282_20261011_01.json')
    inv={x['id']:x for x in inventory['rows']};rows=parse_review();assert len(rows)==703
    r=bytearray(b);allow=bytearray(len(b));writes=[]
    def put(at,z,why,id=None):
        assert 0<=at<=len(b)-len(z)
        r[at:at+len(z)]=z;allow[at:at+len(z)]=b'\1'*len(z)
        writes.append({'offset':f'{at:06X}','bytes':len(z),'reason':why,'id':id,'before_hex':b[at:at+len(z)].hex(' ').upper(),'after_hex':z.hex(' ').upper()})
    m={k:bytes.fromhex(v) for k,v in rd('qa/V281_CURRENT_SINGLE_GLYPH_MAPPING_20261011_06.json').items()}
    pairs={k:bytes.fromhex(v) for k,v in rd('qa/V281_CURRENT_FIXED_MENU_PAIRS_20261011_02.json').items()}
    aliases={k:bytes.fromhex(v) for k,v in audit['proposed_ASCII_aliases'].items()};m.update(aliases)
    font=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',12)
    small=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',7)
    hzk=Path('G:/Emu/SFC/修改rom/HZK12').read_bytes()
    def bitmap(ch):
        z=hzk12_glyph(ch,hzk)
        return z if z is not None else encode_pixels(render_char(ch,font,small))
    occupied=set(m.values())|set(pairs.values())
    safe=rd('text/extracted/native46_blank_slot_audit_v1.json')
    slots=[]
    for value in safe['availableLowBytes']:
        low=int(value,16);code=bytes([0x46,low]);at=0x60A000+low//8*256+low%8*16
        if code not in occupied and s[at:at+16]+s[at+128:at+144]==bytes(32) and b[at:at+16]+b[at+128:at+144]==bytes(32):slots.append(low)
    assert len(slots)>=50
    glyphs=[]
    def newglyph(atom,composite=False):
        assert slots
        low=slots.pop(0);code=bytes([0x46,low]);at=0x60A000+low//8*256+low%8*16
        if composite:
            im=Image.new('1',(16,16),0)
            for i,ch in enumerate(atom):im.paste(unpack(bitmap(ch)).crop((2,2,14,14)).resize((7 if i==0 else 6,12),Image.Resampling.NEAREST),(0 if i==0 else 7,2))
            z=encode_pixels(im)
        else:z=bitmap(atom)
        assert len(z)==32 and any(z)
        # The fixed menu retains thirteen bitmap columns. Keep every new ink
        # pixel within x0..12, matching the existing 冠/顿 display correction.
        im=unpack(z);box=im.getbbox();shift=max(0,box[2]-13)
        if shift:
            assert box[0]>=shift
            shifted=Image.new('1',(16,16),0);shifted.paste(im,(-shift,0))
            assert sum(shifted.get_flattened_data())==sum(im.get_flattened_data())
            z=encode_pixels(shifted)
        put(at,z[:16],'audited blank native46 glyph upper',atom);put(at+128,z[16:],'audited blank native46 glyph lower',atom)
        (pairs if composite else m)[atom]=code
        glyphs.append({'atom':atom,'class':'fixed_only_pair' if composite else 'single','code':code.hex(' ').upper(),'offset':f'{at:06X}','SHA256':sha(z),'glyph_hex':z.hex(' ').upper(),'original_and_current_slot_blank':True,'ink_left_shift':shift,'all_ink_preserved_inside_13_columns':True})
        return code
    for ch in sorted(audit['missing_new_glyph_occurrences']):newglyph(ch)
    def enc(t,compact=False):
        z,missing,errors=encode(t,m|(pairs if compact else {}),battle=False)
        assert not missing and not errors,(t,missing,errors)
        return z
    def compact_for(t,capacity,cells=False):
        z=enc(t)
        fits=lambda z:len(atoms(z))<=capacity if cells else len(z)<=capacity
        if fits(z):return z
        z=enc(t,True)
        k=len(t)
        while not fits(z) and k>=2:
            pair=t[k-2:k]
            if pair not in pairs:newglyph(pair,True)
            z=enc(t,True);k-=2
        assert fits(z),(t,capacity,len(z),len(atoms(z)))
        return z
    arena=int(audit['current_tail_arena_end'],16)
    def alloc(z,why,id=None):
        nonlocal arena
        at=arena;arena+=len(z);assert arena<0x7FFE00 and b[at:arena]==bytes(len(z))
        put(at,z,why,id);return at
    applied=[];held=[];long_names=[]
    for row in rows:
        x=inv[row['id']];kind=x['kind'];at=int(x['offset'],16);text=row['resolved_zh']
        assert s[at:at+x['capacity']]==bytes.fromhex(x['raw_hex'])
        if row['internal_or_input_character']:
            held.append({'id':row['id'],'reason':'internal placeholder/input structure preserved'});continue
        if kind=='K':
            full=enc(text);fallback=compact_for(text,10)
            put(at,fallback+b'\x50'*(10-len(fallback)),'inherent name confirmed first',row['id'])
            if len(full)>10:
                target=alloc(full,'full inherent name display string',row['id'])
                long_names.append({'id':row['id'],'source':f'5F{at&65535:04X}','zh':text,'target':f'{target-0x400000:06X}','bytes':len(full),'fallback_hex':fallback.hex(' ').upper(),'full_hex':full.hex(' ').upper()})
            applied.append({'id':row['id'],'kind':kind,'zh':text,'offset':f'{at:06X}'})
        elif kind in 'TMI':
            # Spaces are native line separators in these description records.
            lines=[];remaining=text
            while len(remaining)>14:
                cut=14
                points=[i+1 for i,ch in enumerate(remaining[:14])if ch in '，、；：。']
                if points and points[-1]>=6:cut=points[-1]
                if cut<len(remaining) and remaining[cut-1] in 'HL' and remaining[cut]=='P':cut-=1
                lines.append(remaining[:cut]);remaining=remaining[cut:]
            lines.append(remaining)
            payload=b'\x50'.join(enc(line)for line in lines)
            assert len(payload)<=63 and all(len(line)<=14 for line in lines)
            put(at,bytes([len(payload)])+payload+bytes(63-len(payload)),'expanded description length and payload',row['id'])
            applied.append({'id':row['id'],'kind':kind,'zh':text,'lines':lines,'offset':f'{at:06X}','payload_hex':payload.hex(' ').upper(),'bytes':len(payload)})
    # Synchronize only exact Japanese identities and typed namespaces.
    typed=copy.deepcopy(rd(manifest['latest_typed_review']));skills=copy.deepcopy(rd(manifest['latest_techniques_and_spells']));items=copy.deepcopy(rd(manifest['latest_items']))
    targets={norm(c['jp']):c['new_zh'] for c in audit['name_conflicts_with_current_sources']}
    related=[];done=set()
    for x in typed['translations']:
        if not x['id'].startswith(('P','E')):continue
        text=targets.get(norm(x.get('source_corrected')or x.get('jp','')))
        if x['id']=='P0219':text='天衣无缝';x['jp']=x['source_corrected']='天衣無縫'
        if not text or x['translation_zh_cn']==text:continue
        old=x['translation_zh_cn'];x['translation_zh_cn']=text;at=int(x['source_offset'],16);z=enc(text);assert len(z)<=10
        put(at,z+b'\x50'*(10-len(z)),'exact related player/enemy technique name',x['id']);done.add(at)
        x.update(previous_translation_zh_cn=old,translation_status='v283_user_rule_compiled',review_source='docs/missing_translation_review_20261011')
        related.append({'id':x['id'],'offset':f'{at:06X}','old':old,'new':text,'namespace':'typed player/enemy technique'})
    for group in ['techniques','spells']:
        for x in skills[group]:
            text=targets.get(norm(x['jp']))
            if x['id']=='P0219':text='天衣无缝';x['jp']='天衣無縫'
            if not text or x['zh']==text:continue
            old=x['zh'];x['zh']=text;at=int(x.get('name_offset',x.get('source_name_offset')),16);z=enc(text);assert len(z)<=10
            if at not in done:put(at,z+b'\x50'*(10-len(z)),'exact related spell name',x['id']);related.append({'id':x['id'],'offset':f'{at:06X}','old':old,'new':text,'namespace':group});done.add(at)
    for x in items['translations']:
        text=targets.get(norm(x['source_jp']))
        if not text or x['translation_zh_cn']==text:continue
        old=x['translation_zh_cn'];at=int(x['offset'],16);z=enc(text);cap=x['record_bytes'];assert len(z)<=cap
        put(at,z+b'\x50'*(cap-len(z)),'exact related item name',x['complete_review_id'])
        x.update(translation_zh_cn=text,display_zh_cn=text,runtime_record_hex=(z+b'\x50'*(cap-len(z))).hex(' ').upper(),previous_translation_zh_cn=old)
        related.append({'id':x['complete_review_id'],'offset':f'{at:06X}','old':old,'new':text,'namespace':'item'})
    # Preserve each cached field's cell positions; relocation changes bytes only.
    menu_arena=0x3DB840;menu_limit=0x3DC000;menu=[];address_map={}
    for row in rows:
        x=inv[row['id']]
        if x['kind']!='U' or row['internal_or_input_character']:continue
        text=row['resolved_zh'];raw=bytes.fromhex(x['raw_hex']);budget=len(atoms(raw));idx=x['index']
        if idx in [102,103]:
            # The active pools are relocated copies with 57/38 fixed cells.
            # Expanding the obsolete three-byte source slot would eat its neighbor.
            applied.append({'id':row['id'],'kind':'U','zh':text,'active_preload_copy_updated':True})
            continue
        if idx==56:
            # This pointer was deliberately reassigned to the actual dodge-skill
            # heading by the earlier human feedback; preserve that distinct UI.
            menu.append({'id':row['id'],'review_zh':text,'runtime_zh':'见切','status':'existing distinct dodge-category heading retained','offset':'3DFE80'})
            applied.append({'id':row['id'],'kind':'U','zh':'见切','review_zh':text,'existing_feedback_semantics_retained':True});continue
        fields=FIELDS.get(idx,[(text,budget)])
        assert sum(n for _,n in fields)==budget,(row['id'],sum(n for _,n in fields),budget)
        data=bytearray();parts=[];source_cell=0;tokens=atoms(raw)
        for content,n in fields:
            old_field=int(x['offset'],16)+sum(len(a)for a in tokens[:source_cell])
            part=content if isinstance(content,bytes)else compact_for(content,n,True)
            assert len(atoms(part))<=n,(row['id'],content,n)
            part+=b'\x50'*(n-len(atoms(part)));parts.append({'text':content.hex(' ').upper()if isinstance(content,bytes)else content,'cells':n,'byte_start':len(data),'old_field_offset':f'{old_field:06X}','raw_icon_or_dynamic':isinstance(content,bytes)})
            data.extend(part);source_cell+=n
        assert len(atoms(data))==budget
        if idx>=100:
            assert len(data)<=x['capacity'],(row['id'],len(data),x['capacity'])
            payload=bytes(data)+b'\x50'*(x['capacity']-len(data));put(int(x['offset'],16),payload,'operation label',row['id']);dest=int(x['offset'],16)
        else:
            dest=menu_arena;menu_arena+=len(data)
            assert menu_arena<=menu_limit and b[dest:menu_arena]==s[dest:menu_arena]==b'\xff'*len(data)
            put(dest,bytes(data),'native menu stream cached cells preserved',row['id'])
            put(0x3DF976+idx*2,((dest-0x3DFA08)&65535).to_bytes(2,'little'),'native start-only menu label pointer',row['id'])
            for part in parts:address_map[int(part['old_field_offset'],16)]=dest+part['byte_start']
        menu.append({'id':row['id'],'runtime_review_zh':text,'offset':f'{dest:06X}','cells':budget,'payload_hex':bytes(data).hex(' ').upper(),'fields':parts,'pending_icon_fields_preserved':idx in [44,60,64,67],'dynamic_school_cells_preserved':idx==58})
        applied.append({'id':row['id'],'kind':'U','zh':text,'offset':f'{dest:06X}','native_subfield_caches_preserved':True})
    for identifier,original_start,current_start,count,maxbytes in [('U102',0x3DF830,0x3D7600,57,128),('U103',0x3DF8FF,0x3DFE00,38,96)]:
        x=inv[identifier];position=len(atoms(s[original_start:int(x['offset'],16)]));cursor=current_start;cells=[]
        for _ in range(count):
            n=2 if b[cursor]in TWO else 1;cells.append(b[cursor:cursor+n]);cursor+=n
        assert b''.join(cells[position:position+3])==bytes.fromhex(x['raw_hex'])
        cells[position:position+3]=atoms(enc('页'))+[b'\x50',b'\x50']
        stream=b''.join(cells);assert len(cells)==count and len(stream)<=maxbytes
        put(current_start,stream,'active relocated page-label preload; cell positions retained',identifier)
        menu.append({'id':identifier,'runtime_review_zh':'页','offset':f'{current_start:06X}','cell_offset':position,'pool_cells':count,'payload_hex':stream.hex(' ').upper()})
    # Update proven direct native preload address patterns, if present.
    direct=[]
    for old,new in sorted(address_map.items()):
        pattern=b'\xA2'+(old&65535).to_bytes(2,'little')+bytes.fromhex('86 75 A9 FD 85 77')
        at=0x50000
        while True:
            at=b.find(pattern,at,0x60000)
            if at<0:break
            put(at+1,(new&65535).to_bytes(2,'little'),'exact direct native menu preload operand')
            direct.append({'instruction':f'{at:06X}','old':f'{old:06X}','new':f'{new:06X}'});at+=len(pattern)
    schools=b''.join(enc(t)for t in ['苍龙','朱鸟','白虎','玄武','太阳'])+enc('月')+b'\x50'
    assert len(schools)==23 and len(atoms(schools))==12
    for at in [0x5F38B0,0x5F38D0]:put(at,schools,'prototype school copy; Moon left aligned')
    # The shop assembles 買う / 売る and 買いに来た / 売りに来た from shared
    # cached cells. Use explicit Chinese label templates after the real reopen
    # showed that the old 買う template combined 买 with the new 卖 cell.
    assert b[0x5A60E:0x5A616]==bytes.fromhex('03 06 02 22 02 4e 02 ff')
    assert b[0x5A616:0x5A61E]==bytes.fromhex('03 06 02 1a 02 4a 02 ff')
    assert b[0x5A61E:0x5A62C]==bytes.fromhex('03 08 05 22 02 26 02 2a 02 2e 02 32 02 ff')
    assert b[0x5A62C:0x5A63A]==bytes.fromhex('03 06 05 1a 02 1e 02 2a 02 2e 02 32 02 ff')
    # Actual Buy enters A616 and A62C; Sell enters A60E and A61E.
    # The cached base is 021A: 买=021A, 卖=024A, 出=024E.
    put(0x5A616,bytes.fromhex('03 06 02 1a 02 00 00 ff'),'shop Buy label uses 买 and an empty tile')
    put(0x5A60E,bytes.fromhex('03 06 02 4a 02 4e 02 ff'),'shop Sell label uses 卖出 in that order')
    put(0x5A62C,bytes.fromhex('03 06 05 1a 02 00 00 00 00 00 00 00 00 ff'),'shop Buy option Chinese label, original five-cell width')
    # The battle counter must treat native46 as a two-byte glyph as the fixed
    # menu/font loader already does. Preserve both original return continuations.
    from build_font_renderer_hook import branch_code
    classifier=branch_code(['c9 10',(None,0x90,'single'),'c9 17',(None,0x90,'double'),'c9 18',(None,0xf0,'double'),'c9 19',(None,0xf0,'double'),'c9 20',(None,0x90,'single'),'c9 24',(None,0x90,'double'),'c9 25',(None,0xf0,'double'),'c9 2a',(None,0xf0,'double'),'c9 46',(None,0xf0,'double'),('label','single'),'5c df b5 fe',('label','double'),'5c de b5 fe'])
    assert len(classifier)<=72 and b[0x7FA0B8:0x7FA100][40:]==bytes(32)
    put(0x7FA0B8,classifier,'bounded battle count native46 classification')
    # Full strings resolve from the inherent-name bank as well as the existing
    # FD names. Keep original wrappers and their parameter/stack restoration.
    assert len(long_names)==2
    entries=[]
    for x in long_names:
        ptr=int(x['source'][2:],16);target=int(x['target'],16)
        entries.append(ptr.to_bytes(2,'little')+(target&65535).to_bytes(2,'little')+x['bytes'].to_bytes(2,'little')+b'\0\0')
    battle_table=b[0x7FBD00:0x7FBD70]+b''.join(entries);put(0x7FBD00,battle_table,'16 exact battle name entries')
    for at,ending in [(0x7FBC00,bytes.fromhex('c2 30 7a fa 68 28 6b')),(0x7FB800,bytes.fromhex('c2 30 7a fa 68 28 a5 ac a6 aa 6b'))]:
        end=b.find(ending,at,at+256)+len(ending);assert end>at
        helper=b[at:end];assert bytes.fromhex('c9 fd d0 2c')in helper
        helper=helper.replace(bytes.fromhex('c9 fd d0 2c'),bytes.fromhex('c9 fd f0 04 c9 5f d0 2c'),1).replace(bytes.fromhex('e0 70 00'),bytes.fromhex('e0 80 00'),1)
        assert len(helper)<256;put(at,helper,'battle full-name dispatcher includes 5F inherent bank')
    fixed_table=alloc(b[0x7FBF80:0x7FBFF8]+b''.join(entries),'17 exact fixed-menu full-name entries')
    # Relocate the actual current fixed-menu wrapper, adjusting its BRL targets
    # that cross the four-byte insertion. Instructions are decoded explicitly.
    start=0x7FEECF;ending=bytes.fromhex('7a fa 68 28 6b');end=b.find(ending,start,start+400)+len(ending)
    helper=bytearray(b[start:end]);insert=helper.index(bytes.fromhex('c9 fd d0 38'))
    pc=0;wide_m=True;wide_x=True;branches=[]
    one={0x08,0x48,0xDA,0x5A,0xC8,0xEA,0xE8,0x8A,0x18,0xAA,0x28,0x68,0x7A,0xFA,0x6B}
    two={0xA5,0x85,0xB7,0xA3,0x83,0xC5}
    while pc<len(helper):
        if pc==0xB9:
            # Formation mismatch is reached from its 16-bit comparison branch,
            # bypassing the successful match's SEP and jump-to-draw.
            assert helper[pc:pc+4]==bytes.fromhex('8a 29 f0 ff')
            wide_m=True;wide_x=True
        op=helper[pc]
        if op in [0xC2,0xE2]:
            flag=helper[pc+1];enabled=(op==0xC2)
            if flag&0x20:wide_m=enabled
            if flag&0x10:wide_x=enabled
            n=2
        elif op in one:n=1
        elif op in two:n=2
        elif op in [0xA9,0xC9,0x29,0x69]:n=3 if wide_m else 2
        elif op in [0xA0,0xA2,0xC0,0xE0]:n=3 if wide_x else 2
        elif op in [0x22,0xBF,0xDF]:n=4
        elif op==0x82:
            n=3;target=pc+3+int.from_bytes(helper[pc+1:pc+3],'little',signed=True);branches.append((pc,target,2))
        elif op in [0xD0,0xF0,0xB0,0x90,0x80]:
            n=2;target=pc+2+int.from_bytes(helper[pc+1:pc+2],'little',signed=True);branches.append((pc,target,1))
        else:raise AssertionError(('wrapper opcode',hex(pc),hex(op)))
        pc+=n
    for pc,target,n in branches:
        if pc==insert+2:continue
        if pc<insert and target>=insert+4:helper[pc+1:pc+1+n]=(target-(pc+n+1)+4).to_bytes(n,'little',signed=True)
        elif pc>=insert+4 and target<insert:helper[pc+1:pc+1+n]=(target-(pc+n+1)-4).to_bytes(n,'little',signed=True)
    helper[insert:insert+4]=bytes.fromhex('c9 fd f0 04 c9 5f d0 38')
    for old,delta in [(bytes.fromhex('bf 80 bf 3f'),0),(bytes.fromhex('bf 82 bf 3f'),2),(bytes.fromhex('bf 84 bf 3f'),4)]:
        assert old in helper;helper=helper.replace(old,b'\xBF'+(fixed_table-0x400000+delta).to_bytes(3,'little'),1)
    assert bytes.fromhex('e0 78 00')in helper;helper=helper.replace(bytes.fromhex('e0 78 00'),bytes.fromhex('e0 88 00'),1)
    newhelper=alloc(helper,'fixed menu wrapper preserves old names/formations and adds inherent long names')
    put(0x5DE2D,b'\x22'+(newhelper-0x400000).to_bytes(3,'little'),'existing fixed menu wrapper target')
    # All ID, combat, icon, event-control, ROM-size and previous fix guards.
    for lo,hi in [(0x3E0F00,0x3E1D00),(0x5BAA00,0x5BBA00),(0x5B34A0,0x5B37A0),(0x5B79B0,0x5B79E0),(0x3A0000,0x3D0000),(0x7F8E00,0x7F9D19),(0x724D50,0x724D84),(0x780000,0x790000),(0x7D0000,0x7E0000)]:assert r[lo:hi]==b[lo:hi],(hex(lo),hex(hi))
    for site in rd('build/source_control_table264_20261008_05.json')['sites']:
        at=site['CPU']-0xC00000;assert r[at:at+2]==b[at:at+2]
    for x in inventory['empty_slots']:
        at=int(x['offset'],16);z=bytes.fromhex(x['raw_hex']);assert r[at:at+len(z)]==b[at:at+len(z)],x
    assert r[0x7FFE00:0x7FFFF0]==bytes(496)
    for at in [0xFFDC,0x40FFDC]:put(at,bytes.fromhex('ff ff 00 00'),'checksum normalization')
    checksum=sum(r)&65535
    for at in [0xFFDC,0x40FFDC]:r[at:at+4]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    assert len(r)==len(b)==0x800000 and sum(r)&65535==checksum
    assert all(allow[i]for i,(u,v)in enumerate(zip(b,r))if u!=v)
    for x in writes:
        if x['reason']=='checksum normalization':continue
        at=int(x['offset'],16);assert r[at:at+x['bytes']]==bytes.fromhex(x['after_hex']),x['reason']
    out.write_bytes(r)
    d={'schema':'v283-user-missing-translations-build-v1','status':'STATIC_READBACK_PASS_RUNTIME_PENDING','ROM':out.relative_to(P).as_posix(),'SHA256':sha(r),'base_ROM':basefile,'base_SHA256':sha(b),'writes':writes,'applied':applied,'held_structure':held,'related_names':related,'native46_glyphs':glyphs,'remaining_audited_native46_slots':len(slots),'virtual_font_atlases_unchanged':True,'long_names':long_names,'native_menu':menu,'direct_preloads':direct,'menu_arena_start':'3DB840','menu_arena_end':f'{menu_arena:06X}','arena_end':f'{arena:06X}','fixed_name_table':f'{fixed_table:06X}','fixed_menu_helper':f'{newhelper:06X}','source_review_files_SHA256':{row['file']:sha((P/row['file']).read_bytes())for row in rows},'policy':'For the five named tables only, confirmed column first, otherwise suggestion; internal/input/icon structure preserved; known dodge-category feedback retained.','confirmed_rows':sum(bool(x['confirmed_zh'])for x in rows),'suggestion_rows':sum(not x['confirmed_zh']for x in rows),'reserved496_preserved':True,'empty_slots_preserved':len(inventory['empty_slots']),'all_gameplay_and_source_control_guards_pass':True,'formal_baseline_promoted':False}
    proof.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if auxiliary:
        tag=proof.stem.rsplit('_',1)[1]
        typed.update(ROM_SHA256=sha(r),current_test_ROM_SHA256=sha(r),source_revision='20261011_missing_'+tag)
        for x in typed['translations']:
            x['current_test_ROM_SHA256']=sha(r)
            if x.get('translation_status')=='v283_user_rule_compiled':x['compiled_ROM_SHA256']=sha(r)
        skills.update(current_test_ROM_SHA256=sha(r),source_revision='20261011_missing_'+tag)
        for group in ['techniques','spells']:
            for x in skills[group]:
                x['current_test_ROM_SHA256']=sha(r)
                if int(x.get('name_offset',x.get('source_name_offset')),16)in done:
                    x.update(compiled_ROM_SHA256=sha(r),status='已编入测试包20 待手测',compiled=True)
        items.update(current_test_ROM_SHA256=sha(r),source_revision='20261011_missing_'+tag)
        for x in items['translations']:
            x['current_test_ROM_SHA256']=sha(r)
            if x.get('previous_translation_zh_cn'):
                x.update(compiled_ROM_SHA256=sha(r),status='v283_related_name_compiled_manual_pending',encoded_single_glyph_bytes=len(enc(x['translation_zh_cn'])))
        for f,obj in [('text/translations/missing_menu_user_resolved_v283_20261011_01.json',{'schema':'user-resolved-missing-menu-v1','rows':rows,'ROM_SHA256':sha(r),'policy':d['policy'],'applied':applied,'held_structure':held}),('text/translations/typed_review_integrated_v283_20261011_01.json',typed),('text/translations/techniques_spells_category_review_v283_20261011_01.json',skills),('text/translations/item_names_user_v283_20261011_01.json',items),('qa/V283_CURRENT_SINGLE_GLYPH_MAPPING_20261011_01.json',{k:v.hex(' ').upper()for k,v in m.items()}),('qa/V283_CURRENT_FIXED_MENU_PAIRS_20261011_01.json',{k:v.hex(' ').upper()for k,v in pairs.items()})]:
            f=P/f.replace('_20261011_01.json','_20261011_'+tag+'.json');assert not f.exists();f.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:d[k]for k in ['ROM','SHA256','arena_end','menu_arena_end','remaining_audited_native46_slots']},ensure_ascii=False))
    print('Applied',len(applied),'related',len(related),'glyphs',len(glyphs),'held',len(held))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8');main()
