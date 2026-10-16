"""Read the current ROM and sources; emit layout evidence only, never a ROM."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from dry_run_encoding_plan import encode

P = Path(__file__).resolve().parents[1]
OUT = P / 'qa/LINEBREAK_READONLY_ANALYSIS_20261016_01.json'
TOKEN = re.compile(r'\{[^{}]+\}')


def rd(path):
    return json.loads((P / path).read_text(encoding='utf-8-sig'))


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def file_offset(cpu):
    if 0x3E8000 <= cpu < 0x400000:
        return cpu + 0x400000
    return cpu - 0xC00000 if cpu >= 0xC00000 else cpu


def payload(rom, rec):
    src, resume = int(rec['source'], 16), int(rec['resume'], 16)
    bank = src >> 16
    bank = bank | 0xC0 if bank < 0x40 else bank
    desc = 0x3FF800 + bank * 5
    n = int.from_bytes(rom[desc:desc + 2], 'little')
    tab = file_offset(int.from_bytes(rom[desc + 2:desc + 5], 'little'))
    keys = [int.from_bytes(rom[tab + i * 2:tab + i * 2 + 2], 'little') for i in range(n)]
    assert keys == sorted(set(keys))
    ptr = tab + n * 2 + keys.index(src & 65535) * 3
    at = file_offset(int.from_bytes(rom[ptr:ptr + 3], 'little'))
    tail = b'\xff' + ((bank << 16) | (resume & 65535)).to_bytes(3, 'little')
    end = rom.find(tail, at, at + 8192)
    assert end >= at, (rec['id'], hex(at))
    return at, rom[at:end], tail


def main():
    manifest = rd('text/translations/translation_sources_current.json')
    rompath = P / manifest['latest_test_ROM']['file']
    rom = rompath.read_bytes()
    before = sha(rom)
    assert before == manifest['latest_test_ROM']['SHA256']
    base = rd('docs/ALINE_V10AJ264_BATCH263B_STORY_20261008_05.json')
    typed = rd(manifest['latest_typed_review'])['translations']
    overlay = rd(manifest['latest_dialogue_overlay'])['translations']
    mapping = {k: bytes.fromhex(v) for k, v in rd(manifest['latest_font_mapping']).items() if len(k) == 1}
    reviewed = {r['text_id']: r['translation_zh_cn'] for r in typed if r['id'].startswith('C')}
    verified, unresolved = [], []
    screenshot = None
    for rec in base['records']:
        at, actual, tail = payload(rom, rec)
        text = overlay.get(rec['source'], reviewed.get(rec['id'], rec['zh']))
        if text == rec['zh'] and actual == bytes.fromhex(rec['encoded']):
            verified.append((rec, text))
        else:
            encoded, missing, errors = encode(text, mapping, battle=False)
            if not missing and not errors and actual == encoded:
                verified.append((rec, text))
            else:
                # Later per-scene overlays are not inferred from old prose.
                unresolved.append({'id': rec['id'], 'source': rec['source'],
                                   'current_payload_file': f'{at:06X}',
                                   'reason': 'not identical to these baseline/latest-review inputs; later overlays require separate reconciliation'})
        if rec['source'] == '0x3C0DCB':
            assert text == rec['zh'] and actual == bytes.fromhex(rec['encoded'])
            original = text
            proposed = text.replace('取代{NEWLINE}{CHARACTER_NAME:05}', '取代{CHARACTER_NAME:05}')
            # In-memory preview changes only one newline, no words/macros/control order.
            assert original.replace('{NEWLINE}', '') == proposed.replace('{NEWLINE}', '')
            assert [x for x in TOKEN.findall(original) if x != '{NEWLINE}'] == [x for x in TOKEN.findall(proposed) if x != '{NEWLINE}']
            expansion = {'{CHARACTER_NAME:05}': '米迦勒', '{LOCATION:08}': '罗亚努', '{BUTTON_WAIT}': ''}
            def display(s):
                for a, b in expansion.items():
                    s = s.replace(a, b)
                return s.split('{NEWLINE}')
            screenshot = {'issue': 'LAYOUT-LINEBREAK-001', 'source': rec['source'], 'text_id': rec['id'],
                'current_payload_file': f'{at:06X}', 'current_payload_hex': actual.hex(' ').upper(),
                'return_hex': tail.hex(' ').upper(), 'current_ROM_readback_exact': True,
                'source_file': 'text/translations/utterances_batch01_v1.json',
                'original_Japanese': 'そこで{CHARACTER_NAME:05}に代わって、{NEWLINE}この私が{LOCATION:08}侯になる。{BUTTON_WAIT}',
                'current_text': original, 'current_lines': display(original),
                'current_line_cells_for_screenshot_names': list(map(len, display(original))),
                'preview_only_text': proposed, 'preview_only_lines': display(proposed),
                'preview_line_cells_for_screenshot_names': list(map(len, display(proposed))),
                'diagnosis': 'Chinese source contains two explicit NEWLINE controls; first is an added early break before the dynamic name. It is not forced by the screenshot window edge.',
                'non_newline_tokens_and_text_preserved_in_preview': True,
                'native_scene_replay': 'not performed; user has no save; source/payload cause confirmed, future scene validation still needed',
                'exact_window_capacity': 'not inferred from screenshot; must measure its actual text origin/right edge/line height at repair time'}
    assert screenshot

    # Review leads only: these are not counts of bugs. Flow, names and window
    # context are deliberately not guessed from isolated source units.
    candidates = []
    for rec, text in verified:
        if rec['kind'] != 'utterance' or '{NEWLINE}' not in text:
            continue
        reasons = []
        if re.search(r'\{NEWLINE\}[，。、；：！？）】》]', text):
            reasons.append('closing_punctuation_immediately_after_explicit_newline')
        for line in text.split('{NEWLINE}')[1:-1]:
            literal = TOKEN.sub('', line)
            if '{' not in line and 1 <= len(literal) <= 3:
                reasons.append('very_short_middle_line_context_review_required')
                break
        if reasons:
            candidates.append({'id': rec['id'], 'source': rec['source'], 'reasons': reasons, 'text': text})
    after = sha(rompath.read_bytes())
    assert after == before
    result = {
        'schema': 'readonly-linebreak-analysis-v1', 'date': '2026-10-16',
        'status': 'ANALYSIS_AND_PREVIEW_ONLY_NO_ROM_WRITE',
        'ROM': manifest['latest_test_ROM']['file'], 'ROM_SHA256_before': before,
        'ROM_SHA256_after': after, 'ROM_unchanged': True,
        'screenshot': screenshot,
        'source_readback_inventory': {
            'baseline_units': len(base['records']), 'verified_against_current_ROM': len(verified),
            'verified_kinds': dict(Counter(r['kind'] for r, t in verified)),
            'verified_utterances_with_explicit_newline': sum(r['kind'] == 'utterance' and '{NEWLINE}' in t for r, t in verified),
            'later_overlay_reconciliation_needed': len(unresolved), 'unresolved': unresolved,
            'review_candidates_count': len(candidates),
            'review_candidates_are_not_confirmed_bugs': True,
            'review_candidates': candidates,
            'limits': ['Static payload inventory is not execution-path or all-scene coverage.',
                       'Short lines may be intentional; WAIT/page/window/choice/poetry context must be reviewed.',
                       'Dynamic expanded widths and actual window capacities are not supplied by this scan.']},
        'existing_tool_limits': {
            'tools/audit_utterance_layout_v1.py': 'default 10-character narrow-bubble upper bound; old build142 names; guessed party/item widths; no contextual window width, underfill, language or complete-flow checks',
            'tools/normalize_event_translation_controls.py': 'historical draft tool redistributes literal text proportionally to original slots and restores original tokens; not a Chinese semantic reflow engine; not established as the cause of this screenshot',
            'tools/build_v284_display_feedback_v1.py': 'wrap13 handles 431 fixed description records: max two lines, native 0x50 separator, 64-byte record; not a universal dialogue rule'},
        'repair_deferred': True, 'translation_payload_sources_modified': False,
        'report': 'docs/LINEBREAK_ANALYSIS_AND_REPAIR_PLAN_20261016_01.md'}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'status': result['status'], 'verified_units': len(verified),
                      'needs_overlay_reconciliation': len(unresolved), 'review_leads': len(candidates),
                      'screenshot_before': screenshot['current_lines'], 'screenshot_preview': screenshot['preview_only_lines'],
                      'ROM_unchanged': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
