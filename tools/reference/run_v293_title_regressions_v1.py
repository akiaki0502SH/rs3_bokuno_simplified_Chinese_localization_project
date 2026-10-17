"""Replay the established thirteen genuine-snapshot normal-input routes."""
from pathlib import Path
import concurrent.futures,hashlib,json,subprocess,sys
from run_v292_regressions_v1 import PROTECTED
P=Path(__file__).resolve().parents[1]
D=P/'qa/title_prologue_v293_20261017_01'
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))


def main():
    b=rd('qa/V293_TITLE_PROLOGUE_BUILD_20261017_05.json')
    old=rd('qa/V292_REGRESSION_20261017_02.json')
    assert old['ROM_SHA256']==b['base_SHA256']
    report=P/'qa/V293_TITLE_NORMAL_REGRESSION_20261017_05.json';assert not report.exists()
    def normal(row):
        state=P/row['state_source'];before=sha(state.read_bytes())
        prefix=D/('normal05_'+row['case']);assert not prefix.with_suffix('.json').exists()
        z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',
            str(P/b['ROM']),str(state),row['actions'],str(prefix)],cwd=P,capture_output=True,timeout=60)
        prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr)
        assert z.returncode==0,(row['case'],z.stderr[-1000:])
        assert rd(prefix.with_suffix('.json'))['ROM_SHA']==b['SHA256']
        base=(P/row['candidate_state']).with_suffix('.ram').read_bytes()
        new=prefix.with_suffix('.ram').read_bytes()
        checks={key:base[lo:hi]==new[lo:hi]for key,lo,hi in PROTECTED}
        checks['SRAM_exact']=(P/row['candidate_state']).with_suffix('.srm').read_bytes()==prefix.with_suffix('.srm').read_bytes()
        checks['input_unchanged']=before==sha(state.read_bytes())
        assert all(checks.values()),(row['case'],checks)
        print(row['case'],'PASS',flush=True)
        return {'case':row['case'],'state_source':row['state_source'],'actions':row['actions'],
            'checks':checks,'candidate_state':prefix.with_suffix('.state').relative_to(P).as_posix(),
            'candidate_image':prefix.with_suffix('.png').relative_to(P).as_posix(),
            'normal_input_only':True,'full_WRAM_identical':base==new}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        rows=list(pool.map(normal,old['normal_routes']))
    proof={'status':'THIRTEEN_ESTABLISHED_NORMAL_INPUT_PAIRS_PROTECTED_PASS',
        'ROM':b['ROM'],'SHA256':b['SHA256'],'normal_pairs':len(rows),'rows':rows,
        'no_role_story_inventory_money_or_VM_injection':True}
    report.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'status':proof['status'],'normal_pairs':len(rows)},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
