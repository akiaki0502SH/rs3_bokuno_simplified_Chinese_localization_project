"""Preserve reviewed inputs and synchronize the user's four approved spell names."""
from pathlib import Path
import copy,hashlib,json,sys
from build_v286_four_spell_names_v1 import CONFIRMED
P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
mp=P/'text/translations/translation_sources_current.json';m=rd(mp);assert m['build_revision']=='v285_center_and_yang01'
frozen=P/'text/translations/translation_sources_before_v286_20261011_01.json';assert not frozen.exists();frozen.write_bytes(mp.read_bytes())
backup=(P/'text/backups/v286_four_spell_names_20261011_01').resolve();assert backup.is_relative_to(Path('G:/CodexProjects'))and not backup.exists();backup.mkdir()
docs=['docs/SKILL_NAMES_CONFIRMED_CURRENT.md','docs/SKILL_NAMES_RECOMMENDED_20261011_01.md','docs/TECHNIQUES_AND_SPELLS_BY_CATEGORY_REVIEW_20261010_01.md']
receipt=[]
for name in docs:
 file=P/name;dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);data=file.read_bytes();dest.write_bytes(data);receipt.append({'file':name,'SHA256':sha(data)})
(backup/'COPY_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
sp=rd(m['latest_techniques_and_spells']);old_by={x['id']:copy.deepcopy(x)for x in sp['spells']if x['id']in CONFIRMED}
for x in sp['spells']:
 if x['id']in CONFIRMED:
  jp,zh=CONFIRMED[x['id']];x.update(jp=jp,zh=zh,source_glyphs_need_review=False,status='用户确认四条原字及译名；v286待构建',confirmed_by_user=True,confirmation_source='2026-10-11 conversation: 可以，就按照你的建议来',original_glyph_evidence='qa/V285_FOUR_HELD_SPELL_ORIGINAL_CONTEXT_20261011_01.json')
  if x['id']=='M0024':x['usage_notes']='零姫幻术：召唤幻兽攻击，附混乱。'
  elif x['id']=='M0080':x['usage_notes']='妖魔系妖术：消耗1LP，给自身施加リヴァイヴァ；属性分组不等于学习术系。'
  else:x['usage_notes']='魔道板解读：'+('火行术／金行术／禁咒'if x['id']=='M0104'else'水行术／木行术／土行术')
sp['confirmed_source_glyph_map']['18']['E7']='猫';sp['confirmed_source_glyph_map']['46'].update({'25':'硝','28':'板'})
sp.update(source_revision='20261011_four_spells_v286_01',spell_source_glyphs_need_review_count=0,source_unconfirmed_spells_not_compiled_count=0,latest_skill_confirmations='text/translations/skill_names_user_confirmed_20261011_07.json',four_approved_names_pending_build=list(CONFIRMED))
sf=P/'text/translations/techniques_spells_category_review_v286_20261011_01.json';assert not sf.exists();sf.write_text(json.dumps(sp,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
conf=rd(m['latest_skill_confirmations'])
for x in conf['translations']:
 if x['id']in CONFIRMED:
  jp,zh=CONFIRMED[x['id']];x.update(jp=jp,suggestion=zh,confirmed=zh,previous_current=x['final'],final=zh,changed=True,note='原ROM字形已核，用户在会话确认接入；旧候选保留在review_original。',confirmation_source='2026-10-11 conversation')
conf.update(source_revision='20261011_07',previous_confirmation_source=m['latest_skill_confirmations'],confirmed_count=sum(x['confirmed']is not None for x in conf['translations']),changed_count=4,changed_count_scope='new four spell records only; previous changes inherited',latest_spell_snapshot=sf.relative_to(P).as_posix())
# Retain the already compiled v283 decisions in the effective current list.
# Historical review_original/confirmed cells remain available for provenance.
effective={x['id']:x['zh']for x in sp['spells']+sp['techniques']}
for x in rd(m['latest_typed_review'])['translations']:
 if x['file'].replace('\\','/').endswith('/04_enemy_techniques.md'):effective[x['id']]=x['translation_zh_cn']
carry=[{'id':x['id'],'old':x['final'],'current':effective[x['id']]}for x in conf['translations']if x['id']in effective and x['final']!=effective[x['id']]]
for x in conf['translations']:
 if x['id']in effective and x['final']!=effective[x['id']]:x.update(previous_confirmation_final=x['final'],final=effective[x['id']],effective_compiled_baseline_source=sf.relative_to(P).as_posix()if x['id'][0]!='E'else m['latest_typed_review'])
conf['already_compiled_name_carry_forward']=carry
cf=P/'text/translations/skill_names_user_confirmed_20261011_07.json';assert not cf.exists();cf.write_text(json.dumps(conf,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
# Update four stable IDs only. Monster and spell-description M numbers differ.
for name in docs:
 file=P/name;lines=file.read_text(encoding='utf8').splitlines();new=[]
 for line in lines:
  if line.startswith('|'):
   cells=[x.strip()for x in line.split('|')[1:-1]]
   if cells and cells[0]in CONFIRMED:
    jp,zh=CONFIRMED[cells[0]]
    if name.endswith('SKILL_NAMES_CONFIRMED_CURRENT.md'):cells[1:3]=[zh,jp]
    elif name.endswith('SKILL_NAMES_RECOMMENDED_20261011_01.md')and len(cells)==6:
     cells[1]=jp;cells[3]=zh;cells[4]=zh;cells[5]='原ROM字形已核；用户确认接入v286'
    elif name.endswith('SKILL_NAMES_RECOMMENDED_20261011_01.md')and len(cells)==3:
     cells[1]=zh;cells[2]='已核原字并由用户确认；接入v286'
    else:cells[1]=zh;cells[2]=jp;cells[4]='用户确认；已接入v286测试包，待自然场景复测'
    line='| '+' | '.join(cells)+' |'
   elif cells and cells[0]=='M0104、M0105'and name.endswith('SKILL_NAMES_RECOMMENDED_20261011_01.md'):
    line='| M0104、M0105 | 魔道板解读 | 原字46:28已核为板；用户确认接入，两条对应不同术系。 |'
   elif cells and cells[0]in effective and ((len(cells)==3 and name.endswith('SKILL_NAMES_CONFIRMED_CURRENT.md'))or(len(cells)==5 and name.endswith('TECHNIQUES_AND_SPELLS_BY_CATEGORY_REVIEW_20261010_01.md'))):
    cells[1]=effective[cells[0]];line='| '+' | '.join(cells)+' |'
  new.append(line)
 text='\n'.join(new)+'\n'
 if name.endswith('SKILL_NAMES_CONFIRMED_CURRENT.md'):
  text=text.replace('这是最新译文源对照，尚未写入ROM。','当前术名236条均已编入测试ROM；其中最后四条为本轮用户确认的黑猫、玻璃之盾及两条魔道板解读。未全场景验收。')
 elif name.endswith('SKILL_NAMES_RECOMMENDED_20261011_01.md'):
  text=text.replace('已同步最新译文源，尚未写入ROM；原字待核状态保留。','最新确认已接入测试ROM；最后四条原字已核并由用户确认。旧候选在原译列保留供追溯。')
 else:
  text=text.replace('下面中文是待审稿，**这些术名字段仍未编入ROM**。','当前236条非空术名均已编入测试ROM；下方其他逐行状态保留早期审阅记录，以最新JSON快照为准。')
  text=text.replace('剩余原字待核4条：M0024, M0080, M0104, M0105；仍不会把这些术名草稿写入ROM。','最后四条M0024、M0080、M0104、M0105已核为黒猫、硝子の盾、魔道板解読，并按用户确认接入v286。')
 file.write_text(text,encoding='utf8')
snap=P/'docs/SKILL_NAMES_CONFIRMED_20261011_07.md';assert not snap.exists();snap.write_bytes((P/docs[0]).read_bytes())
overlay={'schema':'four-user-confirmed-spell-names-v1','date':'2026-10-11','approval':'可以，就按照你的建议来','evidence':'qa/V285_FOUR_HELD_SPELL_ORIGINAL_CONTEXT_20261011_01.json','source_manifest':frozen.relative_to(P).as_posix(),'source_snapshot':sf.relative_to(P).as_posix(),'rows':[{'id':id,'jp':jp,'zh':zh,'previous_candidate':old_by[id]['zh'],'offset':old_by[id]['name_offset']}for id,(jp,zh)in CONFIRMED.items()],'no_other_review_wording_changes':True,'new_font_glyphs_required':0}
overlay.pop('no_other_review_wording_changes');overlay.update(no_other_new_ROM_name_changes=True,already_compiled_name_carry_forward=carry)
of=P/'text/translations/four_spell_names_user_confirmed_v286_20261011_01.json';assert not of.exists();of.write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'source_snapshot':sf.relative_to(P).as_posix(),'approved_records':4,'backup':backup.relative_to(P).as_posix()},ensure_ascii=False))
