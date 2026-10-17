"""Extract the four native title-prologue pages and existing Chinese shadows.

Read-only ROM inspection. Outputs source bytes, decoded text, layout padding,
and the existing translation; it does not change a ROM or any translation.
"""
from pathlib import Path
import hashlib,json,sys
from audit_linebreak_feedback_readonly_v1 import payload
from scan_rom_inventory import decode_bytes

P=Path(__file__).resolve().parents[1]
sha=lambda z:hashlib.sha256(z).hexdigest().upper()
rd=lambda f:json.loads((P/f).read_text(encoding='utf-8-sig'))
PAGES=[(0x805,0x3C0937,0x3C093D,0x3C09C4,'死食'),
       (0x806,0x3C09C4,0x3C09CA,0x3C0A72,'魔王'),
       (0x807,0x3C0A72,0x3C0A78,0x3C0B3B,'圣王'),
       (0x808,0x3C0B3B,0x3C0B3F,0x3C0BD4,'新的宿命之子')]


def display_japanese(text):
    # These legacy decoder labels represent visually identical/near-identical
    # native glyph aliases. Keep the untouched decoding and bytes in JSON.
    for old,new in [('すベて','すべて'),('モンスタ一','モンスター'),
                    ('ゲ一ト','ゲート'),('アビスヘ','アビスへ'),('いずこかヘ','いずこかへ')]:
        text=text.replace(old,new)
    return text


def readable(text):
    return '\n'.join(line.strip() for line in text.split('{NEWLINE}'))


def main():
    output=P/'text/extracted/title_prologue_v292_20261017_01.json'
    review=P/'docs/标题动画序文_日中对照_20261017.txt'
    for f in [output,review]:
        assert f.resolve().is_relative_to(P) and not f.exists()
    m=rd('text/translations/translation_sources_current.json')
    rompath=P/m['latest_test_ROM']['file'];rom=rompath.read_bytes()
    sourcepath=P.parent/'roms/source/bokuno_proto_1.123_analysis.sfc';source=sourcepath.read_bytes()
    assert sha(rom)==m['latest_test_ROM']['SHA256']
    assert sha(source)=='4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0'
    catalog=rd('text/translation_catalog.json')['entries']
    baseline=rd('docs/ALINE_V10AJ264_BATCH263B_STORY_20261008_05.json')['records']
    rows=[]
    for event,block,start,end,title in PAGES:
        item=next(r for r in catalog if int(r['offset'],16)==block)
        assert block+int(item['metadata']['relative_start'],16)==start
        raw=source[start:end];assert raw==bytes.fromhex(item['raw'])
        assert rom[start:end]==raw
        decoded=decode_bytes(raw);assert decoded==item['source']
        record=next(r for r in baseline if int(r['source'],16)==start)
        target,body,tail=payload(rom,record)
        assert body==bytes.fromhex(record['encoded'])
        prefix=rom[block:start];assert prefix==source[block:start]
        rows.append({'page':len(rows)+1,'title':title,'native_event':f'{event:04X}',
            'native_block':f'{block:06X}','native_text_start':f'{start:06X}',
            'native_text_end_exclusive':f'{end:06X}','native_text_bytes':len(raw),
            'native_prefix_hex':prefix.hex(' ').upper(),'native_text_hex':raw.hex(' ').upper(),
            'native_text_SHA256':sha(raw),'japanese_decoded_tokens':decoded,
            'japanese_display_tokens':display_japanese(decoded),
            'japanese_display_lines':display_japanese(decoded).split('{NEWLINE}'),
            'existing_chinese_tokens':record['zh'],'existing_chinese_lines':record['zh'].split('{NEWLINE}'),
            'line_count':len(decoded.split('{NEWLINE}')),'shadow_record_id':record['id'],
            'current_shadow_target':f'{target:06X}','current_shadow_hex':body.hex(' ').upper(),
            'current_shadow_return_hex':tail.hex(' ').upper(),
            'current_shadow_matches_existing_translation':True,'native_Japanese_bytes_retained':True})
    proof={'schema':'title-prologue-four-page-extraction-v1','status':'FOUR_PAGES_ROM_BYTES_AND_EXISTING_SHADOWS_VERIFIED',
        'ROM':rompath.relative_to(P).as_posix(),'ROM_SHA256':sha(rom),
        'source_ROM_SHA256':sha(source),'page_count':len(rows),'pages':rows,
        'ROM_write_performed':False,'translation_changes_performed':False,
        'runtime_title_display_route_traced':False,
        'scope':'Four world-history pages beginning with 死食; title demo scenes and credits are outside this extraction.',
        'normalization':'Readable Japanese normalizes selected legacy ベ/一/ヘ glyph labels; raw bytes and unchanged decoding are retained.',
        'finding':'The current ROM retains native Japanese text and also contains corresponding Chinese shadow payloads. The user screenshot shows Japanese in the title animation; the precise rendering/lookup bypass remains untraced.'}
    output.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    lines=['标题动画序文：四屏日中对照','提取日期：2026-10-17',
        '对应版本：v292／包29，与公开v0.1.3目标一致。',
        '日文直接解码自ROM；中文为现有影子译文，供核对，并非本次新译或实际标题画面显示证明。',
        '阅读版省去居中空格，规范べ／ー／へ等同形字标签；JSON保留原始字节、解码和全部空格。',
        '本次未修改ROM；标题动画未使用现有中文的具体原因仍需追踪显示入口。','']
    for row in rows:
        lines += ['='*40,f"第{row['page']}屏：{row['title']}",
            f"原生事件 {row['native_event']}；正文 {row['native_text_start']}..{row['native_text_end_exclusive']}（末地址不含）",'',
            '【日文原文】',readable(row['japanese_display_tokens']),'',
            '【现有中文译文】',readable(row['existing_chinese_tokens']),'']
    review.write_text('\n'.join(lines)+'\n',encoding='utf8',newline='\n')
    assert rompath.read_bytes()==rom and sourcepath.read_bytes()==source
    assert len(rows)==4 and [r['line_count']for r in rows]==[10,11,11,10]
    print(json.dumps({'status':proof['status'],'page_count':len(rows),
        'line_counts':[r['line_count']for r in rows],
        'review':str(review),'evidence':str(output),'ROM_unchanged':True},ensure_ascii=False))


if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
