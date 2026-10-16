"""Audit encoding/window prerequisites; does not build or write any ROM/patch."""
from pathlib import Path
import collections
import hashlib
import json
import re

from audit_linebreak_feedback_readonly_v1 import payload
from dry_run_encoding_plan import encode

P = Path(__file__).resolve().parents[1]
D = P / 'qa/layout_v3_prewrite_readiness_20261016_01'
rd = lambda f: json.loads((P / f).read_text(encoding='utf8'))
sha = lambda b: hashlib.sha256(b).hexdigest().upper()
TOKEN = re.compile(r'\{[^{}]+\}')
NL = '{NEWLINE}'


def main():
    manifest = rd('text/translations/translation_sources_current.json')
    rompath = P / manifest['latest_test_ROM']['file']
    rom = rompath.read_bytes()
    assert sha(rom) == manifest['latest_test_ROM']['SHA256']
    layouts = rd('qa/layout_v3_prewrite_readiness_20261016_01/default_layouts.json')
    v2 = {r['id']: r for r in rd('qa/layout_review_20261016_02/text_inventory_and_previews.json')}
    base = {r['id']: r for r in rd('docs/ALINE_V10AJ264_BATCH263B_STORY_20261008_05.json')['records']}
    mapping = {c: bytes.fromhex(z) for c, z in rd(manifest['latest_font_mapping']).items() if len(c) == 1}
    candidates, held = [], []
    generated_changed = 0
    for row in layouts['records']:
        proposed = row['proposed_source']
        if proposed is None or proposed == row['text']:
            continue
        generated_changed += 1
        original = v2[row['id']]
        assert row['text'] == original['text']
        reasons = []
        flags = set(original.get('flags', []))
        if row['category'] == '索引说明':
            reasons.append('indexed_description_consumer_unverified')
        if not original.get('window_profiles') or 'window_or_caller_pending' in flags:
            reasons.append('actual_window_unverified')
        if row['fragment'] or 'fragment_or_join_needs_complete_flow' in flags:
            reasons.append('fragment_or_join_unverified')
        if row['variable']:
            reasons.append('variable_name_width_estimated')
        if row['screen_count'] != 1:
            reasons.append('multiple_wait_segments_need_native_paging_validation')
        if row['added_newline_after_wait']:
            reasons.append('new_wait_boundary_newline_needs_validation')
        text = row['text']
        body = text[:-len('{BUTTON_WAIT}')] if text.endswith('{BUTTON_WAIT}') else text
        tokens = TOKEN.findall(body)
        allowed = lambda token: (token == NL or bool(re.fullmatch(r'\{LOCATION:[0-9A-F]{2}\}', token)) or
            bool(re.fullmatch(r'\{CHARACTER_NAME:[0-9A-E][0-9A-F]\}', token)))
        if any(not allowed(t) for t in tokens):
            reasons.append('timing_or_other_controls_require_separate_review')
        if proposed.replace(NL, '') != text.replace(NL, ''):
            reasons.append('non_layout_content_changed')
        if [t for t in TOKEN.findall(proposed) if t != NL] != [t for t in TOKEN.findall(text) if t != NL]:
            reasons.append('non_newline_control_sequence_changed')
        if reasons:
            held.append({'id': row['id'], 'category': row['category'], 'reasons': sorted(set(reasons))})
            continue
        descriptor = {'id': row['id'], 'category': row['category'], 'source': row['source'],
            'current_text': text, 'proposed_text': proposed, 'proposed_display': row['proposed_display'],
            'window_budget': row['kb'], 'status': 'ENCODING_AND_KNOWN_WINDOW_PREREQUISITES_PASS_NOT_BUILT_OR_RUNTIME_VERIFIED'}
        if row['category'] == '固定说明':
            at = int(original['source'], 16)
            old, missing, errors = encode(text.replace(NL, ' '), mapping, battle=False)
            new, nmissing, nerrors = encode(proposed.replace(NL, ' '), mapping, battle=False)
            size = rom[at]
            if missing or errors or nmissing or nerrors or rom[at + 1:at + 1 + size] != old:
                held.append({'id': row['id'], 'category': row['category'], 'reasons': ['current_description_encoding_readback_mismatch']})
                continue
            if len(new) > 63:
                held.append({'id': row['id'], 'category': row['category'], 'reasons': ['description_encoded_capacity_exceeded']})
                continue
            descriptor.update(old_bytes=len(old), new_bytes=len(new), fixed_record_capacity=63,
                current_readback_exact=True, new_encoded_hex=new.hex(' ').upper())
        elif row['category'] == '剧情与对白':
            rec = base[row['id']]
            at, actual, tail = payload(rom, rec)
            old, missing, errors = encode(text, mapping, battle=False)
            new, nmissing, nerrors = encode(proposed, mapping, battle=False)
            if missing or errors or nmissing or nerrors or actual != old:
                held.append({'id': row['id'], 'category': row['category'], 'reasons': ['current_event_encoding_or_alias_readback_mismatch']})
                continue
            descriptor.update(old_bytes=len(old), new_bytes=len(new), current_payload_file=f'{at:06X}',
                return_hex=tail.hex(' ').upper(), current_readback_exact=True,
                grows_and_needs_relocation=len(new) > len(old), new_encoded_hex=new.hex(' ').upper())
        else:
            raise AssertionError(row['category'])
        candidates.append(descriptor)
    assert sha(rompath.read_bytes()) == sha(rom)
    assert generated_changed == len(candidates) + len(held)
    result = {'status': 'V3_READONLY_PREWRITE_PREREQUISITE_AUDIT_COMPLETE_NO_ROM_WRITE',
        'ROM': manifest['latest_test_ROM']['file'], 'ROM_SHA256': sha(rom), 'HTML_SHA256': layouts['HTML_SHA256'],
        'default_preview_budget': [10, 4], 'generated_changed_records': generated_changed,
        'candidates_for_test_build_preparation': len(candidates),
        'candidate_categories': dict(collections.Counter(r['category'] for r in candidates)),
        'held_records': len(held), 'held_reason_counts': dict(collections.Counter(reason for r in held for reason in r['reasons'])),
        'growing_event_payloads': sum(bool(r.get('grows_and_needs_relocation')) for r in candidates),
        'candidates': candidates, 'held': held,
        'not_ready_for_full_ROM_application': True, 'ROM_unchanged': True,
        'remaining_before_any_build': ['Review selected Chinese layouts, rather than treat HTML display as approval.',
            'Validate current directory aliases/shared payloads and reserved arenas before choosing in-place writes or relocation.',
            'Retain original source keys, return addresses and event end16 guards; validate complete byte-diff allowlists.',
            'Build a separately named test ROM only after the intended write scope is authorized.',
            'Run original scene/window tests before recommending a playable release.'],
        'v3_kb_is_not_always_a_confirmed_window': '185 indexed-description records have a provisional 13x2 kb; this audit excludes them.',
        'limits': 'This is a prerequisite screen, not a completed ROM build, allocator audit or gameplay validation.'}
    (P / 'qa/LAYOUT_V3_PREWRITE_READINESS_20261016_01.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ['generated_changed_records', 'candidates_for_test_build_preparation',
        'candidate_categories', 'held_records', 'held_reason_counts', 'growing_event_payloads', 'ROM_unchanged']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
