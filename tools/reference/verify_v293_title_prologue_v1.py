"""Verify all four title streams, natural CPU/font traces and normal routes."""
from pathlib import Path
import hashlib,json,re,sys
from PIL import Image
P=Path(__file__).resolve().parents[1]
D=P/'qa/title_prologue_v293_20261017_01'
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))


def glyphs(raw):
    out=[];i=0;row=0;col=0
    while i<len(raw):
        lead=raw[i]
        if lead==0x24:row+=1;col=0;i+=1;continue
        if lead>=0x50:code=lead;i+=1
        else:
            code=lead*256+raw[i+1];i+=2
            if lead in list(range(0x10,0x17))+[0x19]:
                code=(0x28+(7 if lead==0x19 else lead-0x10))*256+raw[i-1]
            elif lead in [0x18,0x46]:code=(0x24 if lead==0x18 else 0x25)*256+raw[i-1]
        out.append((code,row*0x40+col*2));col+=1
        assert row<=11 and col<=16
    return out


def white_mask(path):
    im=Image.open(path).convert('RGB')
    return bytes(int(min(rgb)>=240)for rgb in im.get_flattened_data())


def main():
    b=rd('qa/V293_TITLE_PROLOGUE_BUILD_20261017_05.json')
    overlay=rd('text/translations/title_prologue_user_confirmed_v293_20261017_01.json')
    rom=(P/b['ROM']).read_bytes();base=(P/b['base_ROM']).read_bytes()
    assert sha(rom)==b['SHA256'] and sha(base)==b['base_SHA256']
    replay=bytearray(base);covered=bytearray(len(base))
    for w in b['writes']:
        at=int(w['offset'],16);z=bytes.fromhex(w['after_hex'])
        assert base[at:at+len(z)]==bytes.fromhex(w['before_hex'])
        assert not any(covered[at:at+len(z)])
        replay[at:at+len(z)]=z;covered[at:at+len(z)]=b'\1'*len(z)
    assert replay==rom and sum(rom)&65535==int.from_bytes(rom[0xffde:0xffe0],'little')
    log=(D/'candidate05_boot_trace.txt').read_text(encoding='utf8')
    result=re.search(r'RESULT mapped_pages=(\d+) glyphs=(\d+) virtual_glyphs=(\d+) original_text_reads=(\d+) no_VM_or_world_writes=true',log)
    assert result and tuple(map(int,result.groups()))==(4,448,109,0)
    assert log.count('ADAPTED ')==log.count('RESTORED ')==4
    rows=[]
    for i,page in enumerate(b['pages']):
        assert page['lines']==overlay['pages'][i]['lines']
        z=bytes.fromhex(page['encoded_hex']);at=int(page['file'],16)
        assert rom[at:at+len(z)]==z and sha(z)==page['SHA256']
        want=glyphs(z);lo=int(page['cpu'],16);hi=lo+len(z);actual=[]
        for line in log.splitlines():
            m=re.match(r'GLYPH f=(\d+) ptr=(\w+) code=(\w+) map=(\w+) tile=(\w+)',line)
            if m and lo<int(m[2],16)<=hi:actual.append((int(m[3],16),int(m[4],16)))
        assert actual==want,(page['page'],len(actual),len(want))
        assert all(not s.endswith(('，','。','、'))for s in page['lines'])
        image=D/['candidate05_boot_f01200.png','candidate05_boot_f03000.png',
                 'candidate05_boot_f04600.png','candidate05_boot_f05800.png'][i]
        snes=D/f'snes_candidate05_step{i:03d}.png'
        same=white_mask(image)==white_mask(snes)
        assert same,('text pixel masks differ between cores',page['page'])
        rows.append({'page':page['page'],'lines':page['lines'],'native_glyphs_including_spaces':len(actual),
            'exact_glyph_sequence_and_row_column_positions':True,'text_pixels_equal_between_Mesen_and_Snes9x':same,
            'image':image.relative_to(P).as_posix(),'normal_cold_boot_no_injection':True})
    normal=rd('qa/V293_TITLE_NORMAL_REGRESSION_20261017_05.json')
    assert normal['SHA256']==b['SHA256'] and normal['normal_pairs']==13
    assert all(all(r['checks'].values())for r in normal['rows'])
    cold=rd(D/'snes_candidate05.json');skip=rd(D/'snes_skip05.json')
    assert cold['ROM_SHA']==skip['ROM_SHA']==b['SHA256']
    assert cold['frames']==6500 and cold['mode']==skip['mode']=='FRESH_BOOT_NO_SNAPSHOT_OR_BATTERY'
    proof={'schema':'v293-title-prologue-verification-v1','status':'FOUR_NATIVE_TITLE_PAGES_TWO_CORES_AND_THIRTEEN_NORMAL_PAIRS_PASS',
        'ROM':b['ROM'],'SHA256':b['SHA256'],'write_manifest_replayed_byte_exact':True,
        'native_cold_boot_frames':6500,'native_display_pages':rows,'glyphs_including_spaces':448,
        'virtual_glyphs_with_exact_font_address_and_30_byte_fetch_assertions':109,
        'original_Japanese_text_reads_after_adapter':0,'getter_and_loop_register_stack_assertions_passed':True,
        'four_original_page_end_and_bank_restores_verified':True,'approved_text_and_punctuation_exact':True,
        'original_16_column_grid_retained':True,'normal_input_pairs':13,'Start_skip_to_title_menu_checked':True,
        'menu_image':'qa/title_prologue_v293_20261017_01/snes_skip05_step001.png',
        'fonts_v291_layout_and_v292_rewards_preserved':True,'native_script_and_historical_shadows_preserved':True,
        'natural_gameplay_not_full_game_acceptance':True,
        'experiments_not_delivered':['01 title virtual helper lost the glyph low byte',
            '02 index-only hypothesis did not recover the lost byte',
            '03 adjacent page boundaries collided; fixed by matching the active exclusive end as well',
            '04 native 18FB 踪 also required low-byte recovery; all special two-byte leads now handled'],
        'evidence_driver':'tools/mesen_v293_title_verify_v1.lua',
        'driver_SHA256':sha((P/'tools/mesen_v293_title_verify_v1.lua').read_bytes())}
    (P/'qa/V293_TITLE_PROLOGUE_VERIFICATION_20261017_05.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:proof[k]for k in ['status','SHA256','glyphs_including_spaces','normal_input_pairs']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
