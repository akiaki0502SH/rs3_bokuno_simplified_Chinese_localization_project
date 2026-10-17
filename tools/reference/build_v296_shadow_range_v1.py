"""Cover the full upper-ROM shadow arena in the existing VM classifier."""
from pathlib import Path
import hashlib
import json

P = Path(__file__).resolve().parents[1]
D = P / 'qa/academy_spell_jump_20261018_01'
sha = lambda b: hashlib.sha256(b).hexdigest().upper()
read = lambda p: json.loads((P / p).read_text(encoding='utf-8-sig'))


def main():
    manifest = read('text/translations/translation_sources_current.json')
    assert manifest['build_revision'] == 'v295_inn_price_padding01'
    report = P / 'qa/V296_SHADOW_RANGE_BUILD_20261018_01.json'
    assert not report.exists()
    inputs = [
        ('clean', P / manifest['latest_test_ROM']['file'],
         '98168405A376F9353DF6F93CF7D70B63E667B46B8CCDE278EE588DDD6E02D476',
         P / 'roms/work/bokuno_cn_candidate_v10bp296_shadow_range_20261018_01.smc'),
        ('user_modified', D / 'reported_modified.smc',
         'EE9814831D2F0407B307E05E8756991CD421DB7B8139249490CD1B91BD2FB72B',
         P / 'roms/work/bokuno_cn_user_modified_v296_shadow_range_20261018_01.smc'),
    ]
    rows = []
    for label, source, expected, out in inputs:
        base = source.read_bytes()
        assert sha(base) == expected and len(base) == 0x800000 and not out.exists()
        assert base[0x7FC103:0x7FC106] == bytes.fromhex('3F 80 9C')
        assert base[0x7FC000:0x7FC006] == bytes.fromhex('08 C2 30 48 DA E2')
        rom = bytearray(base)
        rom[0x7FC105] = 0xFF
        for h in (0xFFDC, 0x40FFDC):
            rom[h:h+4] = bytes.fromhex('FF FF 00 00')
        checksum = sum(rom) & 65535
        for h in (0xFFDC, 0x40FFDC):
            rom[h:h+4] = (checksum ^ 65535).to_bytes(2, 'little') + checksum.to_bytes(2, 'little')
        changes = [i for i, (a, b) in enumerate(zip(base, rom)) if a != b]
        allowed = {0x7FC105} | set(range(0xFFDC, 0xFFE0)) | set(range(0x40FFDC, 0x40FFE0))
        assert set(changes) <= allowed and sum(rom) & 65535 == checksum
        # The independent diagnosis candidates must be identical to this production build.
        trial = D / ('modified_range_fix_candidate.smc' if label == 'user_modified' else 'clean_range_fix_candidate.smc')
        assert bytes(rom) == trial.read_bytes()
        assert not any(rom[0x7FFE00:0x7FFFF0])
        out.write_bytes(rom)
        rows.append({'kind': label, 'base_ROM': source.relative_to(P).as_posix(),
                     'base_SHA256': expected, 'ROM': out.relative_to(P).as_posix(), 'SHA256': sha(rom),
                     'changed_offsets': [f'{x:06X}' for x in changes],
                     'only_classifier_range_and_checksums_changed': True})
    result = {'status': 'V296_MINIMAL_CLASSIFIER_RANGE_BUILD_COMPLETE_VALIDATION_PENDING',
              'root_cause': 'v265 VM lookahead range table limits CPU bank 3F to pages 80..9C; later shadow relocation also uses pages B4..FB. The VM therefore classifies virtual Chinese glyph prefixes 10..16/19 as native opcodes.',
              'logical_write': {'file': '7FC105', 'before': '9C', 'after': 'FF',
                                'CPU_range_before': '3F:8000-9CFF', 'CPU_range_after': '3F:8000-FFFF'},
              'native_source_scripts_or_gameplay_commands_changed': False,
              'fonts_text_items_or_modifier_features_changed': False,
              'original_inputs_unchanged': True, 'outputs': rows}
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
