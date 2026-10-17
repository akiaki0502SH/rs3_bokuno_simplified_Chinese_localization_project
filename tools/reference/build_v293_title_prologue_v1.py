"""Route only four native title pages to the user-confirmed Chinese text."""
from pathlib import Path
import argparse,hashlib,json,sys
from build_font_renderer_hook import branch_code
from dry_run_encoding_plan import encode

P=Path(__file__).resolve().parents[1]
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))
TABLE=0x3FFD50
INIT=0x3FFC50
LOOP=0x3FFCC0
GLYPH=0x3FFD80
NATIVE=[(0x0937,0x09C4),(0x09C4,0x0A72),(0x0A72,0x0B3B),(0x0B3B,0x0BD4)]


def long(op,at):return f'{op:02X} '+at.to_bytes(3,'little').hex(' ')


def init_code():
    # Preserve the original C01B1E call and every returned register/flag.
    # A table row must match both original start and exclusive end.
    return branch_code(['22 1e 1b c0','08 c2 30 48 da e2 20 a5 7a c9 fc',
        (None,0xD0,'restore'),'c2 20 a2 00 00',('label','find'),
        'a5 78',long(0xDF,TABLE),(None,0xD0,'next'),
        'a5 7b',long(0xDF,TABLE+2),(None,0xD0,'restore'),
        long(0xBF,TABLE+4),'85 78',long(0xBF,TABLE+6),'85 7b e2 20',
        long(0xBF,TABLE+8),'85 7a',(None,0x80,'restore'),
        ('label','next'),'8a 18 69 0a 00 aa e0 28 00',(None,0x90,'find'),
        ('label','restore'),'c2 30 fa 68 28 6b'])


def loop_code():
    # Native FF3971 is also the page's completion check. Restore the exact
    # original end/bank here, before its ordinary comparison and RTS in FF.
    # The existing CN-aware font classifier/reader already supports the text.
    return branch_code(['08 c2 30 48 da a2 00 00',('label','find'),
        'a5 78',long(0xDF,TABLE+6),(None,0xD0,'next'),
        'a5 7b',long(0xDF,TABLE+6),(None,0xD0,'next'),
        'e2 20 a5 7a',long(0xDF,TABLE+8),(None,0xD0,'next8'),
        'c2 20',long(0xBF,TABLE+2),'85 78 85 7b e2 20 a9 fc 85 7a',
        (None,0x80,'restore'),('label','next8'),'c2 20',('label','next'),
        '8a 18 69 0a 00 aa e0 28 00',(None,0x90,'find'),
        ('label','restore'),'c2 30 fa 68 28 c2 20 a5 78 5c 75 39 ff'])


