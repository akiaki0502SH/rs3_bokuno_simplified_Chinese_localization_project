"""Independent write replay/encoding checks and bounded runtime evidence binding."""
from pathlib import Path
import hashlib
import json
import re

from dry_run_encoding_plan import encode

P = Path(__file__).resolve().parents[1]
D = P / 'qa/layout_v291_runtime_20261017_01'
rd = lambda f: json.loads((P / f).read_text(encoding='utf8'))
sha = lambda b: hashlib.sha256(b).hexdigest().upper()
TOKEN = re.compile(r'\{[^{}]+\}')


def main():
    build = rd('qa/V291_LAYOUT_V3_PILOT_BUILD_20261017_01.json')
    normal = rd('qa/V291_NORMAL_REGRESSION_20261017_01.json')
    source = (P / build['base_ROM']).read_bytes()
    rom = (P / build['ROM']).read_bytes()
    assert sha(source) == build['base_SHA256'] and sha(rom) == build['SHA256']
    expected, mask = bytearray(source), bytearray(len(source))
    for w in build['writes']:
        at = int(w['offset'], 16)
        before, after = bytes.fromhex(w['before_hex']), bytes.fromhex(w['after_hex'])
        assert len(before) == len(after) == w['bytes']
        assert source[at:at + len(before)] == before and not any(mask[at:at + len(before)])
        expected[at:at + len(after)] = after
        mask[at:at + len(after)] = b'\1' * len(after)
    assert bytes(expected) == rom
    assert all(mask[i] for i, (a, b) in enumerate(zip(source, rom)) if a != b)
    mapping_file = rd('text/translations/translation_sources_current.json')['latest_font_mapping']
    mapping = {c: bytes.fromhex(z) for c, z in rd(mapping_file).items() if len(c) == 1}
    for row in build['rows']:
        a, b = row['current_text'], row['proposed_text']
        assert a.replace('{NEWLINE}', '') == b.replace('{NEWLINE}', '')
        assert [t for t in TOKEN.findall(a) if t != '{NEWLINE}'] == [t for t in TOKEN.findall(b) if t != '{NEWLINE}']
        new_text = b.replace('{NEWLINE}', ' ') if row['mode'] == 'fixed64' else b
        encoded, missing, errors = encode(new_text, mapping, battle=False)
        assert not missing and not errors
        at = int(row['new_payload_file'], 16)
        if row['mode'] == 'fixed64':
            assert len(encoded) <= 63 and rom[at] == len(encoded)
            assert rom[at + 1:at + 1 + len(encoded)] == encoded
            assert rom[at + 1 + len(encoded):at + 64] == bytes(63 - len(encoded))
        else:
            end = at + len(encoded) + 4
            assert rom[at:at + len(encoded)] == encoded
            assert rom[at + len(encoded):end] == bytes.fromhex(row['return_hex'])
            assert all((at + i) & 65535 not in row['forbidden_end16'] for i in range(end - at))
            pointer_at = int(row['pointer_file'], 16)
            assert int.from_bytes(rom[pointer_at:pointer_at + 3], 'little') == int(row['new_payload_CPU'], 16)
            old_at = int(row['current_payload_file'], 16)
            assert rom[old_at:old_at + row['old_bytes'] + 4] == source[old_at:old_at + row['old_bytes'] + 4]
    fonts = [(0x2C0000, 0x2C8000), (0x608000, 0x60C000), (0x780000, 0x790000), (0x7D0000, 0x7E0000)]
    assert all(rom[a:b] == source[a:b] for a, b in fonts)
    assert rom[0x7FF300:0x7FF610] == source[0x7FF300:0x7FF610]
    assert rom[0x7FFE00:0x7FFFF0] == bytes(496)
    assert normal['all_protected_pass'] and normal['paired_cases'] == 13 and normal['ROM_SHA256'] == build['SHA256']
    regions = [('flags', 0xF400, 0xF800), ('actors', 0xF561, 0xF561 + 26 * 48),
               ('extended', 0x1F960, 0x1F960 + 33 * 48), ('name', 0xF300, 0xF308),
               ('money', 0xF31A, 0xF31C), ('inventory', 0xF320, 0xF400)]
    controlled = []
    for case in ['wide3e', 'narrow3e']:
        traces = {version: (D / f'{case}_{version}_trace.txt').read_text(encoding='utf8') for version in ['base', 'candidate']}
        base_ram = (D / f'{case}_base_after.ram').read_bytes()
        new_ram = (D / f'{case}_candidate_after.ram').read_bytes()
        checks = {name: base_ram[lo:hi] == new_ram[lo:hi] for name, lo, hi in regions}
        assert all(checks.values())
        counts = {}
        for version, trace in traces.items():
            m = re.search(r'RESULT reader_hits=(\d+) new_ROM_reads=(\d+) cols=(\d+) rows=(\d+)', trace)
            assert m and int(m[1]) > 0 and int(m[2]) > 0
            counts[version] = [int(v) for v in m.groups()]
        assert counts['base'][2:] == counts['candidate'][2:]
        controlled.append({'case': case, 'checks': checks, 'native_read_counts': counts,
            'candidate_image': (D / f'{case}_candidate.png').relative_to(P).as_posix(),
            'original_story_replay': False, 'scope': 'Original source window constructor, isolated VM metadata, no original scene/actor claim'})
    discarded = [
        {'case': 'wide3e_initial_idle_protection_check', 'trace': (D / 'wide3e_trace.txt').relative_to(P).as_posix(),
         'reason': 'Opening a native dialogue changes fields compared with idle state. Replaced with paired base/candidate protection checks; initial trace retained.'},
        {'case': 'throne3f_borrowed_forest_seed', 'trace': (D / 'throne3f_base_trace.txt').relative_to(P).as_posix(),
         'reason': 'Baseline ROM itself did not reach the requested target; another forest NPC script took over. Not counted as throne dialogue verification.'}]
    seen = sorted({x for row in normal['rows'] for x in row['observed_new_payload_text_cursor']})
    assert seen == ['utt_3C1A6F_3C1A8E', 'utt_3C1C82_3C1C98']
    report = {'status': 'STATIC_311_ROWS_13_NORMAL_PAIRS_AND_2_NATIVE_WINDOW_PAIRS_PASS_MANUAL_PENDING',
        'ROM': build['ROM'], 'SHA256': build['SHA256'], 'base_ROM': build['base_ROM'], 'base_SHA256': build['base_SHA256'],
        'compiled_layout_records': len(build['rows']), 'event_records': 261, 'fixed_description_records': 50,
        'write_manifest_replayed_byte_exact': True, 'fonts_and_v289_postbattle_code_byte_identical': True,
        'normal_input_paired_cases': 13, 'normal_observed_new_payloads': seen, 'controlled_native_pairs': controlled,
        'discarded_diagnostic_attempts': discarded, 'full_original_scene_coverage': False,
        'limits': ['Only two changed dialogue payloads were observed on the normal opening route.',
                   'Two additional native-window pairs are controlled fixtures, not full original scene replays.',
                   'Throne-room original scene still requires manual testing.',
                   'All 311 original contexts and a complete playthrough are not verified.']}
    (P / 'qa/V291_LAYOUT_PILOT_VERIFICATION_20261017_01.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'status': report['status'], 'ROM_SHA256': build['SHA256'], 'compiled': len(build['rows']),
        'normal_pairs': 13, 'controlled_pairs': 2, 'original_scenes_all_verified': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
