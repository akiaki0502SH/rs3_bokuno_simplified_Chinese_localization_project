"""Apply the reviewed digit bitmaps without changing text, layout or code."""
from pathlib import Path
import argparse,hashlib,json,sys
from font_geometry_v1 import glyph_locations,read_glyph,unpack
P=Path(__file__).resolve().parents[1]
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',default='roms/work/bokuno_cn_candidate_v10bn294_digit_font_20261017_01.smc')
    p.add_argument('--report',default='qa/V294_DIGIT_FONT_BUILD_20261017_01.json')
    a=p.parse_args();out=(P/a.rom).resolve();proof=(P/a.report).resolve()
    assert out.is_relative_to(P/'roms/work')and proof.is_relative_to(P/'qa')and not out.exists()and not proof.exists()
    frozen=rd('text/translations/translation_sources_before_v294_20261017_01.json')
    assert frozen['build_revision']=='v293_title_prologue01'
    base=(P/frozen['latest_test_ROM']['file']).read_bytes()
    assert sha(base)==frozen['latest_test_ROM']['SHA256']=='F1FCD42B314BE37BA2A7D9F7EF233A1CA11E6D1333EB2F721DD8B81676BF2129'
    candidate_path=P/'font/digit_preview_20261017_01/candidate_digits.json'
    preview=rd('qa/DIGIT_FONT_SPACING_REVIEW_20261017_01.json')
    assert sha(candidate_path.read_bytes())==preview['candidate_SHA256']
    candidate=rd(candidate_path);mp=rd(frozen['latest_font_mapping'])
    r=bytearray(base);allow=bytearray(len(base));writes=[];changed=set();rows=[]
    for row in candidate['glyphs']:
        digit=row['digit'];new=bytes.fromhex(row['glyph_hex']);box=unpack(new).getbbox()
        assert list(box)==row['candidate_bbox']and box[3]==14 and box[3]-box[1]==10 and box[2]<=13
        codes={bytes.fromhex(mp[digit]),bytes([0x23,int(digit)])}
        placements=[]
        for code in sorted(codes):
            for loc in glyph_locations(code):
                if loc in changed:continue
                changed.add(loc);old=read_glyph(base,loc)
                for at,z in zip(loc,[new[:16],new[16:]]):
                    assert not any(allow[at:at+16]);r[at:at+16]=z;allow[at:at+16]=b'\1'*16
                    writes.append({'offset':f'{at:06X}','bytes':16,'digit':digit,'code':code.hex(' ').upper(),
                        'before_hex':base[at:at+16].hex(' ').upper(),'after_hex':z.hex(' ').upper()})
                placements.append({'code':code.hex(' ').upper(),'upper':f'{loc[0]:06X}','lower':f'{loc[1]:06X}',
                    'before_bbox':list(unpack(old).getbbox()),'after_bbox':list(box)})
        rows.append({'digit':digit,'glyph_hex':new.hex(' ').upper(),'glyph_SHA256':sha(new),
            'ink_height':10,'bottom_y':13,'left_blank':box[0],'right_blank':14-box[2],'placements':placements})
    # No mapped non-numeric glyph may alias a changed slot.
    numeric=set('0123456789０１２３４５６７８９')
    for atom,code in mp.items():
        if atom in numeric:continue
        try:locs=glyph_locations(bytes.fromhex(code))
        except ValueError:continue
        assert not any(x in changed for x in locs),('non-digit slot alias',atom,code)
        assert all(read_glyph(base,x)==read_glyph(r,x)for x in locs)
    for h in [0xffdc,0x40ffdc]:r[h:h+4]=bytes.fromhex('ff ff 00 00')
    checksum=sum(r)&65535
    for h in [0xffdc,0x40ffdc]:
        z=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
        r[h:h+4]=z;allow[h:h+4]=b'\1'*4
        writes.append({'offset':f'{h:06X}','bytes':4,'digit':None,'code':None,
            'before_hex':base[h:h+4].hex(' ').upper(),'after_hex':z.hex(' ').upper()})
    assert len(r)==0x800000 and sum(r)&65535==checksum
    assert all(allow[i]for i,(x,y)in enumerate(zip(base,r))if x!=y)
    assert r[0x3ff800:0x3ffd00]==base[0x3ff800:0x3ffd00]
    assert r[0x7ff280:0x7ffff0]==base[0x7ff280:0x7ffff0]
    assert r[0x3a0000:0x3d0000]==base[0x3a0000:0x3d0000]
    report={'schema':'v294-reviewed-digit-font-v1','status':'STATIC_PASS_RUNTIME_PENDING',
        'ROM':out.relative_to(P).as_posix(),'SHA256':sha(r),'base_ROM':frozen['latest_test_ROM']['file'],
        'base_SHA256':sha(base),'approved_candidate':candidate_path.relative_to(P).as_posix(),
        'approved_candidate_SHA256':sha(candidate_path.read_bytes()),'rows':rows,'writes':writes,
        'font_locations_changed':len(changed),'all_non_digit_mapped_glyphs_unchanged':True,
        'text_bytes_control_code_and_advance_unchanged':True,'digit5_horizontal_shift_from_preview':0,
        'v293_title_code_and_text_preserved':True,'v292_reward_code_preserved':True,
        'v291_layout_preserved':True,'reserved496_preserved':True}
    out.write_bytes(r);proof.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:report[k]for k in ['ROM','SHA256','font_locations_changed','status']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
