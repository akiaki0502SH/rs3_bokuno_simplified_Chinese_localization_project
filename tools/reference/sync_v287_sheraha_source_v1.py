"""Preserve the previous source and register one explicit user wording approval."""
from pathlib import Path
import json,copy,hashlib
from build_v287_sheraha_wording_v1 import BEFORE,AFTER
P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
mp=P/'text/translations/translation_sources_current.json';m=rd(mp);assert m['build_revision']=='v286_four_spell_names01'
frozen=P/'text/translations/translation_sources_before_v287_20261011_01.json';assert not frozen.exists();frozen.write_bytes(mp.read_bytes())
file=P/'docs/translation_review_20261010/12_battle_messages.md';original=file.read_bytes()
backup=(P/'text/backups/v287_sheraha_wording_20261011_01').resolve();assert backup.is_relative_to(Path('G:/CodexProjects'))and not backup.exists();backup.mkdir();(backup/file.name).write_bytes(original)
analysis=rd('qa/B0028_SHERAHA_SCENE_SUBJECT_ANALYSIS_20261011_01.json');old=analysis['message']['current_translation'];assert old.count(BEFORE)==1;new=old.replace(BEFORE,AFTER)
lines=original.decode('utf8').splitlines();changed=0
for i,line in enumerate(lines):
 if line.startswith('| B0028 |'):
  cells=[x.strip()for x in line.split('|')[1:-1]];assert cells[1]==old;cells[1]=new;cells[4]='用户确认省略人物主语；已编入v287测试包，待自然战斗复测';lines[i]='| '+' | '.join(cells)+' |';changed+=1
assert changed==1
lines[2]='当前64条战斗消息已接入私人测试构建；下方其他旧状态保留历史。B0028封印句于2026-10-11按用户确认改为中性表达，原控制与停顿保持。正式基线264-05保持。'
file.write_text('\n'.join(lines)+'\n',encoding='utf8')
overlay={'schema':'user-confirmed-battle-wording-overlay-v1','record':'B0028','text_id':'indexed_battle_event_messages_3d9a00_01C','file':'docs/translation_review_20261010/12_battle_messages.md','date':'2026-10-11','approval':'可以','analysis':'qa/B0028_SHERAHA_SCENE_SUBJECT_ANALYSIS_20261011_01.json','before':old,'translation_zh_cn':new,'replacement_before':BEFORE,'replacement_after':AFTER,'semantic_review_resolved':True,'resolution':'保留光之钻石封印记忆与黑暗之力的持续含义，不向此句补入原文未指明的人物主语。','no_other_message_wording_changes':True,'review_backup':backup.relative_to(P).as_posix()+'/'+file.name,'review_before_SHA256':hashlib.sha256(original).hexdigest().upper()}
of=P/'text/translations/sheraha_b0028_user_confirmed_v287_20261011_01.json';assert not of.exists();of.write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
typed=rd(m['latest_typed_review']);assert not any(x['id']=='B0028'and x['file'].endswith('12_battle_messages.md')for x in typed['translations'])
typed['translations'].append({'file':overlay['file'],'id':'B0028','text_id':overlay['text_id'],'source_offset':'0x3D9ED8','runtime_offset':'0x3D9F87','source_file':'原生战斗消息1C，global78','zh':old,'jp':analysis['message']['original_japanese'],'translation_zh_cn':new,'translation_status':'user_confirmed_v287_pending_build','approval':'2026-10-11会话用户确认','compiled_ROM_SHA256':None,'current_test_ROM_SHA256':m['latest_test_ROM']['SHA256']})
typed.update(entry_count=len(typed['translations']),source_revision='20261011_sheraha_v287_01',newly_compiled_this_round=1,source_only_pending_count=1,previous_compiled_overlay=m['latest_typed_review'],latest_battle_wording_overlay=of.relative_to(P).as_posix())
tf=P/'text/translations/typed_review_integrated_v287_20261011_01.json';assert not tf.exists();tf.write_text(json.dumps(typed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'source_snapshot':tf.relative_to(P).as_posix(),'approved_record':'B0028','new_clause':AFTER},ensure_ascii=False))
