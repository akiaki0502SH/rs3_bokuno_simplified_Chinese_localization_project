"""Normal-input paired replays on copies of existing user states; no RAM injection."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import subprocess
import sys

P = Path(__file__).resolve().parents[1]
D = P / 'qa/layout_v291_runtime_20261017_01'
rd = lambda f: json.loads((P / f).read_text(encoding='utf8'))
sha = lambda b: hashlib.sha256(b).hexdigest().upper()
PROTECTED = [('flags', 0xF400, 0xF800), ('actors', 0xF561, 0xF561 + 26 * 48),
             ('extended', 0x1F960, 0x1F960 + 33 * 48), ('name', 0xF300, 0xF308),
             ('money', 0xF31A, 0xF31C), ('inventory', 0xF320, 0xF400)]


def main():
    D.mkdir(exist_ok=True)
    build = rd('qa/V291_LAYOUT_V3_PILOT_BUILD_20261017_01.json')
    prior = rd('qa/V288_FONT_GEOMETRY_REGRESSION_20261012_01.json')['rows']
    cases = []
    for slot in range(4):
        action = D / f'description{slot:03d}_actions.json'
        action.write_text(json.dumps([[['DOWN'], 4, 60], [['UP'], 4, 120]]), encoding='utf8')
        cases.append((f'description{slot:03d}', f'user_saves/snes9x_20261011_v283_feedback_inputs_01/bokuno_cn_v10bc283_extra_test.{slot:03d}', str(action)))
    for row in prior:
        cases.append(('prior_' + row['case'], row['state_source'], row['actions']))
    action = D / 'inn_idle_actions.json'
    action.write_text(json.dumps([[[], 0, 60]]), encoding='utf8')
    cases.append(('inn', 'user_saves/snes9x_20261016_v290_inn_tom_inputs_01/bokuno_cn_v10bj290_private_test.002', str(action)))
    action = D / 'opening_actions.json'
    action.write_text(json.dumps([[[], 0, 360]] + [[['A'], 1, 360]] * 12), encoding='utf8')
    cases.append(('opening_progress', 'user_saves/snes9x_20261016_v290_inn_tom_inputs_01/bokuno_cn_v10bj290_private_test.003', str(action)))
    battle = next(r for r in rd('qa/V289_POSTBATTLE_RUNTIME_PROOF_20261013_01.json')['normal_routes'] if r['case'] == 'battle_progress')
    cases.append(('battle_progress', battle['state_source'], 'qa/postbattle_feedback_v289_20261013_01/natural_battle_actions.json'))
    jobs = [(name, label, build[key], state, actions) for name, state, actions in cases
            for label, key in [('base', 'base_ROM'), ('candidate', 'ROM')]]

    def run(job):
        name, label, rom, state, actions = job
        prefix = D / (name + '_' + label)
        if not prefix.with_suffix('.json').exists():
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', 'tools/snes9x_v266_regression_runner_v1.py',
                rom, state, actions, str(prefix)], cwd=P, capture_output=True, timeout=60)
            prefix.with_suffix('.stdout.txt').write_bytes(result.stdout + result.stderr)
            assert result.returncode == 0, (name, label, result.stderr[-1500:])
        assert rd(prefix.with_suffix('.json'))['ROM_SHA'] == sha((P / rom).read_bytes())
        print('replay', name, label, flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, jobs))
    rows = []
    new_ranges = [(int(r['new_payload_CPU'], 16), int(r['new_payload_CPU'], 16) + r['new_bytes'], r['id'])
                  for r in build['rows'] if r['mode'] != 'fixed64']
    for name, state, actions in cases:
        a, b = D / (name + '_base'), D / (name + '_candidate')
        ar, br = a.with_suffix('.ram').read_bytes(), b.with_suffix('.ram').read_bytes()
        checks = {key: ar[lo:hi] == br[lo:hi] for key, lo, hi in PROTECTED}
        checks['SRAM_exact'] = a.with_suffix('.srm').read_bytes() == b.with_suffix('.srm').read_bytes()
        cursors = {int.from_bytes(bytes.fromhex(line), 'little') for line in b.with_suffix('.vm').read_text().splitlines()}
        hits = sorted({rid for lo, hi, rid in new_ranges if any(lo <= cursor < hi for cursor in cursors)})
        rows.append({'case': name, 'state_source': state, 'actions': actions, 'checks': checks,
            'protected_pass': all(checks.values()), 'observed_new_payload_text_cursor': hits,
            'candidate_image': b.with_suffix('.png').relative_to(P).as_posix(),
            'candidate_state': b.with_suffix('.state').relative_to(P).as_posix(),
            'normal_input_only': True})
    report = {'status': 'NORMAL_INPUT_REPLAYS_COMPLETE_REVIEW_REQUIRED', 'ROM_SHA256': build['SHA256'],
        'paired_cases': len(rows), 'all_protected_pass': all(r['protected_pass'] for r in rows), 'rows': rows,
        'limits': ['Text-cursor sampling is not an instruction-level glyph trace.',
                   'Controlled/all-entry display tests and full-game equivalence are not implied.']}
    if report['all_protected_pass']:
        report['status'] = 'THIRTEEN_NORMAL_INPUT_PAIRED_ROUTES_PROTECTED_PASS'
    (P / 'qa/V291_NORMAL_REGRESSION_20261017_01.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'status': report['status'], 'cases': len(rows), 'new_payloads_seen': sorted({x for r in rows for x in r['observed_new_payload_text_cursor']}),
                      'failures': [r for r in rows if not r['protected_pass']]}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