def glyph_code():
    # The existing 55D440 title helper maps virtual lead bytes to 28..2F and
    # native 18/46 leads to 24/25, but loses the glyph's low byte (e.g. 12 7F
    # becomes 2A00). Recover that byte
    # from the just-consumed stream without changing its cursor. The native
    # index calculation wraps 28..2F to atlas pages 0..7 as intended.
    return branch_code(['08 c2 20 48 e2 20 a5 7a c9 59',
        (None,0xF0,'bank59'),'c9 3f',(None,0xD0,'restore'),
        'c2 20 a5 78 c9 98 fb',(None,0x90,'restore'),'c9 4a fc',
        (None,0xB0,'restore'),(None,0x80,'rangeok'),
        ('label','bank59'),'c2 20 a5 78 c9 40 da',(None,0x90,'restore'),
        'c9 8f dc',(None,0xB0,'restore'),('label','rangeok'),
        'c2 20 a5 8d c9 00 24',(None,0x90,'restore'),
        'c9 00 30',(None,0xB0,'restore'),
        'c6 78 e2 20 a7 78 85 8d c2 20 e6 78',('label','restore'),
        'c2 20 68 28 5a c2 20 a6 8d 5c ee 39 ff'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',default='roms/work/bokuno_cn_candidate_v10bm293_title_prologue_20261017_05.smc')
    parser.add_argument('--report',default='qa/V293_TITLE_PROLOGUE_BUILD_20261017_05.json')
    a=parser.parse_args();out=(P/a.rom).resolve();report=(P/a.report).resolve()
    assert out.is_relative_to(P/'roms/work') and report.is_relative_to(P/'qa')
    assert not out.exists() and not report.exists()
    overlay=rd('text/translations/title_prologue_user_confirmed_v293_20261017_01.json')
    base=(P/overlay['base_ROM']['file']).read_bytes()
    assert sha(base)==overlay['base_ROM']['SHA256']=='26CBE0971C02D2908B486FF40E8616D4E70CB950ADAC8DEEB4632E3F311EAB7F'
    src=(P.parent/'roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
    frozen=rd('text/translations/translation_sources_before_v293_20261017_01.json')
    assert frozen['build_revision']=='v292_reward_growth01'
    mapping={k:bytes.fromhex(v)for k,v in rd(frozen['latest_font_mapping']).items()}
    r=bytearray(base);covered=bytearray(len(base));writes=[]
    def put(at,z,reason,expected=None):
        assert not any(covered[at:at+len(z)])
        before=base[at:at+len(z)]
        if expected is None:assert before==src[at:at+len(z)]==bytes([255 if at<0x600000 else 0])*len(z),(hex(at),reason)
        else:assert before==expected,(hex(at),reason,before.hex())
        r[at:at+len(z)]=z;covered[at:at+len(z)]=b'\1'*len(z)
        writes.append({'offset':f'{at:06X}','bytes':len(z),'reason':reason,
            'before_hex':before.hex(' ').upper(),'after_hex':z.hex(' ').upper()})
    pages=[];table=bytearray();cursor=0x59DA40
    for i,page in enumerate(overlay['pages']):
        lines=page['lines'];assert len(lines)==[10,11,11,10][i]
        assert all(len(s)<=16 and not s.endswith(('，','。','、'))for s in lines)
        text='{NEWLINE}'+'{NEWLINE}'.join(' '*((16-len(s))//2)+s if s else ''for s in lines)
        z,missing,errors=encode(text,mapping,battle=False);assert not missing and not errors
        at=cursor if i<3 else 0x7FFB98
        if i<3:cursor+=len(z);assert cursor<=0x59DD00
        cpu=at if at<0x600000 else at-0x400000
        end=(cpu+len(z))&65535
        put(at,z,f'user-confirmed title page {i+1}')
        start,original_end=NATIVE[i]
        table+=start.to_bytes(2,'little')+original_end.to_bytes(2,'little')
        table+=(cpu&65535).to_bytes(2,'little')+end.to_bytes(2,'little')+bytes([cpu>>16,0])
        pages.append({'page':i+1,'event':page['event'],'lines':lines,'centred_tokens':text,
            'line_columns':[len(s)for s in lines],'leading_spaces':[(16-len(s))//2 if s else 0 for s in lines],
            'file':f'{at:06X}','cpu':f'{cpu:06X}','end_low':f'{end:04X}','bytes':len(z),
            'native_start':f'FC{start:04X}','native_end':f'FC{original_end:04X}',
            'SHA256':sha(z),'encoded_hex':z.hex(' ').upper()})
    init=init_code();loop=loop_code();glyph=glyph_code()
    assert len(init)<=LOOP-INIT and len(loop)<=TABLE-LOOP and len(table)==40
    assert 0x7FFB98+pages[-1]['bytes']<=INIT+0x400000
    put(INIT+0x400000,init,'exact four-page start/end adapter')
    put(LOOP+0x400000,loop,'restore native page cursor/end before original completion test')
    put(TABLE+0x400000,bytes(table),'bounded title page mapping table')
    assert GLYPH+len(glyph)<=0x3FFE00
    put(GLYPH+0x400000,glyph,'recover virtual glyph low byte for four new title streams')
    put(0x3F38E5,bytes.fromhex('22')+INIT.to_bytes(3,'little'),'wrap original title event getter',bytes.fromhex('22 1e 1b c0'))
    put(0x3F3971,bytes.fromhex('5c')+LOOP.to_bytes(3,'little'),'wrap title loop completion check',bytes.fromhex('c2 20 a5 78'))
    put(0x3F39E9,bytes.fromhex('5c')+GLYPH.to_bytes(3,'little')+b'\xea','adapt title virtual glyph indices',bytes.fromhex('5a c2 20 a6 8d'))
    for h in [0xffdc,0x40ffdc]:
        r[h:h+4]=bytes.fromhex('ff ff 00 00')
    cs=sum(r)&65535
    for h in [0xffdc,0x40ffdc]:
        put(h,(cs^65535).to_bytes(2,'little')+cs.to_bytes(2,'little'),'SNES checksum',base[h:h+4])
    assert sum(r)&65535==cs and len(r)==len(base)==0x800000
    assert all(covered[i]for i,(x,y)in enumerate(zip(base,r))if x!=y)
    assert r[0x3C0937:0x3C0BD4]==base[0x3C0937:0x3C0BD4]
    for lo,hi in [(0x2C0000,0x2C8000),(0x608000,0x60C000),(0x780000,0x790000),(0x7D0000,0x7E0000),
                  (0x7FF280,0x7FF800),(0x7FFE00,0x7FFFF0)]:assert r[lo:hi]==base[lo:hi]
    proof={'schema':'v293-title-prologue-build-v1','status':'STATIC_PASS_NATIVE_COLD_BOOT_PENDING',
        'ROM':out.relative_to(P).as_posix(),'SHA256':sha(r),'base_ROM':overlay['base_ROM']['file'],
        'base_SHA256':sha(base),'pages':pages,'writes':writes,'init_helper_bytes':len(init),
        'loop_helper_bytes':len(loop),'font_bytes_unchanged':True,'native_script_and_old_shadows_preserved':True,
        'glyph_index_helper_bytes':len(glyph),
        'v292_reward_module_preserved':True,'reserved_last_496_bytes_preserved':True,
        'runtime_scope':'Exact FC0937/09C4/0A72/0B3B start and end pairs only; original FF full-screen text renderer and Chinese glyph pipeline retained.'}
    out.write_bytes(r);report.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:proof[k]for k in ['ROM','SHA256','init_helper_bytes','loop_helper_bytes','status']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
