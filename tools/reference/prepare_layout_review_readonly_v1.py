"""Inventory current text/window evidence and write offline previews only.

No builders/emulators are invoked. All outputs are confined to qa/layout_review_*.
Unknown callers, controls and capacities stay explicitly pending.
"""
from __future__ import annotations

import collections
import argparse
import csv
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

from audit_linebreak_feedback_readonly_v1 import file_offset, payload
from dry_run_encoding_plan import encode
from layout_preview_core_v1 import NL, TOKEN, control_sequence, expand, line_cells, term_index, wrap
from rs3_text_ops import op_len

P = Path(__file__).resolve().parents[1]
D = P / 'qa/layout_review_20261016_02'
TWO = set(range(0x10, 0x17)) | {0x18, 0x19, 0x20, 0x21, 0x22, 0x23, 0x46}
rd = lambda f: json.loads((P / f).read_text(encoding='utf-8-sig'))
sha = lambda z: hashlib.sha256(z).hexdigest().upper()


def source_len(rom, at):
    # The exact-source adapter v2 distinguishes queued controls 18/46 from glyphs.
    b = rom[at]
    if b in (0x18, 0x46):
        return 2 if rom[at + 1] >= 0x10 else (2 if b == 0x18 else 1)
    if b == 0x4C:
        return 1 if int.from_bytes(rom[at:at + 2], 'little') in (0x084C, 0x2E4C, 0x4E4C) else 2
    return op_len(rom, at)


def native_roots(rom):
    for bank in (0x3A, 0x3B, 0x3C):
        previous = 0
        for i in range(1024):
            end = int.from_bytes(rom[(bank << 16) + i * 2:(bank << 16) + i * 2 + 2], 'little') + 0x800
            start = previous + 0x800
            previous = end - 0x800
            if 0x800 <= start < end <= 65535:
                yield f'{((bank - 0x3A) << 10) + i:04X}', (bank << 16) + start, (bank << 16) + end
    for base, table in [(0x0C00, 0x5AA970), (0x0E00, 0x5AF800), (0x4C00, 0x5EF500)]:
        for i in range(256):
            cpu = int.from_bytes(rom[table + i * 3:table + i * 3 + 3], 'little')
            at = file_offset(cpu)
            if 0 <= at < len(rom) and cpu not in (0, 0xFFFFFF):
                yield f'{base + i:04X}', at, min(len(rom), (at & ~65535) + 65536)


def window_contexts(source, records):
    """Local straight-line evidence, not a full conditional CFG oracle.

    Calls are followed with inherited context, but their return effects are not
    guessed. Conditional/queued calls invalidate context until re-established.
    """
    bykey = {int(r['source'], 16): r for r in records}
    hits = collections.defaultdict(list)
    scanned = set()
    stops = collections.Counter()
    operations = 0

    def walk(root, start, end, mode=None, profile=None, depth=0):
        nonlocal operations
        if depth > 10:
            stops['call_depth_limit'] += 1
            return
        choice, anchor = False, None
        at = start
        while at < end and operations < 1500000:
            state = (at, mode, profile, choice)
            if state in scanned:
                return
            scanned.add(state)
            operations += 1
            if at in bykey:
                rec = bykey[at]
                info = {'root': root, 'mode': mode, 'profile': profile, 'choice': choice,
                        'window_anchor': anchor, 'evidence': 'local_source_decode_not_runtime_replay'}
                if info not in hits[at]:
                    hits[at].append(info)
                at = int(rec['resume'], 16)
                if any(t.startswith(('{WINDOW', '{CHOICE', '{CODE:3C', '{CODE:4F')) for t in TOKEN.findall(rec['zh'])):
                    mode, profile, choice = None, None, True
                continue
            n = source_len(source, at)
            if not n or at + n > end:
                stops['unknown_or_truncated_source_op'] += 1
                return
            b = source[at]
            if b == 0x43 or b == 0x2E:
                return
            if b == 0x4D:
                mode = 1
            elif b == 0x4F and source[at + 1] in (0x1A, 0x1B, 0x1D):
                mode = {0x1A: 2, 0x1B: 3, 0x1D: 0}[source[at + 1]]
            elif b in (0x28, 0x29):
                profile = f'field_mode_{mode}' if mode is not None else None
                choice, anchor = False, f'{at:06X}'
            elif b == 0x3C:
                selector = source[at + n - 1] & 0x7F
                profile = f'field_template_{selector:02X}' if selector >= 8 else None
                choice, anchor = False, f'{at:06X}'
            elif b == 0x2A:
                profile, choice = None, False
            elif b in (0x25, 0x26, 0x27):
                choice = True
            elif b == 0x0D and source[at + 1] in (0x17, 0x18):
                target = file_offset(int.from_bytes(source[at + 2:at + 5], 'little'))
                if 0 <= target < len(source):
                    walk(root + f'/call@{at:06X}', target, min(len(source), (target & ~65535) + 65536), mode, profile, depth + 1)
                if source[at + 1] == 0x17:
                    return
                mode, profile = None, None
            elif b in (0x08, 0x0B, 0x0C, 0x4C) or (b == 0x0D and source[at + 1] in (0x16, 0x19, 0x20)):
                mode, profile = None, None
            at += n
        if operations >= 1500000:
            stops['operation_budget'] += 1

    for root, start, end in native_roots(source):
        walk(root, start, end)
    return hits, {'decoded_states': operations, 'stop_reasons': dict(stops),
                  'scope': 'Native table roots and explicit long calls; conditional branch targets and indirect calls are not fully resolved.'}


