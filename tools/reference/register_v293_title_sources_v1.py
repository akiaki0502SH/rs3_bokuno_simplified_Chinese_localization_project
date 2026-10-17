"""Register the verified local title ROM, preserving published v0.1.3."""
from pathlib import Path
import copy,hashlib,json,sys
P=Path(__file__).resolve().parents[1]
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))


def main():
    f=P/'text/translations/translation_sources_current.json';m=rd(f)
    b=rd('qa/V293_TITLE_PROLOGUE_BUILD_20261017_05.json')
    v=rd('qa/V293_TITLE_PROLOGUE_VERIFICATION_20261017_05.json')
    p=rd('qa/V293_TESTPACKAGE30_PROOF_20261017_05.json')
    assert m['build_revision']=='v292_reward_growth01'and m['latest_test_ROM']['SHA256']==b['base_SHA256']
    assert sha((P/b['ROM']).read_bytes())==b['SHA256']==v['SHA256']==p['ROM_SHA256']
    assert sha((P/p['ZIP']).read_bytes())==p['ZIP_SHA256']
    frozen='text/translations/translation_sources_before_v293_20261017_01.json'
    assert rd(frozen)==m
    public=copy.deepcopy(m['latest_public_release'])
    overlay='text/translations/title_prologue_user_confirmed_v293_20261017_01.json'
    handoff='docs/HANDOFF_CODEX_20261017_V293_TITLE_PROLOGUE_05.md'
    m.update(source_revision='20261017_title_prologue_v293_05',build_revision='v293_title_prologue01',
        status='COMPILED_PRIVATE_TEST_PACKAGE30_MANUAL_PENDING',previous_sources_manifest=frozen,
        previous_test_ROM=copy.deepcopy(m['latest_test_ROM']),previous_test_package=copy.deepcopy(m['latest_test_package']),
        latest_test_ROM={'file':b['ROM'],'SHA256':b['SHA256']},latest_test_package={'file':p['ZIP'],'SHA256':p['ZIP_SHA256']},
        latest_title_prologue_overlay=overlay,latest_title_prologue_build='qa/V293_TITLE_PROLOGUE_BUILD_20261017_05.json',
        latest_title_prologue_validation='qa/V293_TITLE_PROLOGUE_VERIFICATION_20261017_05.json',
        latest_validation='qa/V293_TESTPACKAGE30_PROOF_20261017_05.json',latest_handoff=handoff,
        latest_save_slot_mapping=p['package_directory']+'/版本与存档来源.json',
        next_action='重新开机查看v293/包30四屏标题序文，不加载旧即时档；确认画面与行尾标点。继续v292自然战斗及剩余3271条排版待核。')
    m['source_precedence'].append('v293标题序文最终层：以用户确认的title_prologue_user_confirmed_v293_20261017_01为四屏唯一现译，在v292之后应用build_v293_title_prologue_v1最终05版。仅精确匹配原生0805–0808的起点和结束边界，结束恢复源指针/边界；仅四段新文本修复24–2F扩展字低字节。保留句内标点和省略号，去掉中文行尾逗号/句号。旧原文和旧影子保留为历史字节，不得据此回退标题现译。字体、原剧情、311条排版、v292战后模块及末尾496字节保留区不改。')
    m['pending_counts']['title_prologue_pages_compiled']=4
    assert m['latest_public_release']==public and public['version']=='0.1.3'
    f.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    z=rd(overlay);z.update(ROM_compilation_pending=False,status='COMPILED_V293_PACKAGE30_MANUAL_PENDING',
        compiled_ROM=b['ROM'],compiled_ROM_SHA256=b['SHA256'],verification=m['latest_title_prologue_validation'])
    (P/overlay).write_text(json.dumps(z,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    tracker=rd('text/translations/feedback_deferred_current.json')
    assert not any(x['id']=='TITLE-PROLOGUE-JP-006'for x in tracker['cases'])
    tracker['cases'].append({'id':'TITLE-PROLOGUE-JP-006','issue':'标题动画四屏死食序文仍显示日文',
        'reported_date':'2026-10-17','status':'fixed_private_test_manual_pending',
        'cause':'独立全屏序文入口绕过正文影子读取；特殊双字节字形助手又丢失低字节。',
        'current_action':'v293精确匹配四屏原生边界并接入用户确认稿，修复虚拟及原生扩展字低字节，保留原时序与控制。',
        'latest_test_package':p['ZIP'],'verification':m['latest_title_prologue_validation'],'handoff':handoff})
    tracker['updated_date']='2026-10-17'
    (P/'text/translations/feedback_deferred_current.json').write_text(json.dumps(tracker,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'build_revision':m['build_revision'],'ROM_SHA256':b['SHA256'],'public_release_unchanged':public['version']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
