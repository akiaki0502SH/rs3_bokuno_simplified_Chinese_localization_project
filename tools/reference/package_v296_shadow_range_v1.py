"""Deliver clean v296 plus a separate repair preserving the player's ROM changes."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

from run_v292_regressions_v1 import PROTECTED

P = Path(__file__).resolve().parents[1]
D = P / 'qa/academy_spell_jump_20261018_01'
S = P / 'user_saves/snes9x_20261018_academy_inputs_01'
sha = lambda b: hashlib.sha256(b).hexdigest().upper()
read = lambda p: json.loads((P / p).read_text(encoding='utf-8-sig'))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    proof_path = P / 'qa/V296_TESTPACKAGE33_PROOF_20261018_01.json'
    assert not proof_path.exists()
    manifest_path = P / 'text/translations/translation_sources_current.json'
    m = read(manifest_path)
    assert m['build_revision'] == 'v295_inn_price_padding01'
    verification_path = P / 'qa/V296_SHADOW_RANGE_VERIFICATION_20261018_01.json'
    v = read(verification_path)
    assert v['normal_regression_pairs'] == 13 and v['uncovered_targets_after'] == 0
    # New explicit cancel follows the original menu's seventh item, not an assumed B shortcut.
    aa, bb = [(D / (label + '_cancel_school.ram')).read_bytes() for label in ('clean', 'modified')]
    assert aa == bb
    before = (D / 'modified_cancel_school_before.ram').read_bytes()
    for key, lo, hi in PROTECTED:
        if key != 'flags':
            assert before[lo:hi] == bb[lo:hi], key
    for row in v['academy_clean_vs_modified_pairs']:
        if row['case'] == 'cancel_character':
            row['case'] = 'character_menu_B_input'
    v['visual_review'] = {
        'six_characters_reach_school_menu': True,
        'six_schools_reach_spell_lists': True,
        'explicit_seventh_school_menu_item_cancel_returns_to_field': True,
        'cancel_preserves_money_inventory_party': True,
        'within_run_flag_region_change_not_claimed_unchanged': ['F4C0:10->15'],
        'character_menu_B_is_ignored_not_claimed_as_cancel': True,
        'source_captures': ['school_six_routes_review.png', 'character_six_routes_review.png',
                            'modified_cancel_school_step007.png', 'modified_cancel_school_step008.png'],
        'all_spells_learned_or_game_completed_claimed': False,
    }
    v['remaining'] = 'Maintenance player retest pending; 157 shadow entries are statically covered, not 157 individually played scenes.'
    v['academy_extra_cancel_pair'] = {'full_WRAM_identical': True, 'seventh_item_selected': True,
                                      'money_before': 30000, 'money_after': 30000}
    write_json(verification_path, v)
    builds = read('qa/V296_SHADOW_RANGE_BUILD_20261018_01.json')['outputs']
    previous_package = P / read(m['latest_validation'])['package_directory']
    # Input save slots are found by their existing ROM prefix, never by synthetic state construction.
    previous_rom = next(previous_package.glob('*.smc'))
    previous_saves = sorted(previous_package.rglob(previous_rom.stem + '.00[0-5]'))
    assert len(previous_saves) == 6
    packages = []
    for label, row in [('clean', builds[0]), ('user_modified', builds[1])]:
        rom = P / row['ROM']
        assert sha(rom.read_bytes()) == row['SHA256']
        tail = 'with_saves' if label == 'clean' else 'user_modified_with_save'
        pkg = P / 'artifacts/private_human_tests' / ('bokuno_cn_v10bp296_20261018_33_' + tail)
        archive = Path(str(pkg) + '.zip')
        assert pkg.resolve().is_relative_to(P) and not pkg.exists() and not archive.exists()
        pkg.mkdir()
        stem = 'bokuno_cn_v10bp296_private_test' if label == 'clean' else 'bokuno_cn_v10bp296_user_modified'
        shutil.copy2(rom, pkg / (stem + '.smc'))
        saves = pkg / '存档_snes9x'
        saves.mkdir()
        shutil.copy2(S / 'reported.000', saves / (stem + '.000'))
        shutil.copy2(S / 'reported.srm', saves / (stem + '.srm'))
        save_rows = [{'slot': 0, 'source': str((S / 'reported.000').relative_to(P)),
                      'SHA256': sha((S / 'reported.000').read_bytes()), 'description': '用户原始000，学院术士对话前，未改存档'}]
        if label == 'clean':
            for slot, src in enumerate(previous_saves, 1):
                shutil.copy2(src, saves / f'{stem}.{slot:03d}')
                save_rows.append({'slot': slot, 'source': str(src.relative_to(P)), 'SHA256': sha(src.read_bytes()),
                                  'description': '包32既有真实测试档，原槽' + src.suffix[1:]})
        readme = '# v296 学院术士跳场景修复（测试包33）\n\n'
        readme += ('此包在你当前修改后的 ROM 上修复，保留修改器的全部其他改动。\n\n' if label == 'user_modified'
                   else '此包为标准汉化修复版，未加入你修改器的个人改动。\n\n')
        readme += ('打开 `' + stem + '.smc`。将“存档_snes9x”里的同名前缀文件复制到 Snes9x 的 Saves 目录，再载入000（F1），和面前术士对话。新ROM前缀与旧版不同，保留自己的原文件。\n\n'
                   '000是你提供的原始学院对话前即时档；未改写角色、剧情、金钱或技能。附带SRAM也是原文件副本。\n\n'
                   '根因：汉化对白重定位后，旧的文本范围上限没有同步更新。部分虚拟中文字节被当成原生场景指令执行。修复只改1个范围字节及8个头部校验字节。\n\n'
                   '已在Snes9x1.63内核复测：六名角色、六类术系入口、“算了”取消、取消后重新交谈；标准版与个人修改版行为一致。另通过13组既有流程保护对照。\n\n'
                   '当前11,877个影子文本入口全部纳入正确分类范围；157个先前漏覆盖入口属于静态检查，尚非逐个场景人工验收。\n')
        (pkg / 'README_先读.md').write_text(readme, encoding='utf-8-sig')
        write_json(pkg / '版本与存档来源.json', {'build_revision': 'v296_shadow_range01', 'variant': label,
                     'ROM_SHA256': row['SHA256'], 'original_base_SHA256': row['base_SHA256'], 'saves': save_rows,
                     'only_classifier_range_and_checksums_changed': True, 'manual_retest_pending': True})
        shutil.copy2(verification_path, pkg / '本轮验证.json')
        hashes = []
        for file in sorted(pkg.rglob('*')):
            if file.is_file():
                hashes.append(sha(file.read_bytes()) + '  ' + file.relative_to(pkg).as_posix())
        (pkg / 'SHA256_校验.txt').write_text('\n'.join(hashes) + '\n', encoding='utf-8-sig')
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for file in sorted(pkg.rglob('*')):
                if file.is_file():
                    z.write(file, file.relative_to(pkg).as_posix())
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert z.read(stem + '.smc') == rom.read_bytes()
            for file in pkg.rglob('*'):
                if file.is_file():
                    assert z.read(file.relative_to(pkg).as_posix()) == file.read_bytes()
        packages.append({'variant': label, 'file': archive.relative_to(P).as_posix(), 'SHA256': sha(archive.read_bytes()),
                         'package_directory': pkg.relative_to(P).as_posix(), 'ROM': (pkg / (stem + '.smc')).relative_to(P).as_posix(),
                         'ROM_SHA256': row['SHA256'], 'slots': len(save_rows), 'full_ZIP_readback': True})
    for entry in read(D / 'inputs.json'):
        assert sha(Path(entry['source']).read_bytes()) == entry['SHA256']
    proof = {'status': 'V296_PACKAGE33_CLEAN_AND_USER_MODIFIED_REPAIR_VERIFIED_MANUAL_PENDING',
             'ROM': builds[0]['ROM'], 'ROM_SHA256': builds[0]['SHA256'],
             'ZIP': packages[0]['file'], 'ZIP_SHA256': packages[0]['SHA256'],
             'package_directory': packages[0]['package_directory'], 'packages': packages,
             'normal_regression_pairs': 13, 'six_character_and_six_school_entries_reviewed': True,
             'explicit_cancel_and_reopen_reviewed': True, 'original_user_files_unchanged': True,
             'only_one_range_byte_plus_eight_checksum_bytes': True, 'all_modifier_changes_preserved': True}
    write_json(proof_path, proof)
    snapshot = P / 'text/translations/translation_sources_before_v296_20261018_01.json'
    assert not snapshot.exists()
    snapshot.write_bytes(manifest_path.read_bytes())
    overlay_path = P / 'text/translations/shadow_range_fix_v296_20261018_01.json'
    assert not overlay_path.exists()
    write_json(overlay_path, {'build_revision': 'v296_shadow_range01', 'approved_scope': '调查学院术士对话跳场景，修复已复现的汉化故障，保留个人修改',
                             'source_report': '用户当前bokuno_cn.000', 'build': 'qa/V296_SHADOW_RANGE_BUILD_20261018_01.json',
                             'verification': str(verification_path.relative_to(P)), 'change': {'file': '7FC105', 'before': '9C', 'after': 'FF'}})
    m.update(previous_sources_manifest=str(snapshot.relative_to(P)), previous_test_ROM=m['latest_test_ROM'],
             previous_test_package=m['latest_test_package'], build_revision='v296_shadow_range01',
             source_revision='20261018_shadow_range_v296_01', status='COMPILED_PRIVATE_TEST_PACKAGE33_MANUAL_PENDING',
             latest_test_ROM={'file': builds[0]['ROM'], 'SHA256': builds[0]['SHA256']},
             latest_test_package={'file': packages[0]['file'], 'SHA256': packages[0]['SHA256']},
             latest_user_modified_repair_package=packages[1], latest_validation=str(proof_path.relative_to(P)),
             latest_save_slot_mapping=packages[0]['package_directory'] + '/版本与存档来源.json',
             latest_handoff='docs/HANDOFF_CODEX_20261018_V296_SHADOW_RANGE_01.md',
             latest_shadow_range_overlay=str(overlay_path.relative_to(P)),
             latest_shadow_range_build='qa/V296_SHADOW_RANGE_BUILD_20261018_01.json',
             latest_shadow_range_validation=str(verification_path.relative_to(P)),
             next_action='使用保留个人修改的v296修复包载入学院000，人工复测选人、选术系与取消；继续其余待核排版及自然场景。')
    m['source_precedence'].append('v296事件文本分类最终层：在v295后应用build_v296_shadow_range_v1，将v265原有CPU3F文本页上限9C同步到FF。实查11877个活动目录入口全部覆盖，修复157个后续重定位漏覆盖入口。仅7FC105及两处ROM头校验变化；正文、名称、字库、原生脚本与个人修改保持。')
    write_json(manifest_path, m)
    print(json.dumps(proof, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
