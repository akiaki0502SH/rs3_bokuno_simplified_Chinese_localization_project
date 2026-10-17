"""Register the verified local inn quote fix without changing public assets."""
from pathlib import Path
import copy,hashlib,json,sys
P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()


def main():
    f=P/'text/translations/translation_sources_current.json';m=rd(f)
    frozen='text/translations/translation_sources_before_v295_20261017_01.json'
    assert m==rd(frozen)and m['build_revision']=='v294_digit_font01'
    b=rd('qa/V295_INN_PADDING_BUILD_20261017_01.json');v=rd('qa/V295_INN_PADDING_VERIFICATION_20261017_01.json')
    p=rd('qa/V295_TESTPACKAGE32_PROOF_20261017_01.json')
    assert sha((P/b['ROM']).read_bytes())==b['SHA256']==v['SHA256']==p['ROM_SHA256']
    assert sha((P/p['ZIP']).read_bytes())==p['ZIP_SHA256']
    overlay='text/translations/inn_price_padding_v295_20261017_01.json';assert not(P/overlay).exists()
    handoff='docs/HANDOFF_CODEX_20261017_V295_INN_PADDING_01.md'
    z={'schema':'v295-inn-price-padding-overlay-v1','status':'COMPILED_PRIVATE_PACKAGE32_MANUAL_PENDING',
        'issue':'LAYOUT-NUMBER-PADDING-002','ROM_SHA256':b['SHA256'],'base_ROM_SHA256':b['base_SHA256'],
        'source_commands':b['exact_native_commands'],'checked_VM_cursors':b['checked_VM_cursors'],
        'display_rule':'omit leading blank digits from these two inn quote numbers; retain one zero digit',
        'native_formatter_and_fee_calculation_unchanged':True,'other_numeric_commands_unchanged':True,
        'build':'qa/V295_INN_PADDING_BUILD_20261017_01.json','verification':'qa/V295_INN_PADDING_VERIFICATION_20261017_01.json',
        'native_quote_text_origin_before':v['actual_price_text_origin_before'],'native_quote_text_origin_after':v['actual_price_text_origin_after']}
    (P/overlay).write_text(json.dumps(z,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    public=copy.deepcopy(m['latest_public_release'])
    m.update(source_revision='20261017_inn_padding_v295_01',build_revision='v295_inn_price_padding01',status='COMPILED_PRIVATE_TEST_PACKAGE32_MANUAL_PENDING',
        previous_sources_manifest=frozen,previous_test_ROM=copy.deepcopy(m['latest_test_ROM']),previous_test_package=copy.deepcopy(m['latest_test_package']),
        latest_test_ROM={'file':b['ROM'],'SHA256':b['SHA256']},latest_test_package={'file':p['ZIP'],'SHA256':p['ZIP_SHA256']},
        latest_inn_price_overlay=overlay,latest_inn_price_build='qa/V295_INN_PADDING_BUILD_20261017_01.json',
        latest_inn_price_validation='qa/V295_INN_PADDING_VERIFICATION_20261017_01.json',latest_validation='qa/V295_TESTPACKAGE32_PROOF_20261017_01.json',
        latest_handoff=handoff,latest_save_slot_mapping=p['package_directory']+'/版本与存档来源.json',
        next_action='取消旧住宿报价后重新交谈，复测v295/包32去除前导空格；005/F6为旧真实档正常重开后的样例。继续其余3271条排版及自然战斗验收。')
    m['source_precedence'].append('v295住宿报价最终显示层：在v294之后应用inn_price_padding_v295_20261017_01及build_v295_inn_padding_v1。仅在原生3D读取/格式化完成后的FC3956、FC4202游标，复用C033C5原生紧凑复制；其余3D按原固定三位输出。去掉住宿报价前导空格，保留0、原报价读取、人数、收费、住宿选择、所有字体/文本/剧情和末尾496字节。')
    assert m['latest_public_release']==public and public['version']=='0.1.3'
    f.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    tracker=rd('text/translations/feedback_deferred_current.json');case=next(x for x in tracker['cases']if x['id']=='LAYOUT-NUMBER-PADDING-002')
    case.update(status='fixed_private_test_manual_pending',repair_phase='inn_quote_display_fix_compiled',
        latest_user_instruction='2026-10-17维护者在v294再次反馈5奥拉姆前的过多空格仍存在，本轮单独修复。',
        current_action='v295/包32仅将两处住宿报价改为紧凑显示，正常重新交谈去掉两格；住宿仍扣5，取消不扣款，38格式案例及13既有回归通过。',
        latest_test_package=p['ZIP'],verification=m['latest_inn_price_validation'],handoff=handoff)
    (P/'text/translations/feedback_deferred_current.json').write_text(json.dumps(tracker,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'build_revision':m['build_revision'],'ROM_SHA256':b['SHA256'],'public_release_unchanged':public['version']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
