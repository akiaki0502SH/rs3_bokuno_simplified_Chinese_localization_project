"""Reorder two native result displays without changing reward/skill processing."""
from pathlib import Path
import argparse,hashlib,json,sys
from build_font_renderer_hook import branch_code
P=Path(__file__).resolve().parents[1]
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',default='roms/work/bokuno_cn_candidate_v10bi289_postbattle_word_order_20261013_01.smc')
    parser.add_argument('--report',default='qa/V289_POSTBATTLE_WORD_ORDER_BUILD_20261013_01.json')
    args=parser.parse_args();out=(P/args.rom).resolve();proof=(P/args.report).resolve()
    assert out.is_relative_to(P)and proof.is_relative_to(P)and not out.exists()and not proof.exists()
    m=rd('text/translations/translation_sources_before_v289_20261013_01.json')
    assert m['build_revision']=='v288_font_geometry01'
    b=(P/m['latest_test_ROM']['file']).read_bytes()
    assert sha(b)==m['latest_test_ROM']['SHA256']=='BCE976F8172B5D6F489E0311F44AB8CE2FE644CD14236813EE478DBE22F0D35C'
    s=(P/'../roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
    r=bytearray(b);allow=bytearray(len(b));writes=[]
    def put(at,z,why,expected=None):
        if expected is not None:assert b[at:at+len(z)]==expected,(hex(at),why)
        else:assert b[at:at+len(z)]==s[at:at+len(z)]==bytes(len(z)),(hex(at),why)
        r[at:at+len(z)]=z;allow[at:at+len(z)]=b'\1'*len(z)
        writes.append({'offset':f'{at:06X}','bytes':len(z),'reason':why,
            'before_hex':b[at:at+len(z)].hex(' ').upper(),'after_hex':z.hex(' ').upper()})
    mp={c:bytes.fromhex(z)for c,z in rd(m['latest_font_mapping']).items()}
    enc=lambda text:b''.join(mp[c]for c in text)
    data=enc('习得奥义识破奥义')
    assert len(data)==16 and all(len(mp[c])==2 for c in '习得奥义识破')
    # Existing 7FF27C..7FF7FF gap is zero in both original and current ROM.
    # 7FF280 is reserved for a diagnostic-only frame wait, outside this module.
    ui_get=b[0x20707:0x20726]+b'\x6b'
    assert ui_get.hex(' ')=='a5 65 c2 20 29 ff 00 0a aa bf 00 98 fd 18 69 00 9a 85 aa e2 20 a9 fd 85 ac a5 1e 09 10 85 1e 6b'
    width=bytes.fromhex('22 10 07 5e 1a 1a 6b')
    # Original caller adds one: old name+1 -> new name+3 (习得 + name + 的).
    mastery=branch_code([
        'a6 aa da a5 ac 48 a5 4b 48',              # preserve name pointer/byte limit
        'a9 04 85 4b a2 00 f6 86 aa a9 3f 85 ac',
        'a5 1e 29 ef 85 1e 22 da aa fe',          # 习得, fixed literal
        '68 85 4b 68 85 ac fa 86 aa',
        'a5 7e 18 69 04 85 7e',                  # two full glyphs, four tile cells
        '22 da aa fe 22 85 b5 fe 0a 18 65 7e 85 7e',
        'a9 2b 85 65 22 00 f5 3f 22 da aa fe',   # existing 的, appended to name
        'a5 7a 85 7e e6 7f e6 7f',               # second line
        'a5 4b 48 22 40 07 5e',                 # retain original 見切 / regular decision
        (None,0xb0,'evasion'),
        'a2 04 f6 86 aa a9 04 85 4b a9 1d 85 65',
        (None,0x80,'suffix'),
        ('label','evasion'),
        'a2 08 f6 86 aa a9 08 85 4b a9 12 85 65',
        ('label','suffix'),
        'a9 3f 85 ac a5 1e 29 ef 85 1e 22 da aa fe',
        '68 85 4b 5c 4a d1 c2',
    ])
    item=branch_code([
        'a5 1c 89 02',(None,0xd0,'destroyed'),
        '68 68 85 65',                           # pop old 29 and 13; use 13 first
        'a6 aa da a5 ac 48 a5 4b 48',
        '22 00 f5 3f 22 da aa fe',                # 获得了
        '68 85 4b 68 85 ac fa 86 aa',
        'a5 1e 29 ef 85 1e',
        'a5 7a 85 7e e6 7f e6 7f',
        '22 da aa fe 5c ea ce c2',                # original dynamic item on second line
        ('label','destroyed'),
        '22 da aa fe 5c c4 ce c2',                # exact original destruction path
    ])
    assert len(mastery)<=0x100 and len(item)<=0x100
    put(0x7ff300,mastery,'mastery display: 习得 + actual name + 的 / 奥义, original evasion branch')
    put(0x7ff400,item,'item acquired display: 获得了 / actual name; destruction replays old path')
    put(0x7ff500,ui_get,'bank-safe clone of C20707 indexed UI pointer getter')
    put(0x7ff540,width,'display-only frame width accounts for two-glyph prefix')
    put(0x7ff600,data,'fixed literals: 习得, 奥义, 识破奥义')
    put(0x2d0e9,bytes.fromhex('22 40 f5 3f'),'mastery name-length wrapper',bytes.fromhex('22 10 07 5e'))
    put(0x2d112,bytes.fromhex('5c 00 f3 3f'),'mastery display redirect',bytes.fromhex('22 da aa fe'))
    put(0x2cec0,bytes.fromhex('5c 00 f4 3f'),'acquisition display redirect',bytes.fromhex('22 da aa fe'))
    for at in [0xffdc,0x40ffdc]:
        r[at:at+4]=bytes.fromhex('ff ff 00 00');allow[at:at+4]=b'\1'*4
    checksum=sum(r)&65535
    for at in [0xffdc,0x40ffdc]:r[at:at+4]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    assert sum(r)&65535==checksum and len(r)==len(b)==0x800000
    assert all(allow[i]for i,(x,y)in enumerate(zip(b,r))if x!=y)
    for lo,hi in [(0x2c0000,0x2c8000),(0x608000,0x60c000),(0x780000,0x790000),
                  (0x7d0000,0x7e0000),(0x3d0000,0x3ea000),(0x5ba000,0x5bba00),
                  (0x3ea000,0x3efe00),(0x7ffe00,0x7ffff0)]:assert r[lo:hi]==b[lo:hi]
    out.write_bytes(r)
    report={'schema':'v289-postbattle-word-order-v1','status':'STATIC_PASS_RUNTIME_PENDING',
        'ROM':out.relative_to(P).as_posix(),'SHA256':sha(r),'base_ROM':m['latest_test_ROM']['file'],
        'base_SHA256':sha(b),'writes':writes,'helper_range':['7FF300','7FF610'],
        'mastery_rows':['习得{ACTUAL_SKILL_NAME}的','奥义'],
        'evasion_rows':['习得{ACTUAL_SKILL_NAME}的','识破奥义'],
        'item_rows':['获得了','{ACTUAL_ITEM_NAME}'],
        'root_cause':{'word_order':'Native C2CE72/C2D0D4 draws the dynamic name before suffix templates.',
            'unexpected_把':'indexed_battle_ui_strings_3d9a00_029 translated standalone Japanese を to 把.',
            'genitive':'indexed_battle_ui_strings_3d9a00_02B translated の to 的; the old caller prepended the name.'},
        'all_UI_pool_names_fonts_and_gameplay_processing_preserved':True,
        'existing_UI29_other_consumers_preserved':True,'destruction_branch_preserved':True,
        'formal_baseline_promoted':False}
    proof.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k]for k in ['ROM','SHA256','helper_range']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
