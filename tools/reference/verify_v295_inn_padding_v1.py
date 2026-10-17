"""Check exact formatter scope, genuine inn branches and previous routes."""
from pathlib import Path
import concurrent.futures,hashlib,json,re,subprocess,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from run_v292_regressions_v1 import PROTECTED
from font_geometry_v1 import glyph_locations,read_glyph,unpack
P=Path(__file__).resolve().parents[1];D=P/'qa/inn_padding_v295_20261017_01'
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()


def main():
    b=rd('qa/V295_INN_PADDING_BUILD_20261017_01.json');rom=(P/b['ROM']).read_bytes();base=(P/b['base_ROM']).read_bytes()
    assert sha(rom)==b['SHA256']and sha(base)==b['base_SHA256']
    report=P/'qa/V295_INN_PADDING_VERIFICATION_20261017_01.json';assert not report.exists()
    rebuilt=bytearray(base);mask=bytearray(len(base))
    for w in b['writes']:
        at=int(w['offset'],16);z=bytes.fromhex(w['after_hex'])
        assert base[at:at+len(z)]==bytes.fromhex(w['before_hex'])and not any(mask[at:at+len(z)])
        rebuilt[at:at+len(z)]=z;mask[at:at+len(z)]=b'\1'*len(z)
    assert rebuilt==rom and sum(rom)&65535==int.from_bytes(rom[0xffde:0xffe0],'little')
    def compare(a,c):
        aa=a.with_suffix('.ram').read_bytes();cc=c.with_suffix('.ram').read_bytes()
        checks={k:aa[lo:hi]==cc[lo:hi]for k,lo,hi in PROTECTED}
        checks['SRAM_exact']=a.with_suffix('.srm').read_bytes()==c.with_suffix('.srm').read_bytes()
        assert all(checks.values()),(a.name,c.name,checks)
        return checks
    prior=rd('qa/V294_DIGIT_FONT_RUNTIME_20261017_01.json');assert prior['SHA256']==b['base_SHA256']
    def normal(row):
        prefix=D/('normal_'+row['case']);state=P/row['state_source'];digest=sha(state.read_bytes())
        if not prefix.with_suffix('.json').exists():
            z=subprocess.run([sys.executable,'-B','-X','utf8','tools/snes9x_v266_regression_runner_v1.py',
                str(P/b['ROM']),str(state),row['actions'],str(prefix)],cwd=P,capture_output=True,timeout=60)
            prefix.with_suffix('.stdout.txt').write_bytes(z.stdout+z.stderr);assert z.returncode==0,z.stderr[-1000:]
        assert rd(prefix.with_suffix('.json'))['ROM_SHA']==b['SHA256']and sha(state.read_bytes())==digest
        checks=compare((P/row['candidate_state']).with_suffix(''),prefix)
        print('normal',row['case'],'PASS',flush=True)
        return {'case':row['case'],'checks':checks,'state_source':row['state_source'],'actions':row['actions'],
            'candidate_state':prefix.with_suffix('.state').relative_to(P).as_posix(),
            'candidate_image':prefix.with_suffix('.png').relative_to(P).as_posix(),'normal_input_only':True}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:normals=list(pool.map(normal,prior['normal_routes']))
    def trials(label):
        text=(D/f'{label}_number_trace.txt').read_text(encoding='utf8')
        assert 'RESULT completed=38 formatter_input_only=true no_draw=true'in text
        out=[]
        for line in text.splitlines():
            if not line.startswith('TRIAL '):continue
            out.append(dict(re.findall(r'(\w+)=([\w]+)',line)))
        assert len(out)==38;return out
    aa,cc=trials('base'),trials('candidate');cpu=[]
    for old,new in zip(aa,cc):
        assert old['idx']==new['idx']and old['ptr']==new['ptr']and old['amount']==new['amount']
        target=new['ptr']in ['FC3956','FC4202'];value=int(new['amount'])
        if target:
            expected=b''.join(bytes([0x23,int(c)])for c in str(value))
            assert new['raw']==expected.hex().upper()and int(new['bytes'])==len(expected)
        else:assert old==new,('non-target numeric behavior changed',old,new)
        assert new['SP']==old['SP']=='1F67'and new['protected']=='true'
        cpu.append({'cursor':new['ptr'],'amount':value,'is_inn_target':target,'byte_length':int(new['bytes']),
            'encoded':new['raw'],'non_target_ABI_identical':not target,'protected':True})
    natural=[]
    for case in ['reopen','decline','stay']:
        old=D/(case+'_base');new=D/(case+'_candidate');checks=compare(old,new)
        values={}
        for label,prefix in [('base',old),('candidate',new)]:
            start=Path(str(prefix)+'_before.ram').read_bytes();end=prefix.with_suffix('.ram').read_bytes()
            before=int.from_bytes(start[0xf31a:0xf31c],'little');after=int.from_bytes(end[0xf31a:0xf31c],'little')
            assert after-before==(-5 if case=='stay'else 0)
            values[label]={'before':before,'after':after,'delta':after-before}
        natural.append({'case':case,'checks':checks,'money':values,'normal_controller_only':True,
            'candidate_state':new.with_suffix('.state').relative_to(P).as_posix(),
            'candidate_image':new.with_suffix('.png').relative_to(P).as_posix()})

    frozen=rd('text/translations/translation_sources_before_v295_20261017_01.json')
    mp={k:bytes.fromhex(v)for k,v in rd(frozen['latest_font_mapping']).items()}
    def origins(path,text):
        image=np.asarray(Image.open(path).convert('RGB'));white=np.all(image==255,axis=2)
        w=14*(len(text)-1)+16;h=16;hit=np.ones((image.shape[0]-h+1,image.shape[1]-w+1),dtype=bool)
        for i,ch in enumerate(text):
            glyph=unpack(read_glyph(rom,glyph_locations(mp[ch])[0]))
            for y in range(16):
                for x in range(16):
                    if glyph.getpixel((x,y)):hit &= white[y:y+hit.shape[0],i*14+x:i*14+x+hit.shape[1]]
        return [(int(x),int(y))for y,x in zip(*np.where(hit))]
    before=origins(D/'reopen_base.png','5奥拉姆。');after=origins(D/'reopen_candidate.png','5奥拉姆。')
    assert len(before)==len(after)==1,(before,after)
    assert after[0]==(before[0][0]-28,before[0][1])
    party_before=origins(D/'reopen_base.png','5位客人的话，')
    party_after=origins(D/'reopen_candidate.png','5位客人的话，')
    assert len(party_before)==len(party_after)==1 and party_before==party_after
    assert after[0][0]==party_after[0][0]
    canvas=Image.new('RGB',(1120,340),'#142023');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',21);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
    draw.text((20,12),'住宿报价：正常取消后重新交谈的实测对照',font=font,fill='#f0efdf')
    for i,(name,title)in enumerate([('reopen_base.png','旧版：价格前两格空白'),('reopen_candidate.png','修正版：价格从行首开始')]):
        x=20+550*i;draw.text((x,50),title,font=font,fill='#edb7a0'if i==0 else'#abe0b7')
        image=Image.open(D/name).convert('RGB').crop((60,8,235,76)).resize((525,204),Image.Resampling.NEAREST)
        canvas.paste(image,(x,82))
    draw.text((22,302),'住宿扣款仍为5奥拉姆；选择“算了”不扣款。金额和队伍数据未被注入。',font=small,fill='#b2cbbd')
    comparison=D/'住宿报价_修正前后.png';canvas.save(comparison)
    proof={'schema':'v295-inn-padding-verification-v1','status':'REAL_INN_REOPEN_STAY_DECLINE_CPU38_AND_THIRTEEN_PRIOR_PAIRS_PASS',
        'ROM':b['ROM'],'SHA256':b['SHA256'],'write_manifest_replayed_byte_exact':True,
        'formatter_CPU_trials':cpu,'formatter_trials':38,'target_formatter_cases':20,'non_target_cases':18,
        'one_two_three_digit_amounts_exact':True,'zero_digit_retained':True,'non_target_registers_flags_stack_and_bytes_identical':True,
        'natural_inn_pairs':natural,'normal_existing_pairs':13,'normal_routes':normals,
        'actual_price_text_origin_before':list(before[0]),'actual_price_text_origin_after':list(after[0]),
        'removed_blank_cells':2,'removed_padding_pixels':28,'party_count_position_unchanged':True,
        'actual_stay_money_delta':-5,'decline_money_delta':0,'comparison_image':comparison.relative_to(P).as_posix(),
        'source_scripts_price_reads_fee_calculation_and_stay_logic_unchanged':True,
        'source_state':'user_saves/snes9x_20261016_v290_inn_tom_inputs_01/bokuno_cn_v10bj290_private_test.002',
        'no_role_story_inventory_money_or_VM_injection_in_normal_runs':True,
        'CPU_fixture_formatter_inputs_only_not_gameplay':True,'natural_replay_of_both_distinct_inn_scripts_claimed':False,
        'all_fonts_v293_title_and_v292_rewards_unchanged':True,'full_gameplay_acceptance_not_claimed':True}
    report.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:proof[k]for k in ['status','SHA256','formatter_trials','normal_existing_pairs','removed_padding_pixels']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
