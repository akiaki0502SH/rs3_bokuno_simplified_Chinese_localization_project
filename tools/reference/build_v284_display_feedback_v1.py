"""Apply the user's display reports to package20, with bounded writes."""
from pathlib import Path
import copy,hashlib,json,sys
from PIL import Image,ImageDraw
from dry_run_encoding_plan import encode
from build_font_payloads import encode_pixels,read_interleaved
from build_v283_missing_translations_v1 import atoms

P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()

def unpack(z):
    im=Image.new('1',(16,16),0)
    for y in range(16):
        for x in range(16):
            if z[(y//8*2+x//8)*8+y%8]>>(7-x%8)&1:im.putpixel((x,y),1)
    return im

def wrap13(text):
    out=[]
    while len(text)>13:
        cut=13
        # Prefer punctuation only when the rest still fits the second line.
        points=[i+1 for i,c in enumerate(text[:13])if c in '，、；：。'and i+1>=6 and len(text)-(i+1)<=13]
        if points:cut=points[-1]
        if text[cut-1]in 'HL' and text[cut]=='P':cut-=1
        out.append(text[:cut]);text=text[cut:]
    out.append(text)
    assert len(out)<=2 and all(len(x)<=13 for x in out),(out,len(''.join(out)))
    return out

def main():
    out=P/(sys.argv[1]if len(sys.argv)>1 else 'roms/work/bokuno_cn_candidate_v10bd284_display_feedback_20261011_01.smc')
    pf=P/(sys.argv[2]if len(sys.argv)>2 else 'qa/V284_DISPLAY_FEEDBACK_BUILD_20261011_01.json')
    independent=len(sys.argv)>3 and sys.argv[3]=='independent'
    assert out.is_relative_to(P)and pf.is_relative_to(P)and not out.exists()and not pf.exists()
    manifest=rd('text/translations/translation_sources_before_v284_20261011_01.json')
    assert manifest['build_revision']=='v283_missing_translations04'
    basefile=manifest['latest_test_ROM']['file'];b=(P/basefile).read_bytes();assert sha(b)=='0BF517A76215AD557722CBC4B1D423F2F722766DEDCC14EFBB8325C9386FDBC2'
    r=bytearray(b);allow=bytearray(len(b));writes=[]
    def put(at,z,why,id=None):
        assert 0<=at<=len(b)-len(z)
        r[at:at+len(z)]=z;allow[at:at+len(z)]=b'\1'*len(z)
        writes.append({'offset':f'{at:06X}','bytes':len(z),'reason':why,'id':id,'before_hex':b[at:at+len(z)].hex(' ').upper(),'after_hex':z.hex(' ').upper()})
    m={k:bytes.fromhex(v)for k,v in rd(manifest['latest_font_mapping']).items()}
    def enc(t):
        z,miss,err=encode(t,m,battle=False);assert not miss and not err,(t,miss,err);return z
    old=rd('qa/V283_MISSING_TRANSLATIONS_BUILD_20261011_04.json')
    descriptions=[];changed=[]
    explicit={
      'T045':['沿地面疾驰的冲击波攻击一列','敌人。'],
      'T052':['如舞蹈般穿行敌阵的华丽强力','招式。'],
      'T064':['劈开空间，将敌人打入','次元裂隙。'],
      'T114':['旋转长枪，斩伤触及枪身的','敌人，施展反击。'],
    }
    for x in old['applied']:
        if x['kind']not in 'TMI':continue
        text=x['zh'];source_text=text
        if x['id']=='M203':
            assert text=='恢复我方单体的HP并解除异常状态，熟练后还可解除石化。'
            text='恢复我方单体HP并解除异常状态，熟练后还可解除石化。'
        lines=explicit.get(x['id'],wrap13(text))
        assert ''.join(lines)==text and len(lines)<=2 and all(len(s)<=13 for s in lines)
        rendered=[]
        for line in lines:
            # Local full-size number glyphs; leave generic ASCII digit mapping intact.
            if x['id']in ['I001','I002','I003']:
                line=''.join(chr(ord(c)+0xFEE0)if c in '123'else c for c in line)
            rendered.append(line)
        payload=b'\x50'.join(enc(s)for s in rendered);assert len(payload)<=63
        at=int(x['offset'],16);z=bytes([len(payload)])+payload+bytes(63-len(payload))
        assert len(z)==64
        if b[at:at+64]!=z:
            put(at,z,'description reflow inside 13-cell blue region',x['id']);changed.append(x['id'])
        descriptions.append({'id':x['id'],'kind':x['kind'],'offset':x['offset'],'source_translation':source_text,'display_text':text,'display_lines':lines,'rendered_lines':rendered,'payload_hex':payload.hex(' ').upper(),'bytes':len(payload),'width_cells':13,'source_semantics_preserved':True})
    assert len(descriptions)==431
    # Restore the event label's deliberate four-cell 事 / blank / 件 / blank layout.
    event=next(x for x in old['native_menu']if x['id']=='U047');event_at=int(event['offset'],16)
    assert b[event_at:event_at+6]==enc('事件')+b'\x50\x50'
    event_payload=enc('事')+b'\x50'+enc('件')+b'\x50';assert len(event_payload)==6 and len(atoms(event_payload))==4
    put(event_at,event_payload,'event label 事 件 spacing restored','U047')
    # The shop uses a shared glyph cache. Its long sell-option template still
    # selected the literal pooled phrase 来出售 instead of the approved 卖出.
    shop_at=0x5A61E
    shop_before=bytes.fromhex('03 08 05 22 02 26 02 2A 02 2E 02 32 02 FF')
    shop_after=bytes.fromhex('03 08 05 4A 02 4E 02 1E 02 1E 02 1E 02 FF')
    assert b[shop_at:shop_at+len(shop_before)]==shop_before
    put(shop_at,shop_after,'shop sell option uses approved 卖出 cache cells and three blanks','U064')
    # Tile0000 contains map graphics; use the shop's real cached blank at021E.
    assert b[0x5A616:0x5A61E]==bytes.fromhex('03 06 02 1A 02 00 00 FF')
    put(0x5A616,bytes.fromhex('03 06 02 1A 02 1E 02 FF'),'shop Buy heading uses real cached blank','U064')
    assert b[0x5A62C:0x5A63A]==bytes.fromhex('03 06 05 1A 02 00 00 00 00 00 00 00 00 FF')
    put(0x5A62C,bytes.fromhex('03 06 05 1A 02 1E 02 1E 02 1E 02 1E 02 FF'),'shop Buy option uses four real cached blanks','U064')
    # Initial unselected options also draw directly from the pooled field.
    # Synchronize it without changing its six-byte/five-cell budget.
    assert b[0x3DBA9F:0x3DBAA5]==bytes.fromhex('F5 F1 14 4A 50 50')
    shop_payload=enc('卖出')+b'\x50'*3
    assert len(shop_payload)==6 and len(atoms(shop_payload))==5
    put(0x3DBA9F,shop_payload,'shop initial sell-option pooled field synchronized','U064')
    shop={'offset':f'{shop_at:06X}','pooled_field_offset':'3DBA9F','before_text':'来出售','display_text':'卖出','cache_cells':['024A','024E','021E','021E','021E'],'template_control_and_length_unchanged':True,'buy_label_preserved':'买','real_blank_tile':'021E','initial_unselected_option_synced':True}
    # This operation label is also present in the active 38-cell preload copy.
    # Its obsolete source slot was translated in v283 but the live copy was missed.
    source=(P/'../roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
    position=len(atoms(source[0x3DF8FF:0x3DF933]));cursor=0x3DFE00;cells=[]
    for _ in range(38):
        n=2 if b[cursor]in set(range(0x10,0x17))|{0x18,0x19,0x20,0x21,0x22,0x23,0x46}else 1
        cells.append(b[cursor:cursor+n]);cursor+=n
    assert b''.join(cells[position:position+4])==source[0x3DF933:0x3DF939]
    cells[position:position+4]=atoms(enc('封印'))+[b'\x50',b'\x50']
    preload=b''.join(cells);assert len(cells)==38 and len(preload)<=96
    put(0x3DFE00,preload,'live 38-cell seal-operation label translated','U100')
    # Remove only the music-preview integration sites in the environment menu.
    # The stock function has the same surrounding native instructions, and its
    # stereo flag F545 and cursor-speed flag F544 remain the actual controllers.
    stock=(P/'../roms/source/rs3_v1.1_original_analysis.sfc').read_bytes()
    environment=[]
    spans=[(0x57D6A,0x57D7F),(0x57DA2,0x57DA3),(0x57DAB,0x57DB0),(0x57E19,0x57E1F),(0x57E25,0x57E29)]
    assert b[0x57D6A:0x57D6F]==bytes.fromhex('22 09 19 68 EA')
    assert b[0x57DA2]==0x8D and stock[0x57DA2]==0x9C
    assert b[0x57DAB:0x57DB0]==bytes.fromhex('5C 60 18 68 EA')
    assert b[0x57E19:0x57E1F]==bytes.fromhex('22 00 18 68 EA EA')
    assert b[0x57E25:0x57E29]==bytes.fromhex('5C 20 18 68')
    assert stock[0x57DAB:0x57DB0]==bytes.fromhex('AD 83 3D D0 3B')
    assert stock[0x57E19:0x57E1F]==bytes.fromhex('A9 01 38 ED 83 3D')
    assert stock[0x57E25:0x57E29]==bytes.fromhex('A5 06 D0 03')
    for lo,hi in spans:
        put(lo,stock[lo:hi],'user requested two-option environment menu without music preview')
        environment.append({'start':f'{lo:06X}','end':f'{hi:06X}','stock_reference_hex':stock[lo:hi].hex(' ').upper()})
    # The mod also redraws the music tiles whenever the speed-row draw runs.
    # Keep the original CCBA call and remove only its extra music-tile JSL.
    assert b[0x5FBE8:0x5FBF0]==bytes.fromhex('20 BA CC 22 B0 19 68 60')
    put(0x5FBEB,b'\xEA'*4,'remove automatic music-tile overlay from native draw wrapper')
    # The previous music row survives in old snapshots' tilemaps. Clear those
    # two rows through the native drawing queue and flush before drawing Sound.
    bridge_at=0x52B00;bridge=bytes.fromhex('20 4E D8 20 8A FC 6B')
    assert b[bridge_at:bridge_at+len(bridge)]==source[bridge_at:bridge_at+len(bridge)]==b'\xff'*len(bridge)
    put(bridge_at,bridge,'same-bank native draw and frame-flush bridge')
    helper=bytearray(bytes.fromhex('08 C2 30 48 DA 5A'))
    parameters=[0x06,0x08,0x0A,0x0C,0x0E,0x10]
    for dp in parameters:helper+=bytes([0xA5,dp,0x48])
    for dp,value in [(0x06,8),(0x08,13),(0x0A,0x5000),(0x0C,16),(0x0E,0),(0x10,0)]:helper+=b'\xA9'+value.to_bytes(2,'little')+bytes([0x85,dp])
    helper+=b'\x22'+(bridge_at+0xC00000).to_bytes(3,'little')+bytes.fromhex('C2 30')
    for dp in reversed(parameters):helper+=bytes([0x68,0x85,dp])
    helper+=bytes.fromhex('7A FA 68 28 A9 0E 85 06 6B')
    clear_at=int(old['arena_end'],16);assert clear_at+len(helper)<0x7FFE00 and b[clear_at:clear_at+len(helper)]==bytes(len(helper))
    put(clear_at,helper,'environment old music tilemap cleanup and original Sound X coordinate')
    put(0x57D6A,b'\x22'+(clear_at-0x400000).to_bytes(3,'little'),'environment native Sound setup through bounded cleanup')
    restored=next(x for x in writes if x['offset']=='057D6A' and x['bytes']==21)
    restored['after_hex']=r[0x57D6A:0x57D7F].hex(' ').upper()
    restored['bounded_setup_hook_added']=True
    assert r[0x57D6E:0x57D7F]==stock[0x57D6E:0x57D7F]
    # Keep the character's familiar left radical; enlarge its right 日 component.
    code=m['阳'];assert code==bytes.fromhex('11 C0')
    slot=256+code[1];off=slot//8*256+slot%8*16
    before=b[0x780000+off:0x780010+off]+b[0x780080+off:0x780090+off]
    im=unpack(before)
    for y in range(16):
        for x in range(7,16):im.putpixel((x,y),0)
    draw=ImageDraw.Draw(im);draw.rectangle((7,2,12,13),outline=1);draw.line((7,7,12,7),fill=1)
    glyph=encode_pixels(im);assert glyph!=before and len(glyph)==32
    assert all(im.getpixel((x,y))==0 for x in range(13,16)for y in range(16))
    for base in [0x780000,0x7D0000]:
        assert b[base+off:base+off+16]+b[base+off+128:base+off+144]==before
        put(base+off,glyph[:16],'阳 glyph right component 日 enlarged upper','阳');put(base+off+128,glyph[16:],'阳 glyph right component 日 enlarged lower','阳')
    # Existing old fixes, fonts (outside 阳), names, combat data and source VM stay.
    for lo,hi in [(0x3A0000,0x3D0000),(0x3D0000,0x3D6000),(0x3E0F00,0x3E1D00),(0x5BA000,0x5BBA00),(0x5FB000,0x5FBA00),(0x5B34A0,0x5B37A0),(0x5B79B0,0x5B79E0),(0x5F38B0,0x5F38E7),(0x7F8E00,0x7F9D19),(0x724D50,0x724D84),(0x681800,0x681A00)]:assert r[lo:hi]==b[lo:hi],(hex(lo),hex(hi))
    for site in rd('build/source_control_table264_20261008_05.json')['sites']:
        at=site['CPU']-0xC00000;assert r[at:at+2]==b[at:at+2]
    for x in rd('text/extracted/missing_menu_inventory_v282_20261011_01.json')['empty_slots']:
        at=int(x['offset'],16);z=bytes.fromhex(x['raw_hex']);assert r[at:at+len(z)]==b[at:at+len(z)]
    assert r[0x7FFE00:0x7FFFF0]==bytes(496)
    for at in [0xFFDC,0x40FFDC]:put(at,bytes.fromhex('FF FF 00 00'),'checksum normalization')
    checksum=sum(r)&65535
    for at in [0xFFDC,0x40FFDC]:r[at:at+4]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    assert len(r)==len(b)==0x800000 and sum(r)&65535==checksum
    assert all(allow[i]for i,(u,v)in enumerate(zip(b,r))if u!=v)
    for x in writes:
        if x['reason']=='checksum normalization':continue
        at=int(x['offset'],16);assert r[at:at+x['bytes']]==bytes.fromhex(x['after_hex'])
    out.write_bytes(r)
    report={'schema':'v284-display-feedback-build-v1','status':'STATIC_READBACK_PASS_RUNTIME_PENDING','ROM':out.relative_to(P).as_posix(),'SHA256':sha(r),'base_ROM':basefile,'base_SHA256':sha(b),'writes':writes,'description_layout_rows':descriptions,'changed_description_ids':changed,'changed_description_count':len(changed),'blue_box_line_limit':13,'display_wording_exception':{'M203':{'source':'恢复我方单体的HP并解除异常状态，熟练后还可解除石化。','display':'恢复我方单体HP并解除异常状态，熟练后还可解除石化。','reason':'remove one optional 的 to fit two 13-cell lines; all effects retained'}},'event_spacing':{'offset':f'{event_at:06X}','cells':4,'text':'事 件'},'environment_no_music_preview':environment,'environment_cache_cleanup':{'helper':f'{clear_at:06X}','native_bridge':f'{bridge_at:06X}','rows':[13,14],'preserved_parameters':parameters,'original_Sound_x':14},'arena_end':f'{clear_at+len(helper):06X}','user_explicitly_chose_remove_music_preview':True,'yang_glyph':{'code':code.hex(' ').upper(),'new_hex':glyph.hex(' ').upper(),'old_SHA256':sha(before),'new_SHA256':sha(glyph),'right_component_size':[6,12],'left_radical_unchanged':True},'map_difficulty_digit_encoding':'Only I001/I002/I003 use existing full-size native 23 01/02/03 glyphs; general ASCII digit mapping unchanged','live_seal_preload_synced':True,'gameplay_names_stats_and_source_controls_preserved':True,'reserved496_preserved':True,'formal_baseline_promoted':False}
    report['shop_menu']=shop
    pf.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if not independent:
        tag=pf.stem.rsplit('_',1)[1]
        f=P/('text/translations/display_feedback_v284_20261011_'+tag+'.json');assert not f.exists()
        f.write_text(json.dumps({'schema':'display-feedback-overlay-v1','base_source_manifest':'text/translations/translation_sources_before_v284_20261011_01.json','ROM_SHA256':sha(r),'description_layout_rows':descriptions,'event_spacing':report['event_spacing'],'environment_no_music_preview':True,'yang_glyph':report['yang_glyph'],'map_digit_encoding':report['map_difficulty_digit_encoding'],'reported_cases':['T045','T052','T064','T114','U047','environment','阳','I002']},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        overlay=json.loads(f.read_text(encoding='utf8'));overlay['shop_menu']=shop;overlay['reported_cases'].append('U064_shop_sell');f.write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        mapping=P/('qa/V284_CURRENT_SINGLE_GLYPH_MAPPING_20261011_'+tag+'.json');assert not mapping.exists();mapping.write_bytes((P/manifest['latest_font_mapping']).read_bytes())
    print(json.dumps({k:report[k]for k in ['ROM','SHA256','changed_description_count','blue_box_line_limit']},ensure_ascii=False))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8');main()
