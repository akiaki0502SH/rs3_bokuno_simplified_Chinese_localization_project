"""Correct the v288 vertical centring regression on verified v289."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
from font_geometry_v1 import is_cjk,glyph_locations,read_glyph,unpack
from font_baseline_v1 import normalize_baseline
P=Path(__file__).resolve().parents[1]
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',default='roms/work/bokuno_cn_candidate_v10bj290_font_baseline_20261014_01.smc')
    parser.add_argument('--report',default='qa/V290_FONT_BASELINE_BUILD_20261014_01.json')
    parser.add_argument('--independent',action='store_true');args=parser.parse_args()
    out,proof=(P/args.rom).resolve(),(P/args.report).resolve()
    assert out.is_relative_to(P)and proof.is_relative_to(P)and not out.exists()and not proof.exists()
    m=rd('text/translations/translation_sources_before_v290_20261014_01.json')
    assert m['build_revision']=='v289_postbattle_word_order01'
    b=(P/m['latest_test_ROM']['file']).read_bytes();assert sha(b)==m['latest_test_ROM']['SHA256']
    mp=rd(m['latest_font_mapping']);old_rows={x['atom']:x for x in rd('qa/V288_FONT_GEOMETRY_BUILD_20261012_01.json')['rows']}
    r,allow=bytearray(b),bytearray(len(b));rows=[];writes=[];replacements={};explicit=set()
    def put(at,old,new,why):
        assert read_glyph(b,at)==old
        if old==new:return
        for site,z in zip(at,[new[:16],new[16:]]):r[site:site+16]=z;allow[site:site+16]=b'\1'*16
        writes.append({'upper':f'{at[0]:06X}','lower':f'{at[1]:06X}',
            'reason':why,'before_SHA256':sha(old),'after_SHA256':sha(new)})
    for atom,c in mp.items():
        if not is_cjk(atom):continue
        locations=glyph_locations(bytes.fromhex(c));raw=read_glyph(b,locations[0])
        source_y=old_rows[atom]['before_bbox'][1]
        new,geometry=normalize_baseline(raw,source_y)
        assert geometry['shift'][0]==0,'Horizontal geometry must remain intact'
        assert raw not in replacements or replacements[raw]==new
        replacements[raw]=new
        for at in locations:
            assert read_glyph(b,at)==raw;explicit.add(at);put(at,raw,new,atom)
        rows.append({'atom':atom,'code':bytes.fromhex(c).hex(' ').upper(),**geometry,
            'changed':new!=raw,'new_SHA256':sha(new),'new_hex':new.hex(' ').upper()})
    aliases=[]
    for base,n in [(0x2c0000,1024),(0x608000,256),(0x60a000,256),(0x780000,2048),(0x7d0000,2048)]:
        for slot in range(n):
            top=base+slot//8*256+slot%8*16;at=(top,top+128)
            if at in explicit:continue
            raw=read_glyph(b,at)
            if raw in replacements and replacements[raw]!=raw:
                put(at,raw,replacements[raw],'exact CJK alias, including 王20A3')
                aliases.append({'upper':f'{top:06X}','lower':f'{top+128:06X}'})
    for x in rows:
        for at in glyph_locations(bytes.fromhex(x['code'])):
            raw=read_glyph(r,at);assert sha(raw)==x['new_SHA256']
            assert normalize_baseline(raw,old_rows[x['atom']]['before_bbox'][1])[0]==raw
    for h in [0xffdc,0x40ffdc]:r[h:h+4]=bytes.fromhex('ff ff 00 00');allow[h:h+4]=b'\1'*4
    cs=sum(r)&65535
    for h in [0xffdc,0x40ffdc]:r[h:h+4]=(cs^65535).to_bytes(2,'little')+cs.to_bytes(2,'little')
    assert sum(r)&65535==cs and len(r)==0x800000
    assert all(allow[i]for i,(x,y)in enumerate(zip(b,r))if x!=y)
    atlas=rd(m['latest_font_atlas'])
    for x in atlas['glyphs']:
        if not is_cjk(x['atom']):
            assert all(read_glyph(b,at)==read_glyph(r,at)for at in glyph_locations(bytes.fromhex(x['code'])))
    assert r[0x7ff280:0x7ff800]==b[0x7ff280:0x7ff800],'v289 reward hooks and literals preserved'
    report={'schema':'v290-font-baseline-v1','status':'STATIC_PASS_RUNTIME_PENDING','ROM':out.relative_to(P).as_posix(),
        'SHA256':sha(r),'base_ROM':m['latest_test_ROM']['file'],'base_SHA256':sha(b),
        'root_cause':'v288 cropped each ink bbox and vertically centred it; 11px-high 王/形/阳 were shifted up one row.',
        'body_baseline_y':13,'CJK_singles_audited':len(rows),'CJK_singles_changed':sum(x['changed']for x in rows),
        'body_glyphs_changed':sum(x['changed']and not x['short_stroke_design_preserved']for x in rows),
        'short_glyphs_restored':[x['atom']for x in rows if x['changed']and x['short_stroke_design_preserved']],
        'shift_counts':dict(Counter(str(x['shift'])for x in rows)),
        'target_glyphs':[x for x in rows if x['atom']in['王','形','阳']],
        'extra_aliases_synchronized':aliases,'horizontal_positions_and_all_strokes_preserved':True,
        'right_edge_clipping_fix_preserved':True,'v289_postbattle_composition_preserved':True,
        'text_names_control_flow_gameplay_and_linebreaks_unchanged':True,'rows':rows,'writes':writes,
        'formal_baseline_promoted':False}
    out.write_bytes(r);proof.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if not args.independent:
        fd=P/'font/v290_baseline_20261014_01';assert not fd.exists();fd.mkdir()
        native=[]
        for name,base,n in [('event_atlas',0x780000,0x10000),('fixed_atlas',0x7d0000,0x10000),
            ('standard_font',0x2c0000,0x8000),('native18_font',0x608000,0x2000),('native46_font',0x60a000,0x2000)]:
            z=bytes(r[base:base+n]);f=fd/(name+'.bin');f.write_bytes(z)
            if name in ['event_atlas','fixed_atlas']:
                atlas['eventAtlas'if name=='event_atlas'else'fixedAtlas']={'path':f.relative_to(P).as_posix(),'sha256':sha(z)}
            else:native.append({'path':f.relative_to(P).as_posix(),'offset':f'{base:06X}','length':n,'SHA256':sha(z)})
        atlas['native_geometry_snapshots']=native;bycode={x['code']:x for x in rows}
        for x in atlas['glyphs']:
            z=read_glyph(r,glyph_locations(bytes.fromhex(x['code']))[0]);x['glyphSha256']=sha(z)
            if 'glyphHex'in x:x['glyphHex']=z.hex(' ').upper()
            if x['code']in bycode:
                row=bycode[x['code']];x['placement']={'bbox':row['after_bbox'],'rule':'v290 horizontal centre and body baseline y13; short-stroke design retained','strokes_preserved':True}
        for x in atlas.get('carrierRelocations',[]):
            z=read_glyph(r,glyph_locations(bytes.fromhex(x['newCode']))[0]);x.update(glyphHex=z.hex(' ').upper(),glyphSha256=sha(z))
        atlas.update(source_version='v290_font_baseline01',final_ROM_SHA256=sha(r))
        atlas.setdefault('notes',[]).append('v290正文汉字按共同底部y13定位，横向及全部笔画保持；一、二保留原字体短笔画设计位置。替代v288的独立墨点框垂直居中规则。')
        (P/'docs/SINGLE_GLYPH_ATLAS_V290_BASELINE_20261014_01.json').write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k]for k in ['ROM','SHA256','CJK_singles_audited','CJK_singles_changed','body_glyphs_changed','short_glyphs_restored']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
