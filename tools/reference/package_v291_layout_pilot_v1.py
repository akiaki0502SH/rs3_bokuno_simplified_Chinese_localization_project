"""Deliver the bounded layout pilot and five genuine normal-input snapshots."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

P = Path(__file__).resolve().parents[1]
D = P / 'qa/layout_v291_runtime_20261017_01'
rd = lambda f: json.loads((P / f).read_text(encoding='utf8'))
sha = lambda b: hashlib.sha256(b).hexdigest().upper()


def main():
    build = rd('qa/V291_LAYOUT_V3_PILOT_BUILD_20261017_01.json')
    verify = rd('qa/V291_LAYOUT_PILOT_VERIFICATION_20261017_01.json')
    assert verify['status'] == 'STATIC_311_ROWS_13_NORMAL_PAIRS_AND_2_NATIVE_WINDOW_PAIRS_PASS_MANUAL_PENDING'
    rom = (P / build['ROM']).read_bytes()
    assert sha(rom) == build['SHA256'] == verify['SHA256']
    dest = (P / 'artifacts/private_human_tests/bokuno_cn_v10bk291_20261017_28').resolve()
    assert dest.is_relative_to(P) and dest.is_relative_to(Path('G:/CodexProjects')) and not dest.exists()
    dest.mkdir()
    (dest / '存档_snes9x').mkdir()
    (dest / '对应画面').mkdir()
    stem = 'bokuno_cn_v10bk291_private_test'
    (dest / (stem + '.smc')).write_bytes(rom)
    entries = [
        ('description001_candidate', '水鸟剑说明：如舞蹈般／穿行敌阵的华丽强力招式。', 'description:T052'),
        ('description002_candidate', '次元断说明：劈开空间，／将敌人打入次元裂隙。', 'description:T064'),
        ('description003_candidate', '旋转长枪说明：旋转长枪，斩伤／触及枪身的敌人，施展反击。', 'description:T114'),
        ('delivery_wide', '开场宽框：喂，艾伦，听说雅玛斯／来的船到缪尔斯港了。', 'utt_3C1A6F_3C1A8E'),
        ('delivery_narrow', '开场窄框：马……借我马……／求求你……', 'utt_3C1C82_3C1C98')]
    states = []
    for slot, (prefix, purpose, record_id) in enumerate(entries):
        source = D / (prefix + '.state')
        raw = source.read_bytes()
        assert raw.startswith(b'#!s9xsnp:0012\n')
        saved = gzip.compress(raw, compresslevel=9, mtime=0)
        name = f'{stem}.{slot:03d}'
        (dest / '存档_snes9x' / name).write_bytes(saved)
        assert gzip.decompress(saved) == raw
        shutil.copyfile(D / (prefix + '.png'), dest / '对应画面' / f'{slot:03d}.png')
        states.append({'slot': slot, 'load_key': f'F{slot + 1}', 'purpose': purpose, 'compiled_record': record_id,
            'file': '存档_snes9x/' + name, 'SHA256': sha(saved),
            'source': source.relative_to(P).as_posix(), 'source_SHA256': sha(raw), 'normal_input_only': True})
    sram = P / 'user_saves/snes9x_20261016_v290_inn_tom_inputs_01/bokuno_cn_v10bj290_private_test.srm'
    assert sram.exists() and len(sram.read_bytes()) == 65536
    shutil.copyfile(sram, dest / (stem + '.srm'))
    readme = '''# v291 排版小批量测试版（包28）

本版基于 v290，纳入第三版排版候选中的 **311条：261条对白、50条固定说明**。只调整换行，保留文字、动态名称、字体基线与战后中文语序。原 v290 文件完整保留。

## 使用

解压到独立文件夹，打开 `bokuno_cn_v10bk291_private_test.smc`。将“存档_snes9x”中的五个即时档放进你使用的 Snes9x 存档目录，文件名前缀与本包 ROM 对应；按下面的快捷键载入。

| 槽位 | 加载键 | 主要检查内容 |
| --- | --- | --- |
| 000 | F1 | 水鸟剑说明：如舞蹈般／穿行敌阵的华丽强力招式。 |
| 001 | F2 | 次元断说明：劈开空间，／将敌人打入次元裂隙。 |
| 002 | F3 | 旋转长枪说明：旋转长枪，斩伤／触及枪身的敌人，施展反击。 |
| 003 | F4 | 尤里安开场宽框：喂，艾伦，听说雅玛斯／来的船到缪尔斯港了。 |
| 004 | F5 | 开场窄框：马……借我马……／求求你…… |

“／”只在说明里表示换行，不是游戏中新增的字。五份档均由真实用户档在新 ROM 下通过正常按键生成，没有改角色、金钱、背包或剧情标志；可以按正常流程继续。

## 这版的范围

449条初筛候选中，另138条因共享窗口、前置文字、保护信息不足或明显拆词等原因暂缓；初筛前的3133条待核改动也没有加入。本版不是整份第三版的全量合入。

- 王座厅“然后由我取代米迦勒，／成为罗亚努侯。”已编入，但没有该原剧情的即时档，仍待实际剧情复测。
- 你之前指出的“祭品是妮娜”和“他说要成为勇敢的冒险者”两条，实际窗口尚未确认，本版仍保留原排版；另一条“他还好吗？／当初说要成为勇敢的冒险者，／就离开了镇子。”已进入本轮。
- “冲击波”说明没有采用第三版的“冲击／波”断法，继续保留现有排版，待单独修正。
- 住宿数字前的留白继续单列，不在本版处理。

新对白放到现有空白文本区，原有11877个影子文本载荷全部保留，降低旧即时档续读风险。旧档若停在某句中间，可能继续显示其旧排版；重新触发对白或重新打开菜单后检查。附带五份档已在本版逐个载入验证。

## 已完成的检查

静态回读、完整变更范围检查和逐条文字/控制一致性检查通过；13组正常按键的新旧版对照中，角色、剧情标志、金钱、背包及SRAM一致。真实开场已观察到两段新文本载荷，并查看实际画面；另外完成两组受控原生窗口取字对照。并未声称全部311个原场景或全流程都已验证。

“本轮已写入排版.csv”列出实际加入的内容；“本轮暂缓候选.csv”列出449条中暂缓的部分。“对应画面”与五份即时档一一对应。

这是本地手测版，尚待你继续反馈自然断句、超框、翻页和流程问题。
'''
    (dest / 'README_先读.md').write_text(readme, encoding='utf8')
    with (dest / '本轮已写入排版.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(['编号', '类别', '原排版', '本版排版', '原文字键', '新载荷位置'])
        for r in build['rows']:
            writer.writerow([r['id'], r['category'], r['current_text'].replace('{NEWLINE}', '\n'), r['proposed_display'], r['source'], r['new_payload_file']])
    with (dest / '本轮暂缓候选.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(['编号', '暂缓原因', '拆开的词组'])
        labels = {'previous_text_in_same_window_requires_combined_layout': '同窗前文需合并核对',
            'printed_name_or_spacing_before_payload': '前置名字或空格', 'leading_original_newline_consumes_window_rows': '前置换行占用行数',
            'source_end16_guard_missing': '缺少事件结束位置保护信息', 'protected_phrase_split': '保护词组被拆开',
            'plural_suffix_split_from_preceding_noun': '们与前面的名词被拆开'}
        for r in build['held_from_candidates']:
            writer.writerow([r['id'], '；'.join(labels.get(x, x) for x in r['reasons']), '、'.join(r['split_terms'])])
    sources = {'version': 'v291', 'package': 28, 'ROM_SHA256': build['SHA256'], 'base_ROM_SHA256': build['base_SHA256'],
        'states': states, 'SRAM_source': sram.relative_to(P).as_posix(), 'SRAM_SHA256': sha(sram.read_bytes()),
        'compiled_layout_records': 311, 'full_v3_applied': False, 'original_user_files_not_overwritten': True}
    (dest / '版本与存档来源.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    actions = D / 'delivered_load_actions.json'
    actions.write_text(json.dumps([[[], 0, 1]]), encoding='utf8')
    loads = []
    for r in states:
        prefix = D / f'delivered_slot{r["slot"]:03d}'
        if not prefix.with_suffix('.json').exists():
            process = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'tools/snes9x_v266_regression_runner_v1.py',
                str(dest / (stem + '.smc')), str(dest / r['file']), str(actions), str(prefix)], cwd=P, capture_output=True, timeout=60)
            prefix.with_suffix('.stdout.txt').write_bytes(process.stdout + process.stderr)
            assert process.returncode == 0, process.stderr[-1200:]
        assert rd(prefix.with_suffix('.json'))['ROM_SHA'] == build['SHA256']
        loads.append({'slot': r['slot'], 'load_pass': True})
    (dest / '本轮验证.json').write_text(json.dumps({'verification': verify, 'delivered_state_loads': loads}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (dest / 'SHA256_校验.txt').write_text('\n'.join(sha(f.read_bytes()) + '  ' + f.relative_to(dest).as_posix()
        for f in sorted(dest.rglob('*')) if f.is_file()) + '\n', encoding='utf8')
    zip_path = dest.with_name(dest.name + '_with_saves.zip')
    assert not zip_path.exists()
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for f in sorted(dest.rglob('*')):
            if f.is_file():
                archive.write(f, f.relative_to(dest).as_posix())
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.testzip() is None
        for f in dest.rglob('*'):
            if f.is_file():
                assert archive.read(f.relative_to(dest).as_posix()) == f.read_bytes()
    proof = {'status': 'V291_PACKAGE28_311_LAYOUT_RECORDS_FIVE_SAVES_READY_MANUAL_PENDING',
        'ROM': build['ROM'], 'ROM_SHA256': build['SHA256'], 'ZIP': zip_path.relative_to(P).as_posix(),
        'ZIP_SHA256': sha(zip_path.read_bytes()), 'package_directory': dest.relative_to(P).as_posix(),
        'compiled_records': 311, 'dialogue': 261, 'descriptions': 50, 'held_from_449_candidates': 138,
        'delivered_saves_loaded': 5, 'normal_paired_routes': 13, 'controlled_native_pairs': 2,
        'full_original_scene_coverage': False, 'formal_baseline_promoted': False}
    (P / 'qa/V291_TESTPACKAGE28_PROOF_20261017_01.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(proof, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
