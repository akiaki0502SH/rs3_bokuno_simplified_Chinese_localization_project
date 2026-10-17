"""Register verified v294 glyph assets and the local test package."""
from pathlib import Path
import copy,hashlib,json,sys
from font_geometry_v1 import glyph_locations,read_glyph
P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()


def main():
    current=P/'text/translations/translation_sources_current.json';m=rd(current)
    frozen=rd('text/translations/translation_sources_before_v294_20261017_01.json')
    assert m==frozen and m['build_revision']=='v293_title_prologue01'
    b=rd('qa/V294_DIGIT_FONT_BUILD_20261017_01.json');v=rd('qa/V294_DIGIT_FONT_VERIFICATION_20261017_01.json')
    p=rd('qa/V294_TESTPACKAGE31_PROOF_20261017_01.json');rom=(P/b['ROM']).read_bytes()
    assert sha(rom)==b['SHA256']==v['SHA256']==p['ROM_SHA256']
    assert sha((P/p['ZIP']).read_bytes())==p['ZIP_SHA256']
    fd=(P/'font/v294_digits_20261017_01').resolve();assert fd.is_relative_to(P)and not fd.exists();fd.mkdir()
    snapshots={}
    for name,start,length in [('event_atlas',0x780000,0x10000),('fixed_atlas',0x7D0000,0x10000),('standard_font',0x2C0000,0x8000)]:
        f=fd/(name+'.bin');z=rom[start:start+length];f.write_bytes(z)
        snapshots[name]={'path':f.relative_to(P).as_posix(),'SHA256':sha(z),'offset':f'{start:06X}','length':length}
    atlas=rd(m['latest_font_atlas']);atlas['source_version']='v294_digit_font01';atlas['final_ROM_SHA256']=b['SHA256']
    for name,key in [('event_atlas','eventAtlas'),('fixed_atlas','fixedAtlas')]:
        atlas[key]={'path':snapshots[name]['path'],'sha256':snapshots[name]['SHA256']}
    for row in atlas['native_geometry_snapshots']:
        if row['offset']=='2C0000':row.update(snapshots['standard_font'])
    by_digit={row['digit']:row for row in b['rows']}
    for row in atlas['glyphs']:
        if row['atom']not in by_digit:continue
        x=by_digit[row['atom']];raw=read_glyph(rom,glyph_locations(bytes.fromhex(row['code']))[0])
        assert sha(raw)==x['glyph_SHA256']
        row['previous_source']=row['source'];row['source']='v294_native_digit_reference'
        row['glyphSha256']=sha(raw);row['glyphHex']=raw.hex(' ').upper()
        row['placement']={'bbox':[x['left_blank'],4,14-x['right_blank'],14],
            'rule':'reviewed native digit, 14px advance centre, bottom y13','strokes_preserved':True}
    atlas['digit_font_geometry']=b['rows']
    atlas.setdefault('notes',[]).append('v294按维护者确认预览统一ASCII及原生0–9为10像素高、字底y13；汉字及字距不改，5保持居中，4保留整像素取整。')
    atlasfile='docs/SINGLE_GLYPH_ATLAS_V294_DIGITS_20261017_01.json';assert not(P/atlasfile).exists()
    (P/atlasfile).write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    overlay='text/translations/digit_font_user_confirmed_v294_20261017_01.json';assert not(P/overlay).exists()
    z={'schema':'user-confirmed-digit-font-v1','status':'COMPILED_V294_PACKAGE31_MANUAL_PENDING',
        'confirmation':'维护者查看大小／字底预览和逐格居中核查后明确“好，请修复”。',
        'approved_candidate':b['approved_candidate'],'approved_candidate_SHA256':b['approved_candidate_SHA256'],
        'ROM_SHA256':b['SHA256'],'digit_height':10,'body_baseline_y':13,'character_advance_unchanged':14,
        'digit5_left_and_right_blank':[3,3],'glyphs':b['rows'],'font_atlas':atlasfile,
        'build':'qa/V294_DIGIT_FONT_BUILD_20261017_01.json','verification':'qa/V294_DIGIT_FONT_VERIFICATION_20261017_01.json'}
    (P/overlay).write_text(json.dumps(z,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    public=copy.deepcopy(m['latest_public_release'])
    m.update(source_revision='20261017_digit_font_v294_01',build_revision='v294_digit_font01',status='COMPILED_PRIVATE_TEST_PACKAGE31_MANUAL_PENDING',
        previous_sources_manifest='text/translations/translation_sources_before_v294_20261017_01.json',
        previous_test_ROM=copy.deepcopy(m['latest_test_ROM']),previous_test_package=copy.deepcopy(m['latest_test_package']),
        latest_test_ROM={'file':b['ROM'],'SHA256':b['SHA256']},latest_test_package={'file':p['ZIP'],'SHA256':p['ZIP_SHA256']},
        latest_font_atlas=atlasfile,latest_digit_font_overlay=overlay,latest_digit_font_build='qa/V294_DIGIT_FONT_BUILD_20261017_01.json',
        latest_digit_font_validation='qa/V294_DIGIT_FONT_VERIFICATION_20261017_01.json',latest_validation='qa/V294_TESTPACKAGE31_PROOF_20261017_01.json',
        latest_handoff='docs/HANDOFF_CODEX_20261017_V294_DIGIT_FONT_01.md',latest_save_slot_mapping=p['package_directory']+'/版本与存档来源.json',
        next_action='复测v294/包31数字：重新触发“大约15年前”等对白，确认大小、字底与居中；继续既有标题、自然战斗及剩余排版待核。')
    m['source_precedence'].append('v294数字字体最终层：在v293后应用digit_font_user_confirmed_v294_20261017_01和build_v294_digit_font_v1。保持编码映射，ASCII小号数字及原生23xx全套0–9同步采用确认的10像素高字形、字底y13；78/7D别名同步，5左右各3像素，字距不改。只有20个数字字形位置和校验和变化，汉字、全部文本、剧情、绘字代码与v293标题模块保持。不能由旧TTF数字或v290字库快照回退本层。')
    assert m['latest_public_release']==public and public['version']=='0.1.3'
    current.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    tracker=rd('text/translations/feedback_deferred_current.json')
    case=next(x for x in tracker['cases']if x['id']=='DIALOGUE-DIGIT-GEOMETRY-007')
    case.update(status='fixed_private_test_manual_pending',current_action='v294/包31已编入确认字形，统一0–9为10像素高、字底y13；居中及字距按预览保持。',
        latest_test_package=p['ZIP'],verification='qa/V294_DIGIT_FONT_VERIFICATION_20261017_01.json',handoff=m['latest_handoff'])
    (P/'text/translations/feedback_deferred_current.json').write_text(json.dumps(tracker,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'build_revision':m['build_revision'],'ROM_SHA256':b['SHA256'],'latest_font_atlas':atlasfile,'public_release_unchanged':public['version']},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