def main():
    global D
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-dir', default='qa/layout_review_20261016_02')
    args = parser.parse_args()
    D = (P / args.review_dir).resolve()
    assert D.is_relative_to((P / 'qa').resolve()) and D.name.startswith('layout_review_')
    assert D.resolve().is_relative_to(P.resolve())
    D.mkdir(exist_ok=True)
    manifest = rd('text/translations/translation_sources_current.json')
    rompath = P / manifest['latest_test_ROM']['file']
    rom = rompath.read_bytes()
    source = (P / '../roms/source/bokuno_proto_1.123_analysis.sfc').read_bytes()
    assert sha(rom) == manifest['latest_test_ROM']['SHA256']
    assert sha(source) == '4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0'
    base = rd('docs/ALINE_V10AJ264_BATCH263B_STORY_20261008_05.json')['records']
    typed = rd(manifest['latest_typed_review'])['translations']
    overlay = rd(manifest['latest_dialogue_overlay'])['translations']
    older_overlay = rd('text/translations/tavern_feedback_overlay_v272_20261010_01.json')['translations']
    mapping = {c: bytes.fromhex(z) for c, z in rd(manifest['latest_font_mapping']).items() if len(c) == 1}
    pairs = {c: bytes.fromhex(z) for c, z in rd(manifest['latest_fixed_menu_pairs']).items()}
    reverse = {z: c for c, z in (mapping | pairs).items()}
    reverse.update({bytes.fromhex('20 A3'): '王', bytes.fromhex('19 54'): '算'})
    reviewed = {r['text_id']: r['translation_zh_cn'] for r in typed if r['id'].startswith('C')}
    typed_offsets = {int(r['source_offset'], 16): r for r in typed if r.get('source_offset')}

    # Immutable inputs and all ROMs already in roms/work are guarded. Hashing
    # the entire ROM archive is unnecessary: sizes/mtimes plus current SHA are
    # recorded, and this program has no ROM-writing entry point.
    rom_snapshot = {str(f.relative_to(P)): [f.stat().st_size, f.stat().st_mtime_ns] for f in (P / 'roms/work').glob('*') if f.is_file()}
    protected_paths = {manifest['latest_typed_review'], manifest['latest_dialogue_overlay'], manifest['latest_items'],
                       manifest['latest_techniques_and_spells'], 'text/translations/utterances_batch01_v1.json'}
    input_hashes = {f: sha((P / f).read_bytes()) for f in protected_paths}

    def decode(raw, mode='fixed'):
        result, unknown, at = [], [], 0
        while at < len(raw):
            b = raw[at]
            if mode == 'event' and b in (0x39, 0x3A, 0x3B, 0x4A):
                name = {0x39: 'PARTY_NAME', 0x3A: 'ITEM_NAME', 0x3B: 'LOCATION', 0x4A: 'CHARACTER_NAME'}[b]
                result.append(f'{{{name}:{raw[at + 1]:02X}}}'); at += 2; continue
            if b == 0x24 and mode != 'fixed':
                result.append(NL); at += 1; continue
            if (mode == 'event' and b == 0x2B) or (mode == 'battle' and b == 0x25):
                result.append(f'{{WAIT:{raw[at + 1]:02X}}}'); at += 2; continue
            if mode == 'event' and b == 0x2C:
                result.append('{BUTTON_WAIT}'); at += 1; continue
            if mode == 'battle' and 0x26 <= b <= 0x29:
                result.append(f'{{CODE:{b:02X}}}'); at += 1; continue
            if mode == 'battle' and b == 0x2A:
                result.append(f'{{CODE:2A{raw[at + 1]:02X}}}'); at += 2; continue
            if b == 0x50:
                result.append(' '); at += 1; continue
            n = 2 if b in TWO else 1
            code = raw[at:at + n]
            if code in reverse:
                result.append(reverse[code])
            else:
                value = f'{{CODE:{code.hex().upper()}}}'
                result.append(value); unknown.append(value)
            at += n
        return ''.join(result), unknown

    profiles = {}
    templates = []
    for i in range(0x29):
        at = 0x3DEB00 + i * 16
        z = rom[at:at + 16]
        assert z == source[at:at + 16]
        rec = {'id': f'field_template_{i:02X}', 'label': f'剧情框模板 {i:02X}', 'ROM_offset': f'{at:06X}',
               'raw': z.hex(' ').upper(), 'tile_width': z[2], 'tile_height': z[3],
               'text_inset_tiles': [z[7], z[8]], 'columns': z[9], 'rows': z[10],
               'capacity_evidence': 'original native descriptor + C012B7 loader; unchanged in v290',
               'capacity_use': 'Conservative native logical-column budget, not a claim about maximum CJK pixel packing.',
               'runtime_scene_verified': False}
        profiles[rec['id']] = rec
        templates.append(rec)
    # Native 4D sets D599=1. Sub-4F 1A/1B/1D set 2/3/0 respectively.
    for at, data in [(0x2267, 'A9 01 8D 99 D5'), (0x226F, 'A9 02 8D 99 D5'),
                     (0x2277, 'A9 03 8D 99 D5'), (0x227F, '9C 99 D5')]:
        assert rom[at:at + len(bytes.fromhex(data))] == source[at:at + len(bytes.fromhex(data))] == bytes.fromhex(data)
    for at, value in [(0x3B30, 0x2267), (0x3B6A, 0x226F), (0x3B6C, 0x2277), (0x3B70, 0x227F)]:
        assert int.from_bytes(rom[at:at + 2], 'little') == int.from_bytes(source[at:at + 2], 'little') == value
    for mode in range(4):
        variants = templates[mode * 8:mode * 8 + 8]
        assert len({(r['columns'], r['rows']) for r in variants}) == 1
        profiles[f'field_mode_{mode}'] = {'id': f'field_mode_{mode}', 'label': ['普通宽框', '普通窄框', '普通两行小框', '普通单行小框'][mode],
            'columns': variants[0]['columns'], 'rows': variants[0]['rows'],
            'variant_templates': [r['id'] for r in variants], 'runtime_scene_verified': False,
            'capacity_evidence': 'Native size-mode handler + eight equal-capacity position variants'}
    profiles['fixed_description_13x2'] = {'id': 'fixed_description_13x2', 'label': '固定说明框', 'columns': 13, 'rows': 2,
        'capacity_evidence': 'v284 actual display feedback and bounded 64-byte description records', 'runtime_scene_verified': 'existing v284 evidence, no new replay'}
    contexts, context_stats = window_contexts(source, base)

    # Actual current fixed bytes are the name expansion evidence, with current
    # full-name exception sources added to the protected term dictionary.
    tables = rd('text/extracted/fixed_tables.json')['tables']
    fixed_rows, names, terms = [], {}, []
    occupied = set()
    for table, data in tables.items():
        for rec in data['records']:
            at, cap = int(rec['offset'], 16), rec['record_size']
            occupied.add((at, cap))
            raw = rom[at:at + cap]
            if not raw or all(b in (0x50, 0) for b in raw):
                continue
            text, unknown = decode(raw.rstrip(b'\x50'))
            if table == 'character_or_graphic_names':
                names[f'{{CHARACTER_NAME:{rec["id"]:02X}}}'] = (text, len(text))
            if table == 'titles_locations_names_10' and rec['id'] >= 0x20:
                names[f'{{LOCATION:{rec["id"] - 0x20:02X}}}'] = (text, len(text))
            if not unknown:
                terms.append(text)
            fixed_rows.append({'id': f'fixed:{table}:{rec["id"]:03X}', 'category': '固定名称与栏位', 'source': f'{at:06X}',
                'text': text, 'raw_hex': raw.hex(' ').upper(), 'capacity_bytes': cap, 'unknown_glyphs': unknown,
                'proposal': text, 'proposal_status': 'fixed_field_no_reflow', 'flags': ['display_consumer_not_inferred_from_storage_capacity']})
    # Special F0..FF character aliases are runtime-dependent, not ordinary rows.
    names = {k: v for k, v in names.items() if '{CHARACTER_NAME:F' not in k and not TOKEN.search(v[0])}
    for r in rd(manifest['latest_items'])['translations']:
        terms.append(r.get('display_zh_cn') or r['translation_zh_cn'])
        at, cap = int(r['offset'], 16), r['record_bytes']
        if (at, cap) not in occupied:
            occupied.add((at, cap))
            raw = rom[at:at + cap]; text, unknown = decode(raw.rstrip(b'\x50'))
            fixed_rows.append({'id': 'item:' + r['text_id'], 'category': '固定名称与栏位', 'source': f'{at:06X}',
                'text': text, 'raw_hex': raw.hex(' ').upper(), 'capacity_bytes': cap, 'unknown_glyphs': unknown,
                'proposal': text, 'proposal_status': 'fixed_field_no_reflow', 'flags': ['existing_full_name_interface_preserved'],
                'full_interface_spelling': r.get('display_zh_cn') or r['translation_zh_cn']})
    for i in range(85):
        at, cap = 0x5E69B0 + i * 16, 16
        raw = rom[at:at + cap]
        if raw == b'\x50' * cap:
            continue
        text, unknown = decode(raw.rstrip(b'\x50'))
        fixed_rows.append({'id': f'quest_title:{i:02X}', 'category': '固定名称与栏位', 'source': f'{at:06X}',
            'text': text, 'raw_hex': raw.hex(' ').upper(), 'capacity_bytes': cap, 'unknown_glyphs': unknown,
            'proposal': text, 'proposal_status': 'fixed_field_no_reflow', 'flags': ['single_line_name']})
        if not unknown:
            terms.append(text)
    for r in rd(manifest['latest_techniques_and_spells'])['spells']:
        terms.append(r['zh'])
        at = int(r['name_offset'], 16)
        if (at, 10) not in occupied:
            raw = rom[at:at + 10]; text, unknown = decode(raw.rstrip(b'\x50'))
            fixed_rows.append({'id': 'spell:' + r['id'], 'category': '固定名称与栏位', 'source': f'{at:06X}', 'text': text,
                'raw_hex': raw.hex(' ').upper(), 'capacity_bytes': 10, 'unknown_glyphs': unknown,
                'proposal': text, 'proposal_status': 'fixed_field_no_reflow', 'flags': ['single_line_name']})
    word_input = D / 'segmentation_input.json'
    word_output = D / 'segmentation_terms.json'
    corpus = [r['zh'] for r in base] + list(overlay.values()) + [r['translation_zh_cn'] for r in typed]
    corpus += [r['display_text'] for r in rd('qa/V284_DISPLAY_FEEDBACK_BUILD_20261011_05.json')['description_layout_rows']]
    word_input.write_text(json.dumps({'texts': corpus}, ensure_ascii=False), encoding='utf8')
    segmented = subprocess.run(['G:/Hermes/home/node/node.exe', str(P / 'tools/segment_layout_terms_readonly_v1.mjs'),
                                str(word_input), str(word_output)], capture_output=True, timeout=60)
    assert segmented.returncode == 0, segmented.stderr.decode(errors='replace')
    terms += json.loads(word_output.read_text(encoding='utf8'))['words']
    termmap = term_index(terms)

    records, failures, reconciliation = [], [], []
    known_keys = set()
    for rec in base:
        at, raw, tail = payload(rom, rec)
        text = overlay.get(rec['source'], reviewed.get(rec['id'], older_overlay.get(rec['source'], rec['zh'])))
        special = None
        if rec['source'] == '0x3B1340':
            text = rec['zh'].replace('公爵，', '公爵，' + NL)
            special = 'v268 exact local newline overlay'
        localmap = mapping
        if rec['source'] == '0x4D6A1A':
            localmap = mapping | {'王': bytes.fromhex('20 A3')}; special = 'v279 same-character 王 display alias'
        if rec['source'] == '0x4D6A58':
            localmap = mapping | {'算': bytes.fromhex('19 54')}; special = 'v279 same-character 算 cancel-only display alias'
        if raw == bytes.fromhex(rec['encoded']) and text == rec['zh']:
            verified = True
        else:
            encoded, missing, errors = encode(text, localmap, battle=False)
            verified = not missing and not errors and raw == encoded
        if not verified:
            failures.append(rec['id'])
        if special or rec['source'] in older_overlay:
            reconciliation.append({'id': rec['id'], 'source': rec['source'], 'reason': special or 'v272 tavern overlay', 'exact_readback': verified})
        key = int(rec['source'], 16)
        known_keys.add(key)
        ctx = contexts.get(key, [])
        ids = sorted({x['profile'] for x in ctx if x['profile'] in profiles})
        unknown_context = not ctx or any(x['profile'] not in profiles for x in ctx)
        ps = [profiles[x] for x in ids]
        limit = min((x['columns'] for x in ps), default=10)
        rows = min((x['rows'] for x in ps), default=4)
        flags = []
        if unknown_context:
            flags.append('window_or_caller_pending')
        if len(ids) > 1:
            flags.append('multiple_window_contexts_use_smallest_budget')
        if any(x['choice'] for x in ctx):
            flags.append('choice_rows_preserved')
        if rec['kind'] != 'utterance' or 'branchmerge' in rec['id']:
            flags.append('fragment_or_join_needs_complete_flow')
        if text[:1] and text[:1] in '，。、；：！？）》】」』':
            flags.append('fragment_or_join_needs_complete_flow')
        if text[:1] and text[:1] in '们的地得':
            flags.append('fragment_or_join_needs_complete_flow')
        if not verified:
            flags.append('payload_source_reconciliation_pending')
        before_cells = line_cells(text, names)
        if before_cells is None:
            flags.append('dynamic_or_control_width_pending')
        elif max(before_cells, default=0) > limit:
            flags.append('explicit_line_exceeds_budget_check_native_autowrap')
        if flags and any(x in flags for x in ['choice_rows_preserved', 'fragment_or_join_needs_complete_flow', 'payload_source_reconciliation_pending']):
            proposal, status = text, 'structural_context_pending'
        else:
            proposal, status = wrap(text, limit, rows, termmap, names, keep_natural_breaks=True)
        after_cells = line_cells(proposal, names)
        if status == 'changed':
            assert after_cells is not None and max(after_cells) <= limit and len(after_cells) <= rows
            assert text.replace(NL, '') == proposal.replace(NL, '') and control_sequence(text) == control_sequence(proposal)
        records.append({'id': rec['id'], 'category': '剧情与对白', 'source': rec['source'], 'text': text,
            'proposal': proposal, 'proposal_status': status, 'display_before': expand(text, names), 'display_after': expand(proposal, names),
            'columns_budget': limit, 'rows_budget': rows, 'before_cells': before_cells, 'after_cells': after_cells,
            'window_profiles': ids, 'window_contexts': ctx, 'flags': flags, 'payload_verified': verified,
            'current_payload_file': f'{at:06X}', 'ready_for_review': status == 'changed' and not unknown_context and not any('pending' in f for f in flags)})
    assert not failures, failures

    # Account for the entire live shadow directory, including post-v264 additions.
    extra_keys = []
    for bank in range(256):
        desc = 0x3FF800 + bank * 5
        count = int.from_bytes(rom[desc:desc + 2], 'little')
        if not count:
            continue
        tab = file_offset(int.from_bytes(rom[desc + 2:desc + 5], 'little'))
        for i in range(count):
            key = (bank << 16) | int.from_bytes(rom[tab + i * 2:tab + i * 2 + 2], 'little')
            keyfile = file_offset(key)
            if keyfile in known_keys:
                continue
            pointer = file_offset(int.from_bytes(rom[tab + 2 * count + 3 * i:tab + 2 * count + 3 * i + 3], 'little'))
            end = rom.find(b'\xff', pointer, pointer + 2048)
            assert end >= pointer
            raw = rom[pointer:end]
            text, unknown = decode(raw, 'event')
            extra_keys.append({'source': f'{keyfile:06X}', 'payload_file': f'{pointer:06X}', 'text': text})
            records.append({'id': f'extra_shadow:{keyfile:06X}', 'category': '新增文字入口', 'source': f'{keyfile:06X}',
                'text': text, 'proposal': text, 'proposal_status': 'structural_context_pending', 'flags': ['caller_and_choice_layout_pending'],
                'unknown_glyphs': unknown, 'raw_hex': raw.hex(' ').upper()})

    # Fixed 64-byte descriptions: current payload must exactly match v284 final.
    desc_rows = rd('qa/V284_DISPLAY_FEEDBACK_BUILD_20261011_05.json')['description_layout_rows']
    for rec in desc_rows:
        at = int(rec['offset'], 16); size = rom[at]; raw = rom[at + 1:at + 1 + size]
        assert raw == bytes.fromhex(rec['payload_hex']), rec['id']
        text = NL.join(rec['rendered_lines'])
        proposal, status = wrap(text, 13, 2, termmap, {})
        encoded, missing, errors = encode(proposal.replace(NL, ' '), mapping, battle=False)
        if status == 'changed' and (missing or errors or len(encoded) > 63):
            proposal, status = text, 'encoding_capacity_pending'
        records.append({'id': 'description:' + rec['id'], 'category': '固定说明', 'source': f'{at:06X}', 'text': text,
            'proposal': proposal, 'proposal_status': status, 'display_before': text.replace(NL, '\n'), 'display_after': proposal.replace(NL, '\n'),
            'window_profiles': ['fixed_description_13x2'], 'columns_budget': 13, 'rows_budget': 2,
            'before_cells': line_cells(text, {}), 'after_cells': line_cells(proposal, {}), 'flags': [], 'payload_verified': True,
            'ready_for_review': status == 'changed', 'capacity_bytes': 63})

    # Separate indexed descriptions use native spaces as line separators; their
    # display consumers are not equated to the 431 fixed description boxes.
    pointers = [int.from_bytes(rom[0x3D6000 + i * 2:0x3D6002 + i * 2], 'little') for i in range(186)]
    assert pointers == sorted(pointers)
    for i in range(185):
        at = 0x3D6200 + pointers[i]; raw = rom[at:0x3D6200 + pointers[i + 1]]
        text, unknown = decode(raw)
        text = text.replace(' ', NL)
        proposal, status = wrap(text, 13, 2, termmap, {}) if not unknown else (text, 'glyph_context_pending')
        records.append({'id': f'indexed_description:{i:03X}', 'category': '索引说明', 'source': f'{at:06X}',
            'text': text, 'proposal': proposal, 'proposal_status': status, 'display_before': text.replace(NL, '\n'),
            'display_after': proposal.replace(NL, '\n'), 'columns_budget': 13, 'rows_budget': 2,
            'flags': ['consumer_window_pending_13x2_is_preview_only'], 'unknown_glyphs': unknown})

    # Indexed menu strings, fixed-width native cache streams and added K names
    # must not be reflowed as paragraphs.
    mp = [int.from_bytes(rom[0x3D7800 + i * 2:0x3D7802 + i * 2], 'little') for i in range(566)]
    assert mp == sorted(mp)
    for i in range(565):
        at = 0x3D7D00 + mp[i]; raw = rom[at:0x3D7D00 + mp[i + 1]]
        text, unknown = decode(raw)
        records.append({'id': f'indexed_menu:{i:03X}', 'category': '菜单与交易短语', 'source': f'{at:06X}',
            'text': text, 'proposal': text, 'proposal_status': 'fixed_field_no_reflow', 'flags': ['consumer_layout_pending'],
            'unknown_glyphs': unknown, 'capacity_bytes': len(raw)})
    missing_build = rd('qa/V283_MISSING_TRANSLATIONS_BUILD_20261011_04.json')
    missing_inv = {r['id']: r for r in rd('text/extracted/missing_menu_inventory_v282_20261011_01.json')['rows']}
    for rec in missing_build['applied']:
        if rec['kind'] != 'K':
            continue
        inv = missing_inv[rec['id']]
        at = int(rec['offset'], 16)
        raw = rom[at:at + inv['capacity']]
        actual_text, unknown = decode(raw.rstrip(b'\x50'))
        # The standard record may use composite fallback glyphs; the source
        # spelling is retained alongside actual bytes and display-interface note.
        records.append({'id': 'extra_name:' + rec['id'], 'category': '固定名称与栏位', 'source': f'{at:06X}',
            'text': actual_text, 'proposal': actual_text, 'proposal_status': 'fixed_field_no_reflow',
            'flags': ['existing_full_name_interface_preserved'], 'current_raw_hex': raw.hex(' ').upper(),
            'unknown_glyphs': unknown, 'full_interface_spelling': rec['zh'], 'inventory_metadata': inv})
    for rec in missing_build['native_menu']:
        at = int(rec['offset'], 16)
        if 'payload_hex' in rec:
            n = len(bytes.fromhex(rec['payload_hex']))
        else:
            encoded, missing, errors = encode(rec['runtime_zh'], mapping, battle=False)
            assert not missing and not errors
            n = len(encoded)
        target_cells = rec.get('cells') or rec.get('pool_cells')
        if target_cells:
            n = 0
            for _ in range(target_cells):
                n += 2 if rom[at + n] in TWO else 1
        text, unknown = decode(rom[at:at + n])
        records.append({'id': 'cache:' + rec['id'], 'category': '菜单缓存与选项', 'source': f'{at:06X}',
            'text': text, 'proposal': text, 'proposal_status': 'fixed_field_no_reflow',
            'flags': ['native_subfields_and_icons_preserved'], 'unknown_glyphs': unknown, 'cells': rec.get('cells')})

    # Battle uses a different control language and an explicit length table.
    # Pointer order is not used to infer lengths.
    selectors = rd('qa/BATTLE64_ORIGINAL_SELECTOR_HEIGHT_STATIC_20261008_01.json')
    for i in range(115):
        offset = int.from_bytes(rom[0x3D9800 + i * 2:0x3D9802 + i * 2], 'little')
        length = int.from_bytes(rom[0x7F9FD0 + i * 2:0x7F9FD2 + i * 2], 'little')
        # Native ADC wraps the low 16 bits inside bank FD. Do not assume every
        # indexed offset necessarily yields a forward linear file address.
        at = 0x3D0000 | ((0x9A00 + offset) & 65535)
        raw = rom[at:at + length]
        text, unknown = decode(raw, 'battle')
        contexts_b = []
        if i >= 50:
            for r in selectors['rows'] + selectors['fixed']:
                if r['event'] == i - 50:
                    sa = file_offset(int(r['selector_CPU'], 16))
                    contexts_b.append({'selector_CPU': r['selector_CPU'], 'rows': r['lines'],
                        'original_selector_unchanged': rom[sa] == int(r['selector'], 16),
                        'scope': 'original selector metadata only; current natural scene replay pending'})
        records.append({'id': f'battle:{i:03X}', 'category': '战斗提示' if i < 50 else '战斗剧情', 'source': f'{at:06X}',
            'text': text, 'proposal': text, 'proposal_status': 'battle_context_pending', 'flags': ['battle_control_language', 'actual_window_width_pending'],
            'unknown_glyphs': unknown, 'selector_contexts': contexts_b, 'byte_length': length})
    records.extend(fixed_rows)
    raw = rom[0x3D77FB:0x3D7800]
    text, unknown = decode(raw)
    records.append({'id': 'inline_label:weapon_growth', 'category': '菜单与交易短语', 'source': '3D77FB',
        'text': text, 'proposal': text, 'proposal_status': 'fixed_field_no_reflow',
        'raw_hex': raw.hex(' ').upper(), 'capacity_bytes': 5, 'unknown_glyphs': unknown,
        'flags': ['direct_inline_label_preserved'], 'evidence': 'qa/V276_HIDDEN_GROWTH_LABEL_BUILD_20261010_01.json'})

    # Coverage is by stable logical index for repacked pools, never their old
    # source offsets. Every current reviewed record and item must be accounted.
    ids = {r['id'] for r in records}
    source_offsets = {int(r['source'], 16) for r in records}
    typed_coverage = []
    for rec in typed:
        text_id = rec['text_id']
        filename = rec['file'].replace('\\', '/').rsplit('/', 1)[-1]
        if text_id in ids:
            evidence = 'event_text_id'
        elif filename == '10_descriptions_stars.md':
            assert f'indexed_description:{int(text_id.rsplit("_", 1)[1], 16):03X}' in ids, text_id
            evidence = 'current_indexed_description_index'
        elif filename == '11_menu_trade_system.md' and text_id.startswith('indexed_indexed_pool_3d7d00_'):
            assert f'indexed_menu:{int(text_id.rsplit("_", 1)[1], 16):03X}' in ids, text_id
            evidence = 'current_indexed_menu_index'
        elif filename == '13_battle_ui_steal.md':
            assert f'battle:{int(text_id.rsplit("_", 1)[1], 16):03X}' in ids, text_id
            evidence = 'current_battle_UI_index'
        elif filename == '12_battle_messages.md':
            assert f'battle:{50 + int(text_id.rsplit("_", 1)[1], 16):03X}' in ids, text_id
            evidence = 'current_battle_event_index'
        else:
            assert int(rec['source_offset'], 16) in source_offsets, rec
            evidence = 'current_fixed_or_direct_source_offset'
        typed_coverage.append({'id': rec['id'], 'text_id': text_id, 'evidence': evidence})
    items = rd(manifest['latest_items'])['translations']
    assert all(int(r['offset'], 16) in source_offsets for r in items)
    assert any(r['source'] == '3D77FB' for r in records)

    for row in records:
        row.setdefault('display_before', row['text'].replace(NL, '\n'))
        row.setdefault('display_after', row['proposal'].replace(NL, '\n'))
        assert row['text'].replace(NL, '') == row['proposal'].replace(NL, '')
        assert control_sequence(row['text']) == control_sequence(row['proposal'])
    assert len({r['id'] for r in records}) == len(records)
    assert sha(rompath.read_bytes()) == sha(rom)
    assert all(sha((P / f).read_bytes()) == h for f, h in input_hashes.items())
    assert rom_snapshot == {str(f.relative_to(P)): [f.stat().st_size, f.stat().st_mtime_ns] for f in (P / 'roms/work').glob('*') if f.is_file()}
    runtime_windows = []
    for filename in ['qa/inn_tom_feedback_20261016_01/input002.ram', 'qa/inn_tom_feedback_20261016_01/input003.ram']:
        ram = (P / filename).read_bytes()
        index = int.from_bytes(ram[0xD5A5:0xD5A7], 'little')
        descriptor = ram[0xD5A7 + index:0xD5A7 + index + 64]
        selector = ram[0xD59C] & 0x7F
        template = profiles[f'field_template_{selector:02X}']
        assert descriptor[5] == template['tile_width'] and descriptor[6] == template['tile_height']
        assert descriptor[25] == template['columns'] and descriptor[26] == template['rows']
        runtime_windows.append({'existing_RAM': filename, 'SHA256': sha(ram), 'mode': ram[0xD599],
            'selector': f'{selector:02X}', 'tile_width': descriptor[5], 'tile_height': descriptor[6],
            'logical_columns': descriptor[25], 'logical_rows': descriptor[26], 'template_matches': True,
            'scope': 'Previously captured real user state; descriptor metadata only, not new layout execution.'})
    compositions = {'status': 'READONLY_COMPOSITION_RULES_NO_REWRITE', 'rules': [
        {'id': 'mastery', 'source_CPU': 'C2D0D4', 'current_pattern': '习得{ACTUAL_SKILL_NAME}的／奥义',
         'variant': '习得{ACTUAL_SKILL_NAME}的／识破奥义', 'evidence': manifest['latest_postbattle_composition_overlay'],
         'action': '保留v289语序；需按完整技能名核对动态框宽及两行，不使用普通对白换行器。'},
        {'id': 'item_acquired', 'source_CPU': 'C2CE72', 'current_pattern': '获得了／{ACTUAL_ITEM_NAME}',
         'evidence': 'qa/V289_POSTBATTLE_RUNTIME_PROOF_20261013_01.json',
         'action': '保留当前获得分支；物品损坏分支独立核对，原UI29不能全局替换。'},
        {'id': 'inn_price', 'source_file': '3C3954', 'example_from_actual_state': '　　5奥拉姆。',
         'evidence': 'qa/INN_TOM_FEEDBACK_ANALYSIS_20261016_01.json',
         'action': '固定三位数前导留白另案登记；比较一位、两位、三位数的起点，保留金额读取和收费。'}]}
    (D / 'composition_rules.json').write_text(json.dumps(compositions, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (D / 'runtime_window_metadata.json').write_text(json.dumps(runtime_windows, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    summary = {'schema': 'offline-layout-review-v1', 'status': 'PREVIEW_ONLY_NO_ROM_OR_TRANSLATION_PAYLOAD_WRITES',
        'preview_revision': '02_modifier_copula_and_ellipsis_feedback',
        'date': '2026-10-16', 'ROM': manifest['latest_test_ROM']['file'], 'ROM_SHA256': sha(rom),
        'inventory_records': len(records), 'categories': dict(collections.Counter(r['category'] for r in records)),
        'proposal_statuses': dict(collections.Counter(r['proposal_status'] for r in records)),
        'changed_preview_count': sum(r['text'] != r['proposal'] for r in records),
        'changed_with_known_profile_for_review': sum(bool(r.get('ready_for_review')) for r in records),
        'event_units_with_known_local_window': sum(bool(r['window_profiles']) for r in records if r['category'] == '剧情与对白'),
        'event_units_window_or_caller_pending': sum('window_or_caller_pending' in r['flags'] for r in records),
        'live_shadow_directory_entries': len(base) + len(extra_keys), 'extra_shadow_entries': extra_keys,
        'all_11875_baseline_payloads_reconciled': True, 'six_later_overlays': reconciliation,
        'inventory_records_include_alias_views_not_unique_visible_sentences': True,
        'fixed_name_unique_source_offsets': len({r['source'] for r in records if r['category'] == '固定名称与栏位'}),
        'current_typed_review_records_accounted': len(typed_coverage),
        'current_item_records_accounted': len(items),
        'existing_user_window_descriptors_checked': len(runtime_windows),
        'additional_composition_rule_groups': len(compositions['rules']),
        'window_context_scan': context_stats, 'protected_input_SHA256': input_hashes,
        'all_existing_ROM_files_metadata_unchanged': True, 'current_ROM_SHA_unchanged': True,
        'wording_and_non_newline_controls_preserved_for_all_proposals': True,
        'known_limits': ['Local source decode is not all-path execution coverage; window inheritance may remain unknown.',
            'Native descriptor column budgets are conservative; new line layouts still need real-scene verification.',
            'Unknown dynamic controls, fragments, choices, timed or formatted text are preserved and flagged.',
            'Fixed-name storage checks do not establish each visible menu-column width.',
            'Battle control language and indexed-description consumers require separate native-window validation.',
            'Extra K-name records inherit the validated v283 full-name interface; no newly claimed encoding validation.']}
    (D / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (D / 'current_review_source_coverage.json').write_text(json.dumps(typed_coverage, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (D / 'window_profiles.json').write_text(json.dumps(profiles, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (D / 'text_inventory_and_previews.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    with (D / 'review.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(['分类', '编号', '位置', '状态', '窗口列预算', '窗口行预算', '原显式断行', '建议预览', '待核事项'])
        writer.writerows([r['category'], r['id'], r['source'], r['proposal_status'], r.get('columns_budget'), r.get('rows_budget'),
                          r['display_before'], r['display_after'], '; '.join(r['flags'])] for r in records)
    write_html(records, summary, profiles)
    print(json.dumps({k: summary[k] for k in ['inventory_records', 'changed_preview_count', 'changed_with_known_profile_for_review',
        'event_units_with_known_local_window', 'event_units_window_or_caller_pending', 'all_11875_baseline_payloads_reconciled']}, ensure_ascii=False))


def write_html(records, summary, profiles):
    data = json.dumps({'rows': records, 'summary': summary, 'profiles': profiles}, ensure_ascii=False).replace('<', '\\u003c')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>中文排版检查与预览</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101816;color:#e5eee8;font:15px/1.6 "Microsoft YaHei",sans-serif}header{padding:24px 5vw;background:#192922;border-bottom:1px solid #3b5144}h1{margin:0;font-size:25px}.muted{color:#b0c4b7}.tag{display:inline-block;border:1px solid #668770;padding:2px 10px;border-radius:20px;margin-right:8px}main{padding:22px 5vw}nav{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}input,select,button{padding:10px;border:1px solid #597362;border-radius:6px;background:#20332a;color:#eef5ef;font:inherit}input{min-width:280px;flex:1}button{cursor:pointer}.card{border:1px solid #405849;background:#17251e;border-radius:10px;padding:16px;margin-bottom:16px}.row{display:grid;grid-template-columns:1fr 1fr;gap:20px}.box{background:#0c1510;border:1px solid #5c6b56;border-radius:8px;padding:16px;white-space:pre-wrap;overflow-wrap:anywhere;min-height:100px;font-size:19px;line-height:1.8}.after{border-color:#74b589}.meta{font-size:13px;color:#b0c4b7}.status{color:#a9d4b4}.stats{display:flex;flex-wrap:wrap;gap:14px}.stat{padding:12px 18px;background:#233a2d;border-radius:8px}.stat strong{font-size:25px;display:block}.pager{display:flex;gap:15px;align-items:center;margin:18px 0}details{margin-top:12px}summary{cursor:pointer}.notice{border-left:3px solid #d9bb74;padding-left:14px}@media(max-width:700px){.row{grid-template-columns:1fr}main{padding:16px}header{padding:20px}input{min-width:180px}}</style>
<header><span class="tag">只读检查</span><span class="tag">未写入 ROM</span><h1>中文排版检查与预览</h1><div class="muted">当前 v290 · 2026-10-16 · 保留译文、名称和非换行控制</div></header><main>
<div class="stats" id="stats"></div>
<section class="card"><h2 style="font-size:19px;margin:0 0 12px">各类文本框的换行限制</h2>
<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;text-align:left;line-height:2.1"><thead><tr><th>类别</th><th>每行字数</th><th>最多行数</th><th>确认情况</th></tr></thead><tbody>
<tr><td>普通宽框</td><td>14 格</td><td>4 行</td><td>原生配置已核对</td></tr>
<tr><td>普通窄框</td><td>9 格</td><td>3 行</td><td>原生配置已核对</td></tr>
<tr><td>两行小框</td><td>8 格</td><td>2 行</td><td>原生配置已核对</td></tr>
<tr><td>单行小框</td><td>7 格</td><td>1 行</td><td>原生配置已核对</td></tr>
<tr><td>固定技能／术／物品说明</td><td>13 格</td><td>2 行</td><td>现行说明框规则已确认</td></tr>
<tr><td>特殊剧情框／全屏旁白</td><td>按具体模板</td><td>按具体模板</td><td>看每条文本下方标注</td></tr>
<tr><td>尚未关联窗口的对白</td><td>暂按 10 格</td><td>暂按 4 行</td><td>待核，不是游戏硬上限</td></tr>
<tr><td>索引说明</td><td>暂按 13 格</td><td>暂按 2 行</td><td>待核，不能等同于固定说明框</td></tr>
<tr><td>战斗台词／战后提示</td><td>按实际窗口</td><td>按实际窗口</td><td>待核，无统一限制</td></tr>
<tr><td>固定名称／菜单／选项</td><td>按具体栏位</td><td>按具体栏位</td><td>不能直接套用对白换行</td></tr>
</tbody></table></div>
<p class="meta">计数时，汉字和全角标点各算一格；动态人名、地名按实际展开后的字数计算。这里列的是当前保守字格预算，原生配置不等于所有绘字路径的实机极限；示意框的视觉宽度也不代表游戏文本框宽度。具体场景仍需复测。</p></section>
<p class="notice">这里展示离线排版候选。原文栏表示明确写入的换行，游戏自身还可能自动折行。每条下方单独标明已关联窗口或暂定限制；所有候选均未应用。</p>
<nav><input id="q" placeholder="搜索文字、编号或位置"><select id="category"><option value="">所有场景</option></select><select id="kind"><option value="changed">有排版变化</option><option value="known">窗口已关联的变化</option><option value="pending">需要继续核对</option><option value="all">全部文本</option></select></nav><div id="count"></div><div class="pager"><button id="prev">上一页</button><span id="page"></span><button id="next">下一页</button></div><section id="cards"></section>
<details><summary>检查范围与已知限制</summary><div id="limits"></div></details></main><script id="dataset" type="application/json">DATASET</script><script>
const data=JSON.parse(document.getElementById('dataset').textContent), $=s=>document.querySelector(s), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let page=0,filtered=[];const size=30;
const labels={changed:'建议调整断行',unchanged:'保持现有断行',fixed_field_no_reflow:'固定栏位，保持格式',structural_context_pending:'片段或选项需核对',battle_context_pending:'战斗窗口需核对',control_or_dynamic_context:'动态内容或演出控制需核对',format_or_join_boundary:'保留特殊格式或衔接',text_exceeds_page_budget:'内容超过当前页预算',indivisible_term_exceeds_budget:'完整名称或词组超过预算',no_legal_break_within_budget:'当前限制内无合适断点',glyph_context_pending:'字码需核对',encoding_capacity_pending:'记录容量需核对',empty:'空字段'};
const fLabels={window_or_caller_pending:'窗口或调用入口待核',multiple_window_contexts_use_smallest_budget:'存在多种窗口，预览采用较小预算',choice_rows_preserved:'保持选项行',fragment_or_join_needs_complete_flow:'需核对完整拼接',dynamic_or_control_width_pending:'动态内容或控制宽度待核',explicit_line_exceeds_budget_check_native_autowrap:'原显式行较长，需核游戏自动折行',consumer_window_pending_13x2_is_preview_only:'实际说明窗口待核，十三格两行仅作预览',consumer_layout_pending:'显示栏位待核',actual_window_width_pending:'实际战斗框宽待核',battle_control_language:'独立战斗控制格式',native_subfields_and_icons_preserved:'保留缓存子栏位及图标',single_line_name:'单行名称',existing_full_name_interface_preserved:'保持现有完整名称接口',display_consumer_not_inferred_from_storage_capacity:'存储容量不能代替可见栏宽'};
$('#stats').innerHTML=[['文本记录',data.summary.inventory_records],['变化候选',data.summary.changed_preview_count],['已关联窗口的候选',data.summary.changed_with_known_profile_for_review]].map(([a,b])=>`<div class="stat"><strong>${b.toLocaleString()}</strong>${a}</div>`).join('');
for(const c of Object.keys(data.summary.categories))$('#category').insertAdjacentHTML('beforeend',`<option>${esc(c)}</option>`);
$('#limits').innerHTML='<p>清单包含剧情、固定与索引说明、战斗提示、固定名称、菜单短语及缓存。所有既有 ROM 文件保持原状。窗口关联是静态资料，不代表全部场景已完成实机复测。</p>';
function limitLabel(r){
 const ids=r.window_profiles||[],pending=!ids.length||(r.flags||[]).some(f=>f==='window_or_caller_pending'||f==='consumer_window_pending_13x2_is_preview_only');
 if(r.columns_budget){
  const dimensions=`每行 ${r.columns_budget} 格，最多 ${r.rows_budget} 行`;
  if(pending)return `暂定限制：${dimensions}；实际文本框待核，这不是游戏硬上限。`;
  const name=ids.map(id=>data.profiles[id]?.label||'特殊剧情框').join('／');
  return `已关联窗口：${name}；当前按${dimensions}排版，原场景仍需复测。`;
 }
 if(r.category==='战斗提示'||r.category==='战斗剧情')return '换行限制待核：按实际战斗窗口，暂无统一字数与行数上限。';
 return '按具体栏位核对容量，不适用统一的对白换行字数限制。';
}
function lineCountLabel(r){
 const before=r.before_cells,after=r.after_cells;
 if(!Array.isArray(before)||!Array.isArray(after))return '';
 return `<div class="meta">原显式断行每行：${before.join(' / ')} 格；建议每行：${after.join(' / ')} 格。</div>`;
}
function filter(){const q=$('#q').value.trim().toLowerCase(),c=$('#category').value,k=$('#kind').value;filtered=data.rows.filter(r=>(!c||r.category===c)&&(!q||(r.text+' '+r.proposal+' '+r.id+' '+r.source).toLowerCase().includes(q))&&(k==='all'||k==='changed'&&r.text!==r.proposal||k==='known'&&r.ready_for_review||k==='pending'&&(r.flags?.some(f=>f.includes('pending'))||r.proposal_status.includes('pending'))));page=0;render()}
function render(){const total=Math.max(1,Math.ceil(filtered.length/size));$('#count').textContent=`当前筛选 ${filtered.length.toLocaleString()} 条`;$('#page').textContent=`${page+1} / ${total}`;$('#prev').disabled=page===0;$('#next').disabled=page+1>=total;
$('#cards').innerHTML=filtered.slice(page*size,(page+1)*size).map(r=>`<article class="card"><div class="meta">${esc(r.category)} · ${esc(r.id)} · ${esc(r.source)}</div><div class="status">${esc(labels[r.proposal_status]||r.proposal_status)}</div><div class="meta">${esc(limitLabel(r))}</div>${lineCountLabel(r)}<div class="row"><div><div class="meta">原显式断行</div><div class="box">${esc(r.display_before)}</div></div><div><div class="meta">建议预览（未应用）</div><div class="box after">${esc(r.display_after)}</div></div></div>${r.flags?.length?'<p class="meta">'+r.flags.map(f=>esc(fLabels[f]||f)).join('；')+'</p>':''}<details><summary>窗口与源文本信息</summary><pre class="meta">${esc(JSON.stringify({profiles:r.window_profiles,contexts:r.window_contexts,source:r.text,proposal:r.proposal,readback:r.payload_verified},null,2))}</pre></details></article>`).join('')||'<p>当前条件下没有记录。</p>'}
$('#q').addEventListener('input',filter);$('#category').addEventListener('change',filter);$('#kind').addEventListener('change',filter);$('#prev').onclick=()=>{page--;render()};$('#next').onclick=()=>{page++;render()};filter();
</script></html>'''
    (D / '排版检查与预览.html').write_text(page.replace('DATASET', data), encoding='utf8')


if __name__ == '__main__':
    main()
