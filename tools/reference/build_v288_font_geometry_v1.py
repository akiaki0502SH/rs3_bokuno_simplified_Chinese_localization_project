"""Apply the complete, lossless full-CJK font placement pass after v287.

All input versions remain frozen. This final build stage must be reapplied
after historical builders, rather than rewriting their font-generation rules.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import sys
from font_geometry_v1 import is_cjk, normalize_cjk, glyph_locations, read_glyph

P = Path(__file__).resolve().parents[1]
FROZEN = 'text/translations/translation_sources_before_v288_20261012_01.json'
sha = lambda z: hashlib.sha256(z).hexdigest().upper()
rd = lambda f: json.loads((P / f).read_text(encoding='utf8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', default='roms/work/bokuno_cn_candidate_v10bh288_font_geometry_20261012_01.smc')
    parser.add_argument('--report', default='qa/V288_FONT_GEOMETRY_BUILD_20261012_01.json')
    parser.add_argument('--independent', action='store_true')
    args = parser.parse_args()
    out, proof = (P / args.rom).resolve(), (P / args.report).resolve()
    assert out.is_relative_to(P) and proof.is_relative_to(P)
    assert not out.exists() and not proof.exists()
    m = rd(FROZEN)
    assert m['build_revision'] == 'v287_sheraha_wording01'
    b = (P / m['latest_test_ROM']['file']).read_bytes()
    assert sha(b) == m['latest_test_ROM']['SHA256']
    mapping = rd(m['latest_font_mapping'])
    r, allow = bytearray(b), bytearray(len(b))
    rows, writes, replacements, explicit = [], [], {}, set()

    def put_glyph(at, before, after, reason):
        assert read_glyph(b, at) == before
        if before == after:
            return
        for site, z in zip(at, (after[:16], after[16:])):
            r[site:site + 16] = z
            allow[site:site + 16] = b'\1' * 16
        writes.append({'upper': f'{at[0]:06X}', 'lower': f'{at[1]:06X}',
                       'reason': reason, 'before_SHA256': sha(before),
                       'after_SHA256': sha(after)})

    for atom, c in mapping.items():
        if not is_cjk(atom):
            continue
        code = bytes.fromhex(c)
        locations = glyph_locations(code)
        before = read_glyph(b, locations[0])
        after, geometry = normalize_cjk(before)
        assert all(read_glyph(b, at) == before for at in locations), atom
        assert before not in replacements or replacements[before] == after
        replacements[before] = after
        for at in locations:
            explicit.add(at)
            put_glyph(at, before, after, atom)
        rows.append({'atom': atom, 'code': code.hex(' ').upper(), **geometry,
                     'changed': before != after, 'old_SHA256': sha(before),
                     'new_SHA256': sha(after), 'new_hex': after.hex(' ').upper()})

    # The native font contains duplicate encodings (e.g. F7 and 20 A7 for 大).
    # Keep exact bitmap aliases in sync, even when the canonical map uses only
    # one of them. Match complete 32-byte glyphs, never partial stroke shapes.
    aliases = []
    for base, slots in [(0x2C0000,1024),(0x608000,256),(0x60A000,256),
                        (0x780000,2048),(0x7D0000,2048)]:
        for slot in range(slots):
            top = base + slot // 8 * 256 + slot % 8 * 16
            at = (top, top + 128)
            if at in explicit:
                continue
            before = read_glyph(b, at)
            if before in replacements and replacements[before] != before:
                put_glyph(at, before, replacements[before], 'exact CJK bitmap alias')
                aliases.append({'upper': f'{at[0]:06X}', 'lower': f'{at[1]:06X}'})

    # Every CJK glyph must survive the native visible-column mask, and every
    # stroke pattern must survive translation. Text/control/code cannot change.
    for row in rows:
        for at in glyph_locations(bytes.fromhex(row['code'])):
            raw = read_glyph(r, at)
            assert sha(raw) == row['new_SHA256']
            assert normalize_cjk(raw)[0] == raw
    for site in (0xFFDC, 0x40FFDC):
        r[site:site + 4] = bytes.fromhex('FF FF 00 00')
        allow[site:site + 4] = b'\1' * 4
    checksum = sum(r) & 65535
    for site in (0xFFDC, 0x40FFDC):
        r[site:site + 4] = (checksum ^ 65535).to_bytes(2,'little') + checksum.to_bytes(2,'little')
    assert sum(r) & 65535 == checksum and len(r) == 0x800000
    assert all(allow[i] for i,(x,y) in enumerate(zip(b,r)) if x != y)
    atlas = rd(m['latest_font_atlas'])
    composite = [x for x in atlas['glyphs'] if len(x['atom']) > 1]
    assert all(read_glyph(b, at) == read_glyph(r, at)
               for x in composite for at in glyph_locations(bytes.fromhex(x['code'])))
    # C3/D6 retain historical kana keys in the mapping, but their actual glyphs
    # were already reassigned to 罗/努 before this build. Their CJK aliases must
    # move together. Every other non-CJK mapped bitmap must remain identical.
    cjk_codes = {bytes.fromhex(code) for atom,code in mapping.items()if is_cjk(atom)}
    legacy_keys = []
    for atom,code_text in mapping.items():
        if is_cjk(atom):continue
        code = bytes.fromhex(code_text)
        try:locations = glyph_locations(code)
        except ValueError:continue
        if any(read_glyph(b,at) != read_glyph(r,at)for at in locations):
            assert code in cjk_codes,(atom,code_text)
            legacy_keys.append({'legacy_key':atom,'code':code_text,
                'CJK_aliases':[ch for ch,z in mapping.items()if is_cjk(ch)and bytes.fromhex(z)==code]})
    report = {
        'schema': 'v288-font-geometry-build-v1',
        'status': 'COMPLETE_CJK_STATIC_PASS_RUNTIME_PENDING',
        'ROM': out.relative_to(P).as_posix(), 'SHA256': sha(r),
        'base_ROM': m['latest_test_ROM']['file'], 'base_SHA256': sha(b),
        'storage_cell': [16,16], 'dialogue_advance': 14,
        'cached_menu_advance': 16, 'common_safe_x': [0,12],
        'target_center': [6.5,7.5], 'rounding': 'floor on both axes',
        'max_center_error_pixels': 0.5,
        'CJK_singles_audited': len(rows),
        'CJK_singles_changed': sum(x['changed'] for x in rows),
        'previous_right_clip_risk_singles': sum(x['previous_clipped_pixels'] > 0 for x in rows),
        'previous_clipped_ink_pixels': sum(x['previous_clipped_pixels'] for x in rows),
        'remaining_right_clip_risk_singles': 0,
        'changed_physical_glyphs': len(writes), 'extra_aliases_synchronized': aliases,
        'shift_counts': dict(Counter(str(x['shift']) for x in rows)),
        'all_single_strokes_sizes_and_pixel_counts_preserved': True,
        'text_code_pointers_gameplay_and_controls_unchanged': True,
        'historical_composite_pairs_preserved': len(composite),
        'composite_limit': 'Two characters packed into one slot remain a separate field-width issue; no lossy resampling in this pass.',
        'non_CJK_typography_preserved': True,
        'legacy_keys_already_reassigned_to_CJK': legacy_keys,
        'rows': rows, 'writes': writes,
        'formal_baseline_promoted': False,
    }
    out.write_bytes(r)
    assert sha(out.read_bytes()) == report['SHA256']
    proof.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if not args.independent:
        fontdir = P / 'font/v288_geometry_20261012_01'
        assert not fontdir.exists()
        fontdir.mkdir()
        for name, base in [('event_atlas',0x780000),('fixed_atlas',0x7D0000)]:
            data = bytes(r[base:base+0x10000])
            (fontdir/(name+'.bin')).write_bytes(data)
            atlas['eventAtlas' if name == 'event_atlas' else 'fixedAtlas'] = {
                'path': (fontdir/(name+'.bin')).relative_to(P).as_posix(), 'sha256': sha(data)}
        native_snapshots = []
        for name,base,size in [('standard_font',0x2C0000,0x8000),
                               ('native18_font',0x608000,0x2000),
                               ('native46_font',0x60A000,0x2000)]:
            data = bytes(r[base:base+size]);path = fontdir/(name+'.bin')
            path.write_bytes(data)
            native_snapshots.append({'path':path.relative_to(P).as_posix(),
                'offset':f'{base:06X}','length':size,'SHA256':sha(data)})
        atlas['native_geometry_snapshots'] = native_snapshots
        geometry_by_code = {x['code']:x for x in rows}
        for entry in atlas['glyphs']:
            raw = read_glyph(r,glyph_locations(bytes.fromhex(entry['code']))[0])
            entry['glyphSha256'] = sha(raw)
            if 'glyphHex' in entry:entry['glyphHex'] = raw.hex(' ').upper()
            if entry['code'] in geometry_by_code:
                row = geometry_by_code[entry['code']]
                entry['placement'] = {'bbox':row['after_bbox'],
                    'rule':'v288 shared full-CJK cell centre with floor rounding',
                    'strokes_preserved':True}
        for entry in atlas.get('carrierRelocations',[]):
            raw = read_glyph(r,glyph_locations(bytes.fromhex(entry['newCode']))[0])
            entry.update(glyphHex=raw.hex(' ').upper(),glyphSha256=sha(raw))
        atlas.update(source_version='v288_font_geometry01',final_ROM_SHA256=sha(r))
        atlas.setdefault('notes',[]).append('v288所有当前中文单字统一到14×16字格中线，取整方向一致；全部墨点保留，x13越界归零。旧复字另属字段宽度问题。')
        (P/'docs/SINGLE_GLYPH_ATLAS_V288_GEOMETRY_20261012_01.json').write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('ROM','SHA256','CJK_singles_audited',
        'CJK_singles_changed','previous_right_clip_risk_singles','remaining_right_clip_risk_singles',
        'changed_physical_glyphs')},ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
