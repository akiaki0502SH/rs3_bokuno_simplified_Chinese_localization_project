"""Bounded first layout pilot on v290; preserve every existing shadow payload."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re

from audit_linebreak_feedback_readonly_v1 import file_offset, payload
from dry_run_encoding_plan import encode
from prepare_layout_review_readonly_v1 import source_len

P = Path(__file__).resolve().parents[1]
rd = lambda f: json.loads((P / f).read_text(encoding='utf8'))
sha = lambda b: hashlib.sha256(b).hexdigest().upper()
NL = '{NEWLINE}'
TOKEN = re.compile(r'\{[^{}]+\}')
# Deliberate gaps in the existing BODY arenas, with a margin after previous
# allocations. No fonts, code, active directories or reserved future bridge.
ARENAS = [(0x7EF400, 0x7EFFF0), (0x7F8100, 0x7F85F0), (0x7F8700, 0x7F8AF0),
          (0x7F8B80, 0x7F8CF0), (0x7FB400, 0x7FB7F0), (0x7FB900, 0x7FBBF0),
          (0x7FF800, 0x7FFE00)]
PROTECTED_CODE = [(0x7ED4B8, 0x7ED6B8), (0x7F9D80, 0x7FB400),
                  (0x7FC100, 0x7FC700), (0x7FF27C, 0x7FF800), (0x7FFE00, 0x7FFFF0)]


def cpu(offset):
    return offset - 0x400000 if 0x7E8000 <= offset < 0x800000 else offset


def directory(rom, base_records, inventory):
    base = {int(r['source'], 16): r for r in base_records}
    extras = {int(r['source'], 16): r for r in inventory if r['id'].startswith('extra_shadow:')}
    rows, tables = {}, []
    for bank in range(256):
        d = 0x3FF800 + bank * 5
        n = int.from_bytes(rom[d:d + 2], 'little')
        if not n:
            continue
        table = file_offset(int.from_bytes(rom[d + 2:d + 5], 'little'))
        keys = [int.from_bytes(rom[table + 2 * i:table + 2 * i + 2], 'little') for i in range(n)]
        assert keys == sorted(set(keys))
        tables.append((table, table + 5 * n))
        for i, key in enumerate(keys):
            source = file_offset((bank << 16) | key)
            site = table + 2 * n + 3 * i
            target = file_offset(int.from_bytes(rom[site:site + 3], 'little'))
            if source in base:
                at, body, tail = payload(rom, base[source])
                assert at == target
            else:
                rec = extras[source]
                body = bytes.fromhex(rec['raw_hex'])
                assert rom[target:target + len(body)] == body
                tail = rom[target + len(body):target + len(body) + 4]
                assert len(tail) == 4 and tail[0] == 0xFF and tail[3] == bank
            rows[source] = {'site': site, 'target': target, 'body': body, 'tail': tail,
                            'end': target + len(body) + 4}
    assert len(rows) == 11877
    return rows, tables


def prefix_reasons(rec, inv, source_rom, source_units):
    """First pilot includes only independently identifiable window starts."""
    why = set()
    target = int(rec['source'], 16)
    for context in inv['window_contexts']:
        anchor = int(context['window_anchor'], 16) if context['window_anchor'] else None
        if anchor is None or anchor >> 16 != target >> 16 or anchor >= target:
            why.add('window_inheritance_requires_complete_caller')
            continue
        at = anchor + source_len(source_rom, anchor)
        prefix_nl = 0
        while at < target:
            if at in source_units:
                why.add('previous_text_in_same_window_requires_combined_layout')
                at = int(source_units[at]['resume'], 16)
                continue
            b = source_rom[at]
            n = source_len(source_rom, at)
            if not n or at + n > target:
                why.add('window_prefix_not_fully_decoded')
                break
            if (b >= 0x51 or 0x20 <= b <= 0x23 or
                    b in (0x18, 0x46) and source_rom[at + 1] >= 0x10 or
                    b in (0x39, 0x3A, 0x3B, 0x3D, 0x4A, 0x50)):
                why.add('printed_name_or_spacing_before_payload')
            if b == 0x24:
                prefix_nl += 1
            if b in (0x0B, 0x0C, 0x08, 0x4C) or b == 0x0D and source_rom[at + 1] in (0x17, 0x18, 0x19, 0x2D, 0x2F):
                why.add('prefix_call_requires_full_flow')
            at += n
        if prefix_nl + rec['proposed_text'].count(NL) + 1 > rec['window_budget'][1]:
            why.add('leading_original_newline_consumes_window_rows')
    return why


def split_terms(rec, terms):
    text = rec['proposed_display'].replace('▼', '')
    flat, cuts, position = text.replace('\n', ''), [], 0
    for ch in text:
        if ch == '\n':
            cuts.append(position)
        else:
            position += 1
    bad = set()
    for term in terms:
        if len(term) > rec['window_budget'][0]:
            continue
        at = flat.find(term)
        while at >= 0:
            if any(at < cut < at + len(term) for cut in cuts):
                bad.add(term)
            at = flat.find(term, at + 1)
    return sorted(bad)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--rom', default='roms/work/bokuno_cn_candidate_v10bk291_layout_v3_pilot_20261017_01.smc')
    parser.add_argument('--report', default='qa/V291_LAYOUT_V3_PILOT_BUILD_20261017_01.json')
    args = parser.parse_args()
    out, reportpath = (P / args.rom).resolve(), (P / args.report).resolve()
    assert out.is_relative_to(P / 'roms/work') and reportpath.is_relative_to(P / 'qa')
    if args.write:
        assert not out.exists() and not reportpath.exists()
    readiness = rd('qa/LAYOUT_V3_PREWRITE_READINESS_20261016_01.json')
    baseline_path = P / readiness['ROM']
    baseline = baseline_path.read_bytes()
    assert sha(baseline) == readiness['ROM_SHA256'] == '20B421AE2840FB23A40CC7A5B39692781190FE24FC8D1775E0045B7E8FA806F2'
    source = (P / '../roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
    assert sha(source) == '4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0'
    html = (P / 'qa/layout_review_20261016_03/排版检查与预览_按词断行.html').read_bytes()
    assert sha(html) == readiness['HTML_SHA256']
    base = rd('docs/ALINE_V10AJ264_BATCH263B_STORY_20261008_05.json')
    base_by_id = {r['id']: r for r in base['records']}
    source_units = {int(r['source'], 16): r for r in base['records']}
    inventory = rd('qa/layout_review_20261016_02/text_inventory_and_previews.json')
    inv = {r['id']: r for r in inventory}
    live, tables = directory(baseline, base['records'], inventory)
    guard = rd('text/extracted/aline_payload_end16_guard_v33_batch263b_20261008_05.json')['forbidden']
    manifest = rd('text/translations/translation_sources_current.json')
    mapping = {c: bytes.fromhex(z) for c, z in rd(manifest['latest_font_mapping']).items() if len(c) == 1}
    terms = rd('qa/layout_review_20261016_03/tools/names.json') + rd('qa/layout_review_20261016_03/tools/terms_curated.json')
    terms += ['冲击波', '勇敢的冒险者', '圣王遗物', '次元裂隙', '光之钻石']
    terms = {t for t in terms if isinstance(t, str) and re.fullmatch(r'[\u3400-\u9fff]{2,20}', t)}
    selected, held = [], []
    for rec in readiness['candidates']:
        reasons = set()
        splits = split_terms(rec, terms)
        if splits:
            reasons.add('protected_phrase_split')
        if '\n们' in rec['proposed_display']:
            reasons.add('plural_suffix_split_from_preceding_noun')
        if rec['category'] == '剧情与对白':
            reasons |= prefix_reasons(rec, inv[rec['id']], source, source_units)
            if rec['source'] not in guard:
                reasons.add('source_end16_guard_missing')
        if reasons:
            held.append({'id': rec['id'], 'reasons': sorted(reasons), 'split_terms': splits})
        else:
            selected.append(rec)
    assert selected and len(selected) + len(held) == 449
    # Every allocation must be within an existing BODY interval, blank in both
    # current and clean ROMs, and outside all live records/directories/code.
    declared = [(int(a, 16), int(b, 16)) for a, b in base['arena_payload_ranges']]
    for lo, hi in ARENAS:
        assert any(a <= lo < hi <= b for a, b in declared)
        assert baseline[lo:hi] == source[lo:hi] == bytes(hi - lo), (hex(lo), hex(hi))
        for a, b in tables + PROTECTED_CODE + [(x['target'], x['end']) for x in live.values()]:
            assert hi <= a or b <= lo, (hex(lo), hex(hi), hex(a), hex(b))
    rom, allowed = bytearray(baseline), bytearray(len(baseline))
    writes, rows = [], []

    def put(at, data, reason, rid):
        assert 0 <= at <= len(rom) - len(data)
        assert not any(allowed[at:at + len(data)]), (rid, hex(at))
        rom[at:at + len(data)] = data
        allowed[at:at + len(data)] = b'\1' * len(data)
        writes.append({'offset': f'{at:06X}', 'bytes': len(data), 'id': rid, 'reason': reason,
                       'before_hex': baseline[at:at + len(data)].hex(' ').upper(), 'after_hex': data.hex(' ').upper()})

    arena_index, cursor, padding = 0, ARENAS[0][0], 0
    for rec in selected:
        assert rec['current_text'].replace(NL, '') == rec['proposed_text'].replace(NL, '')
        assert [t for t in TOKEN.findall(rec['current_text']) if t != NL] == [t for t in TOKEN.findall(rec['proposed_text']) if t != NL]
        fixed = rec['category'] == '固定说明'
        text = rec['proposed_text'].replace(NL, ' ') if fixed else rec['proposed_text']
        data, missing, errors = encode(text, mapping, battle=False)
        assert not missing and not errors and data == bytes.fromhex(rec['new_encoded_hex']), rec['id']
        row = dict(rec)
        if fixed:
            at = int(rec['source'], 16)
            old, missing, errors = encode(rec['current_text'].replace(NL, ' '), mapping, battle=False)
            assert not missing and not errors and rom[at] == len(old) and rom[at + 1:at + 1 + len(old)] == old
            assert len(data) <= 63
            put(at, bytes([len(data)]) + data + bytes(63 - len(data)), 'fixed_description_newlines_only', rec['id'])
            row.update(new_payload_file=f'{at:06X}', mode='fixed64')
        else:
            entry = live[int(rec['source'], 16)]
            old, missing, errors = encode(rec['current_text'], mapping, battle=False)
            assert not missing and not errors and entry['body'] == old
            forbidden = {int(v, 16) for v in guard[rec['source']]}
            blob = data + entry['tail']
            while True:
                lo, hi = ARENAS[arena_index]
                cursor += cursor & 1
                if cursor + len(blob) > hi:
                    arena_index += 1
                    assert arena_index < len(ARENAS), 'BODY capacity exhausted'
                    cursor = ARENAS[arena_index][0]
                    continue
                if any((cursor + i) & 65535 in forbidden for i in range(len(blob))):
                    cursor += 2; padding += 2; continue
                break
            at = cursor; cursor += len(blob)
            put(at, blob, 'new_shadow_body_old_payload_retained', rec['id'])
            put(entry['site'], cpu(at).to_bytes(3, 'little'), 'existing_shadow_pointer_only', rec['id'])
            row.update(new_payload_file=f'{at:06X}', new_payload_CPU=f'{cpu(at):06X}',
                pointer_file=f'{entry["site"]:06X}', return_hex=entry['tail'].hex(' ').upper(),
                forbidden_end16=sorted(forbidden), mode='relocated_old_body_unchanged')
        rows.append(row)
    # Existing executable code, fonts, original event stream and future bridge.
    for lo, hi in [(0, 0x3A0000), (0x3A0000, 0x3D0000), (0x3D0000, 0x3FF800),
                   (0x780000, 0x790000), (0x7D0000, 0x7E0000)] + PROTECTED_CODE:
        assert rom[lo:hi] == baseline[lo:hi], (hex(lo), hex(hi))
    assert rom[0x3FF800:0x3FFD00] == baseline[0x3FF800:0x3FFD00]
    for e in live.values():
        assert rom[e['target']:e['end']] == baseline[e['target']:e['end']], 'old payload changed'
    # Validate all 11,877 live directory entries again with the actual candidate.
    updated, _ = directory(rom, base['records'], inventory)
    selected_sources = {int(x['source'], 16): x for x in rows if x['mode'] != 'fixed64'}
    for src, entry in updated.items():
        if src in selected_sources:
            row = selected_sources[src]
            assert entry['body'] == bytes.fromhex(row['new_encoded_hex'])
            assert entry['target'] == int(row['new_payload_file'], 16)
            assert entry['tail'] == live[src]['tail']
        else:
            assert entry == live[src], hex(src)
    for site in rd('build/source_control_table264_20261008_05.json')['sites']:
        at = site['CPU'] - 0xC00000
        assert rom[at:at + 2] == baseline[at:at + 2]
    for at in (0xFFDC, 0x40FFDC):
        put(at, bytes.fromhex('FF FF 00 00'), 'checksum', None)
    checksum = sum(rom) & 65535
    for at in (0xFFDC, 0x40FFDC):
        rom[at:at + 4] = (checksum ^ 65535).to_bytes(2, 'little') + checksum.to_bytes(2, 'little')
    for write in writes:
        if write['reason'] == 'checksum':
            at = int(write['offset'], 16)
            write['after_hex'] = rom[at:at + write['bytes']].hex(' ').upper()
    assert sum(rom) & 65535 == checksum and len(rom) == 0x800000
    assert all(allowed[i] for i, (a, b) in enumerate(zip(baseline, rom)) if a != b)
    report = {'schema': 'v291-layout-v3-pilot-build-v1', 'status': 'STATIC_PASS_RUNTIME_PENDING',
        'ROM': out.relative_to(P).as_posix(), 'SHA256': sha(rom), 'base_ROM': readiness['ROM'], 'base_SHA256': sha(baseline),
        'v3_HTML_SHA256': readiness['HTML_SHA256'], 'input_candidates': 449, 'selected': len(rows),
        'selected_categories': dict(collections.Counter(x['category'] for x in rows)), 'held_from_candidates': held,
        'held_reason_counts': dict(collections.Counter(reason for x in held for reason in x['reasons'])),
        'rows': rows, 'writes': writes, 'allocation_ranges': [[f'{a:06X}', f'{b:06X}'] for a, b in ARENAS],
        'allocation_end': f'{cursor:06X}', 'end16_alignment_padding': padding,
        'old_11877_shadow_payloads_retained_byte_exact': True, 'all_live_directories_readback_pass': True,
        'wording_and_non_newline_controls_preserved': True, 'source_events_and_957_classification_sites_preserved': True,
        'font_geometry_baseline_postbattle_code_preserved': True, 'reserved496_zero_preserved': True,
        'changed_bytes': sum(a != b for a, b in zip(baseline, rom)), 'full_v3_applied': False,
        'manual_and_original_scene_validation_pending': True, 'formal_baseline_promoted': False}
    assert sha(baseline_path.read_bytes()) == readiness['ROM_SHA256']
    if args.write:
        out.write_bytes(rom)
        assert out.read_bytes() == rom
        reportpath.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    else:
        report['status'] = 'PLAN_STATIC_PASS_NO_ROM_WRITTEN'
        (P / 'qa/V291_LAYOUT_V3_PILOT_PLAN_20261017_01.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: report[k] for k in ['status', 'ROM', 'SHA256', 'selected', 'selected_categories',
        'held_reason_counts', 'allocation_end', 'changed_bytes']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
