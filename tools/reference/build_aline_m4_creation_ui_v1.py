#!/usr/bin/env python3
"""Isolated A-line M4 pilot: rewrite guarded character-creation UI text slots."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from build_character_creation_ui_payloads import FIELDS
from dry_run_encoding_plan import encode

CLEAN_SHA = '4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0'
CHECKSUM_SLOTS = (0x00FFDC, 0x40FFDC)
CELL_SAFE_OVERRIDES = {
    'prompt_sex': '选性别吧',
    'prompt_protagonist': '选主角吧',
    'prompt_star': '选宿星吧',
    'prompt_weapon': '选择擅长武器',
}
DOUBLE_BYTE_LEADS = set(range(0x10, 0x17)) | {0x18, 0x19, 0x46} | set(range(0x20, 0x24))

def display_cells(data: bytes) -> int:
    cells = 0
    i = 0
    while i < len(data):
        lead = data[i]
        if lead in DOUBLE_BYTE_LEADS and i + 1 < len(data):
            i += 2
            cells += 1
        elif lead == 0x50 or lead >= 0x51:
            i += 1
            cells += 1
        else:
            i += 1
    return cells

def sha(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', type=Path, required=True)
    p.add_argument('--clean-rom', type=Path, required=True)
    p.add_argument('--mapping-json', type=Path, required=True)
    p.add_argument('--expected-rom-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--cell-safe-only', action='store_true', help='rewrite only slots whose visible cell count matches the original; use width-preserving prompt wording')
    a = p.parse_args()
    if a.output.exists() or a.manifest.exists():
        raise SystemExit('output or manifest exists; refusing to overwrite')
    base = a.rom.read_bytes()
    clean = a.clean_rom.read_bytes()
    if len(base) != 0x800000 or len(clean) != len(base) or sha(base) != a.expected_rom_sha256.upper() or sha(clean) != CLEAN_SHA:
        raise SystemExit('ROM identity mismatch')
    mapping = {ch: bytes.fromhex(code) for ch, code in json.loads(a.mapping_json.read_text(encoding='utf-8')).items()}
    rom = bytearray(base)
    writes = []
    skipped = []
    covered = set()
    for name, at, capacity, original_zh in FIELDS:
        zh = (CELL_SAFE_OVERRIDES.get(name, original_zh) if a.cell_safe_only else
              '开场：死食危机' if name == 'prologue_title' else original_zh)
        raw = clean[at:at + capacity]
        if len(raw) != capacity or base[at:at + capacity] != raw:
            raise SystemExit(f'{name}: original text slot changed or out of range')
        if any(i in covered for i in range(at, at + capacity)):
            raise SystemExit(f'{name}: overlapping fixed text slot')
        encoded, missing, token_errors = encode(zh, mapping, battle=False)
        if missing or token_errors or len(encoded) > capacity:
            raise SystemExit(f'{name}: cannot fit {zh!r}; bytes={len(encoded)}/{capacity}, missing={sorted(missing)}, tokens={token_errors}')
        payload = encoded + b'\x50' * (capacity - len(encoded))
        before_cells, after_cells = display_cells(raw), display_cells(payload)
        if a.cell_safe_only and before_cells != after_cells:
            skipped.append({'name': name, 'offset': f'0x{at:06X}', 'before_cells': before_cells, 'after_cells': after_cells})
            continue
        rom[at:at + capacity] = payload
        covered.update(range(at, at + capacity))
        writes.append({'name': name, 'offset': f'0x{at:06X}', 'capacity': capacity, 'text': zh,
                       'before': raw.hex(' ').upper(), 'encoded': encoded.hex(' ').upper(),
                       'payload': payload.hex(' ').upper(), 'before_cells': before_cells, 'after_cells': after_cells})
    for h in CHECKSUM_SLOTS:
        rom[h:h + 4] = bytes.fromhex('FF FF 00 00')
    checksum = sum(rom) & 0xFFFF
    for h in CHECKSUM_SLOTS:
        rom[h:h + 2] = (checksum ^ 0xFFFF).to_bytes(2, 'little')
        rom[h + 2:h + 4] = checksum.to_bytes(2, 'little')
        covered.update(range(h, h + 4))
    changed = {i for i, (old, new) in enumerate(zip(base, rom)) if old != new}
    if changed - covered:
        raise SystemExit(f'unexpected change at 0x{min(changed - covered):06X}')
    a.output.write_bytes(rom)
    report = {'phase': 'aline_m4_creation_ui_pilot_v1', 'release_status': 'internal diagnostic only',
              'base_rom': str(a.rom.resolve()), 'base_sha256': sha(base),
              'output_rom': str(a.output.resolve()), 'output_sha256': sha(rom),
              'mapping_json': str(a.mapping_json), 'cell_safe_only': a.cell_safe_only,
              'writes': writes, 'skipped': skipped,
              'changed_bytes': len(changed), 'checksum': f'{checksum:04X}'}
    a.manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'sha256': report['output_sha256'], 'slots': len(writes), 'skipped': len(skipped), 'changed_bytes': len(changed)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
