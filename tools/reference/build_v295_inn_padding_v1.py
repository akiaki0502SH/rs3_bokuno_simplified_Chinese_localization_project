"""Trim leading quote padding at the two native inn price commands only."""
from pathlib import Path
import argparse,hashlib,json,sys
from build_font_renderer_hook import branch_code
P=Path(__file__).resolve().parents[1]
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',default='roms/work/bokuno_cn_candidate_v10bo295_inn_padding_20261017_01.smc')
    parser.add_argument('--report',default='qa/V295_INN_PADDING_BUILD_20261017_01.json')
    a=parser.parse_args();out=(P/a.rom).resolve();report=(P/a.report).resolve()
    assert out.is_relative_to(P/'roms/work')and report.is_relative_to(P/'qa')and not out.exists()and not report.exists()
    m=rd('text/translations/translation_sources_before_v295_20261017_01.json')
    assert m['build_revision']=='v294_digit_font01'
    base=(P/m['latest_test_ROM']['file']).read_bytes()
    assert sha(base)==m['latest_test_ROM']['SHA256']=='6453C242A6876EFDE220FA72D2107B93DD699366E63189B8293CA0D358D48DEF'
    source=(P.parent/'roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
    for at in [0x3c3954,0x3c4200]:assert base[at:at+3]==source[at:at+3]==bytes.fromhex('3d ef 00')
    assert base[0x33c5:0x33cb]==source[0x33c5:0x33cb]==bytes.fromhex('ad 29 bb c9 20 00')
    r=bytearray(base);mask=bytearray(len(base));writes=[]
    def put(at,z,why,expected):
        assert base[at:at+len(z)]==expected and not any(mask[at:at+len(z)])
        r[at:at+len(z)]=z;mask[at:at+len(z)]=b'\1'*len(z)
        writes.append({'offset':f'{at:06X}','bytes':len(z),'reason':why,
            'before_hex':expected.hex(' ').upper(),'after_hex':z.hex(' ').upper()})
    # 3D has already read the original RAM price and called C03503. A 16-bit
    # VM cursor here points at the final operand. Use the original 3E compact
    # copy branches starting C033C5, retaining at least one zero digit.
    helper=branch_code(['08 e2 20 a5 7a c9 fc',(None,0xd0,'ordinary'),
        'c2 20 a5 78 c9 56 39',(None,0xf0,'compact'),'c9 02 42',(None,0xf0,'compact'),
        ('label','ordinary'),'28 ad 29 bb 8d 6d d5 5c 9a 33 c0',
        ('label','compact'),'28 5c c5 33 c0'])
    at=0x59de30;assert at+len(helper)<=0x59de80
    assert base[at:at+len(helper)]==source[at:at+len(helper)]==b'\xff'*len(helper)
    put(at,helper,'two exact inn quote cursors only; reuse native variable-width number copy',b'\xff'*len(helper))
    put(0x3394,bytes.fromhex('5c 30 de 59 ea ea'),'bounded inn quote display adapter',bytes.fromhex('ad 29 bb 8d 6d d5'))
    for h in [0xffdc,0x40ffdc]:r[h:h+4]=bytes.fromhex('ff ff 00 00')
    cs=sum(r)&65535
    for h in [0xffdc,0x40ffdc]:
        put(h,(cs^65535).to_bytes(2,'little')+cs.to_bytes(2,'little'),'SNES checksum',base[h:h+4])
    assert len(r)==0x800000 and sum(r)&65535==cs
    assert all(mask[i]for i,(x,y)in enumerate(zip(base,r))if x!=y)
    for lo,hi in [(0x2c0000,0x2c8000),(0x608000,0x60c000),(0x780000,0x790000),(0x7d0000,0x7e0000),
                  (0x3a0000,0x3d0000),(0x7ff280,0x7ffff0),(0x3503,0x3562)]:assert r[lo:hi]==base[lo:hi]
    proof={'schema':'v295-inn-price-padding-v1','status':'STATIC_PASS_RUNTIME_PENDING',
        'ROM':out.relative_to(P).as_posix(),'SHA256':sha(r),'base_ROM':m['latest_test_ROM']['file'],
        'base_SHA256':sha(base),'writes':writes,'helper_file':'59DE30','helper_bytes':len(helper),
        'exact_native_commands':['FC3954:3D EF 00','FC4200:3D EF 00'],
        'checked_VM_cursors':['FC3956','FC4202'],'native_compact_copy_entry':'C033C5',
        'native_price_read_and_decimal_formatter_unchanged':True,'charge_and_stay_logic_unchanged':True,
        'all_other_numeric_commands_fixed_width_preserved':True,'source_scripts_and_texts_unchanged':True,
        'v294_digit_fonts_v293_title_and_v292_rewards_preserved':True,'reserved496_preserved':True}
    out.write_bytes(r);report.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:proof[k]for k in ['ROM','SHA256','helper_bytes','status']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
