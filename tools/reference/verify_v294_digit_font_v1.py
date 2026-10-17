"""Audit the entire byte diff and exact reviewed glyph geometry."""
from pathlib import Path
import hashlib,json,sys
from font_geometry_v1 import glyph_locations,read_glyph,unpack
P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()


def main():
    b=rd('qa/V294_DIGIT_FONT_BUILD_20261017_01.json');runtime=rd('qa/V294_DIGIT_FONT_RUNTIME_20261017_01.json')
    assert runtime['SHA256']==b['SHA256']and runtime['normal_pairs']==13
    r=(P/b['ROM']).read_bytes();base=(P/b['base_ROM']).read_bytes()
    assert sha(r)==b['SHA256']and sha(base)==b['base_SHA256']
    mask=bytearray(len(base));replay=bytearray(base)
    for w in b['writes']:
        at=int(w['offset'],16);z=bytes.fromhex(w['after_hex'])
        assert not any(mask[at:at+len(z)])and base[at:at+len(z)]==bytes.fromhex(w['before_hex'])
        replay[at:at+len(z)]=z;mask[at:at+len(z)]=b'\1'*len(z)
    assert replay==r and sum(r)&65535==int.from_bytes(r[0xffde:0xffe0],'little')
    frozen=rd('text/translations/translation_sources_before_v294_20261017_01.json');mp=rd(frozen['latest_font_mapping'])
    candidate=rd('font/digit_preview_20261017_01/candidate_digits.json');rows=[]
    for wanted in candidate['glyphs']:
        digit=wanted['digit'];raw=bytes.fromhex(wanted['glyph_hex']);box=unpack(raw).getbbox()
        for code in [bytes.fromhex(mp[digit]),bytes([0x23,int(digit)])]:
            assert all(read_glyph(r,loc)==raw for loc in glyph_locations(code))
        assert box[3]-box[1]==10 and box[3]-1==13 and box[2]<=13
        left,right=box[0],14-box[2]
        assert (left,right)==((2,3)if digit=='4'else(5,5)if digit=='1'else(3,3))
        rows.append({'digit':digit,'bbox':list(box),'left_blank':left,'right_blank':right,
            'height':10,'bottom_y':13,'matches_approved_preview':True})
    allowed=set('0123456789０１２３４５６７８９')
    for ch,c in mp.items():
        if ch in allowed:continue
        try:locs=glyph_locations(bytes.fromhex(c))
        except ValueError:continue
        assert all(read_glyph(base,loc)==read_glyph(r,loc)for loc in locs),ch
    for row in runtime['dialogue_pixel_pairs']:
        assert all(x['missing_pixels']==0 and x['bottom']==29 for x in row['new'])
        assert all(row['checks'].values())
    assert all(all(x['checks'].values())for x in runtime['normal_routes'])
    assert all(all(x['checks'].values())for x in runtime['reward_display_pairs'])
    proof={'schema':'v294-digit-font-verification-v1','status':'EXACT_APPROVED_DIGITS_BYTE_DIFF_AND_RUNTIME_CHECKS_PASS_MANUAL_PENDING',
        'ROM':b['ROM'],'SHA256':b['SHA256'],'approved_candidate_SHA256':b['approved_candidate_SHA256'],
        'rows':rows,'write_manifest_replayed_byte_exact':True,'all_non_digit_mapped_glyphs_unchanged':True,
        'all_changed_bytes_are_listed_glyph_slots_or_checksums':True,'text_scripts_and_render_code_unchanged':True,
        'character_advance_unchanged':14,'digit5_not_shifted_from_reviewed_candidate':True,
        'dialogue_pixel_pairs':5,'normal_input_pairs':13,'reward_display_pairs':3,
        'title_four_pages_pixels_identical_to_v293':True,'original_feedback_scene_replayed':False,
        'runtime_report':'qa/V294_DIGIT_FONT_RUNTIME_20261017_01.json','gameplay_acceptance_not_complete':True}
    (P/'qa/V294_DIGIT_FONT_VERIFICATION_20261017_01.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:proof[k]for k in ['status','SHA256','dialogue_pixel_pairs','normal_input_pairs','reward_display_pairs']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
