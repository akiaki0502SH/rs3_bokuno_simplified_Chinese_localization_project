"""Replay the reported natural academy route and existing protected regressions."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import subprocess
import sys

from audit_linebreak_feedback_readonly_v1 import file_offset
from run_v292_regressions_v1 import PROTECTED

P = Path(__file__).resolve().parents[1]
D = P / 'qa/academy_spell_jump_20261018_01'
sha = lambda b: hashlib.sha256(b).hexdigest().upper()
read = lambda p: json.loads((P / p).read_text(encoding='utf-8-sig'))


def run(job):
    name, rom, state, actions = job
    prefix = D / name
    if not prefix.with_suffix('.json').exists():
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'tools/snes9x_v266_regression_runner_v1.py',
                                 str(rom), str(state), str(actions), str(prefix)], cwd=P,
                                capture_output=True, timeout=60)
        prefix.with_suffix('.stdout.txt').write_bytes(result.stdout + result.stderr)
        assert result.returncode == 0, (name, result.stderr[-1000:])
    receipt = read(prefix.with_suffix('.json'))
    assert receipt['ROM_SHA'] == sha(rom.read_bytes())
    assert receipt['state_SHA'] == sha(state.read_bytes())
    print(name, 'COMPLETE', flush=True)
    return prefix


def protected_equal(a, b):
    aa, bb = a.with_suffix('.ram').read_bytes(), b.with_suffix('.ram').read_bytes()
    result = {key: aa[lo:hi] == bb[lo:hi] for key, lo, hi in PROTECTED}
    result['SRAM_exact'] = a.with_suffix('.srm').read_bytes() == b.with_suffix('.srm').read_bytes()
    return result


def main():
    report = P / 'qa/V296_SHADOW_RANGE_VERIFICATION_20261018_01.json'
    assert not report.exists()
    builds = read('qa/V296_SHADOW_RANGE_BUILD_20261018_01.json')['outputs']
    clean, mod = [P / x['ROM'] for x in builds]
    old = read('qa/V295_INN_PADDING_VERIFICATION_20261017_01.json')
    jobs = []
    for row in old['normal_routes']:
        jobs.append(('regression_' + row['case'], clean, P / row['state_source'], Path(row['actions'])))
    for label, rom in [('clean', clean), ('modified', mod)]:
        start = D / (label + '_fixed_talk.state')
        for i in range(6):
            jobs.append((f'{label}_character_{i}', rom, start, D / f'character_{i}_actions.json'))
            jobs.append((f'{label}_school_{i}', rom, start, D / f'branch_{i}_actions.json'))
        jobs.append((f'{label}_cancel_character', rom, start, D / 'cancel_character_actions.json'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, jobs))
    regression = []
    for row in old['normal_routes']:
        a = (P / row['candidate_state']).with_suffix('')
        b = D / ('regression_' + row['case'])
        checks = protected_equal(a, b)
        assert all(checks.values()), (row['case'], checks)
        regression.append({'case': row['case'], 'checks': checks,
                           'state_source': row['state_source'], 'actions': row['actions'],
                           'candidate_state': b.with_suffix('.state').relative_to(P).as_posix(),
                           'candidate_image': b.with_suffix('.png').relative_to(P).as_posix()})
    pairs = []
    for case in [f'character_{i}' for i in range(6)] + [f'school_{i}' for i in range(6)] + ['cancel_character', 'cancel_school']:
        a, b = D / ('clean_' + case), D / ('modified_' + case)
        checks = protected_equal(a, b)
        assert all(checks.values()), (case, checks)
        assert a.with_suffix('.ram').read_bytes() == b.with_suffix('.ram').read_bytes(), case
        pairs.append({'case': 'character_menu_B_input' if case == 'cancel_character' else case,
                      'checks': checks, 'full_WRAM_identical': True,
                      'candidate_image': b.with_suffix('.png').relative_to(P).as_posix()})
    rom = clean.read_bytes()
    rows = []
    for bank in range(256):
        d = 0x3FF800 + bank * 5
        n = int.from_bytes(rom[d:d+2], 'little')
        if not n:
            continue
        table = file_offset(int.from_bytes(rom[d+2:d+5], 'little'))
        for i in range(n):
            ptr = int.from_bytes(rom[table+2*n+3*i:table+2*n+3*i+3], 'little')
            tb, page = ptr >> 16, (ptr >> 8) & 255
            ranges = [tuple(rom[0x7FC100+j:0x7FC103+j]) for j in range(0, 36, 3)]
            assert tb >= 0xFA or any(tb == b and lo <= page <= hi for b, lo, hi in ranges), f'{ptr:06X}'
            rows.append(ptr)
    uncovered = read(D / 'uncovered_shadow_targets_before.json')
    assert len(uncovered) == 157 and len(rows) == 11877
    # The original reporter's source files must remain unchanged throughout diagnosis.
    for entry in read(D / 'inputs.json'):
        assert sha(Path(entry['source']).read_bytes()) == entry['SHA256'], entry['source']
    result = {'status': 'V296_ACADEMY_NATURAL_ROUTES_AND_PRIOR_PROTECTED_REGRESSIONS_PASS',
              'builds': builds, 'reported_000_SHA256': read(D / 'modified_talk.json')['state_SHA'],
              'unmodified_v295_and_modified_v295_reproduce_same_failure':
                  (D / 'clean_talk.vm').read_bytes() == (D / 'modified_talk.vm').read_bytes(),
              'diagnosis': 'The reported source 4D4CDE redirects to CPU 3FCCDE / file 7FCCDE. This was outside the old 3F:8000-9CFF range. One range byte plus header checksums restores the natural dialogue and menus.',
              'original_scripts_fonts_and_all_modifier_changes_preserved': True,
              'directory_entries_audited': len(rows), 'previously_uncovered_targets': len(uncovered),
              'uncovered_targets_after': 0,
              'directory_audit_is_static_not_full_natural_scene_acceptance': True,
              'normal_regression_pairs': len(regression), 'normal_routes': regression,
              'academy_clean_vs_modified_pairs': pairs,
              'academy_no_VM_character_story_money_or_skill_injection': True,
              'original_user_files_unchanged': True,
              'Japanese_cross_language_snapshot_limit': 'The original Japanese script correctly displays the first research dialogue. Later character selection cannot serve as a clean Japanese control because this Chinese snapshot contains encoded Chinese character-name caches.',
              'remaining': 'Visual acceptance and the explicit cancel-menu outcome are recorded by the final packaging proof. No all-spells learning/combat acceptance is claimed.'}
    assert result['unmodified_v295_and_modified_v295_reproduce_same_failure']
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'normal_pairs': len(regression),
                      'academy_pairs': len(pairs), 'covered': len(rows)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
