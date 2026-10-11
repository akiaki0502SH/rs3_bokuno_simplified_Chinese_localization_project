#!/usr/bin/env python3
"""Read-only inventory for the bokuno Proto1.123 localization project.

The script deliberately writes nothing.  It emits JSON so later extraction,
translation, and reinsertion tools can consume a stable machine-readable
baseline without touching the source ROM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_ROM = Path(__file__).resolve().parents[2] / "roms" / "source" / "bokuno_proto_1.123_analysis.sfc"


SINGLE = (
    "〓" * 0x50
    + "□あいうえおかきくけこさしすせそ"
    + "たちつてとなにぬねのはひふほまみ"
    + "むめもやゆよらりるれろわをんゃゅょっ"
    + "アイウエオカキクケコサシスセソ"
    + "タチツテトナニヌネノハヒフヘホ"
    + "マミムメモヤユヨラリルレロワンァ"
    + "ィゥェォャュョッがぎぐげござじず"
    + "ぜぞだぢづでどばびぶぼガギグゲゴ"
    + "ザジズゼゾダヂヅデドバビブベボパ"
    + "ピプペポヴ一□。、…！？・様行私"
    + "人出何王〜来間大前戦力見中者聖言"
)

TABLE_20 = [
    "□あいうえおかきくけこさしすせそ",
    "たちってとなにぬねのはひふほまみ",
    "むめもやゆよらりるれろわをんゃゅ",
    "ょっアイウエオカキクケコサシスセ",
    "ソタチツテトナニヌネノハヒフヘホ",
    "マミムメモヤユヨラリルレロワンァ",
    "ィゥェォャュョッがぎぐげござじず",
    "ぜぞだぢづでどばびぶぼガギグゲゴ",
    "ザジズゼゾダヂヅデドバビブベボパ",
    "ピプペポヴ一□。、…！？・様行私",
    "人出何王〜来間大前戦力見中者聖言",
    "魔無方手話事今達気開町世会入物子",
    "死知乗術君教族所発上殿家軍別待商",
    "仲海金城助分動持後地取神本思変緒",
    "連敵団報当残合情命心下部聞勝界頼",
    "作体休戻西生船場良最備度帰立近丈",
]
TABLE_21 = [
    "万兵逃夫侯元名破売食怪少々年公配",
    "奴明姫屋成自男士時武止貴宿新住長",
    "着礼必通捕仕以夢北兄日宝使始好父",
    "引外二準呼願要倒先突宮強天説山険",
    "小衛決欲足定係高玄協将構美村隠集",
    "妹有姉安遊関閉国市闘竜女娘不東探",
    "指目殺工房黄爵我判護結親現悪得理",
    "赤賊客壊寝特陣京内老守旅彼念用進",
    "難街代味参意危受幸許活多品槍盗消",
    "徒加島実置身付伝回支覚空原撃申財",
    "攻全防列隊技剣産復石御社形退水件",
    "器龍運投道果打薬業低法状資弓早星",
    "織切光況効同揮弱精三鎧重流乱矢妖",
    "翼農直失書買毒化毛月陽速影落告木",
    "却奪終具腕白草盾太馬段斬血相主花",
    "性抜酒造門官絶減令次数続位収信砂",
]
TABLE_22 = [
    "封野波盟素向巣正風料与面文滅土在",
    "操氷壁射放火眠鳥敗皮起遠恐存口断",
    "装窟番葉調混返交喜込漠飛完製底夜",
    "炎鉄威騎斧十惑平率的員店職陸増予",
    "能邪負選送才熱雪紙初感苦供触玉座",
    "楽吸鬼洞息輪挑追襲練祈侵傷粉杯考",
    "冷違南昔急態臣ぱ嫁望働記頭移井戸",
    "争森針払蒼義普押傭都沼易機反魚超",
    "視鉱牧材差勇祖霧色誘嫌期演真四詩",
    "共舞確散館学越統然棒民％走虎獣異",
    "叩政央策想塔巻刀害幻衝了総頂岩骨",
    "派泊預役寄降習読暗声顔奥旧深営談",
    "秘飲制狩試魅群震師税雷拓銀鱗棍割",
    "脳転功塩穴冒頃肉港格恋霊労噂皆婚",
    "掛音救印久朱優像古値妻研究晶猛嵐",
    "河静激利稲砕温革環蛇雨電爆両羊陶",
]
TABLE_23 = [
    "０１２３４５６７８９ＨＬＰ／←：",
    "芸対永遅若迷張援伯離表母展背独握",
    "闇髪禁遺傑由帯渡授瞳限浮湖観廃倉",
    "庫巨側曲満腐旗勢常瞬杖眼字牙奇尾",
    "振凝催線境綿貿注治跡答建逆閣恩飾",
    "沈忘罪継解麻笑弟過扉画洋墟姿溶七",
    "黒栄億点蹴鏡角香削千避妨絹茶額求",
    "廟牢討任賞亡興問没右識末鎖腹五縦",
    "再築友和志坊乾兆警戒陰福偽歩朝鳴",
    "算級爪狼浪疾拳液裂貫極熟損号林敢",
    "犠牲短勉験墓疲悟届式責暮留左冗病",
    "未驚幅測窓青塞寺院語泣謀創充軽煙",
    "滝到峠抗征誉届謝片計領局鳳辰宵甲",
    "羅刹屍閃双車勁烈臨熒縛順歳殊設各",
    "糸丘誓案敬慮縁伏密兼孫景呪倍阻占",
    "伐幕清仁覆嬢諸亜居酸津智鎮略根汗",
]

TABLES = ["".join(row) for row in (TABLE_20, TABLE_21, TABLE_22, TABLE_23)]
# Bokuno also moves 犠 to 181F and repurposes vanilla 23A0 as 帥.
TABLES[3] = TABLES[3][:0xA0] + "帥" + TABLES[3][0xA1:]
# 23FF is a deliberately altered variant used consistently as 一 in names and
# prose (一人時間差/一文無し/世界一). Semantic evidence outweighs its
# visually similar vanilla 汗 bitmap.
TABLES[3] = TABLES[3][:-1] + "一"

# Bokuno's 18xx bank is stored at file 0x608000 as 256 16x16 1bpp glyphs.
# Only visually/contextually confirmed mappings are named here. Unknown codes
# remain explicit tokens so they cannot be silently mistranslated.
EXTENDED_KNOWN = {
    0x10: "皇", 0x11: "帝", 0x13: "雄", 0x14: "英", 0x17: "証",
    0x18: "魂", 0x1B: "刃", 0x1C: "虫", 0x1D: "誰", 0x1E: "卵", 0x1F: "犠",
    0x20: "僕", 0x22: "刺", 0x25: "亀", 0x26: "惚", 0x27: "譲", 0x28: "堅", 0x2B: "服", 0x2C: "鋼", 0x2D: "可",
    0x30: "他", 0x32: "妙", 0x33: "掌", 0x35: "旋", 0x39: "従", 0x3B: "痛", 0x3C: "吹", 0x3D: "尽",
    0x3F: "黒", 0x40: "賢", 0x41: "祝", 0x42: "歌", 0x44: "底", 0x45: "横", 0x47: "借",
    0x4C: "々", 0x4D: "末", 0x4E: "室", 0x4F: "限", 0x54: "脅", 0x55: "駄",
    0x56: "叉", 0x57: "雲", 0x59: "府", 0x5A: "認", 0x5B: "薔", 0x5C: "薇",
    0x5D: "暴", 0x5E: "困", 0x61: "札", 0x63: "悔", 0x65: "憶", 0x6B: "柱", 0x6D: "樹",
    0x70: "怖", 0x71: "隷", 0x72: "憎", 0x74: "冥", 0x75: "僧", 0x77: "胸", 0x78: "恨", 0x79: "台",
    0x7A: "策", 0x7C: "並", 0x7D: "約", 0x7E: "束", 0x80: "罰", 0x81: "終", 0x82: "葬", 0x83: "崩", 0x89: "輝",
    0x84: "徹", 0x86: "耐", 0x87: "応", 0x8B: "悲", 0x8C: "託", 0x8E: "仮", 0x90: "除", 0x91: "辱", 0x92: "個",
    0x93: "耐", 0x96: "半", 0x97: "戮", 0x99: "騎", 0x9E: "捧",
    0x9C: "撃", 0xA0: "粗", 0xA1: "隅", 0xA2: "費", 0xA8: "貸", 0xA9: "呼", 0xAB: "獅", 0xAC: "怒", 0xAE: "訳", 0xB1: "登", 0xB2: "首",
    0xB4: "銃", 0xB5: "踊", 0xB6: "＝", 0xB7: "晴", 0xBA: "堂", 0xBC: "羽",
    0xBE: "蜘", 0xBF: "蛛", 0xC1: "八", 0xC5: "為", 0xC6: "掃", 0xC7: "砲",
    0xC8: "衝", 0xC9: "儀", 0xCB: "汗", 0xD5: "飛", 0xD6: "泥", 0xE1: "廟", 0xE9: "乱", 0xED: "謎", 0xEE: "微", 0xFD: "致",
    0xF2: "議", 0xF3: "修", 0xFB: "踪", 0xF4: "園", 0xF5: "辺", 0xF9: "拾", 0xFC: "騒", 0xFE: "量",
}

# 46xx is a two-byte native glyph page in the author runtime text reader.
# Mappings below were checked against original ROM bitmaps and sentence context.
NATIVE46_KNOWN = {0x14: "図", 0x26: "噴", 0x32: "育", 0x33: "枚", 0x34: "抱", 0x36: "医", 0x38: "階", 0x39: "説", 0x3A: "敷", 0x40: "鍛", 0x42: "脱", 0x47: "咫", 0x48: "勾", 0x49: "尺", 0x4A: "瓊", 0x4B: "叢", 0x4C: "虚", 0x4D: "努", 0x4E: "招", 0x5E: "容", 0x5F: "胞", 0x61: "種", 0x67: "積", 0x68: "示", 0x6A: "権", 0x6B: "劇", 0x78: "替"}

# 2026-10-10: confirmed against original18xx/46xx glyph bitmaps.
EXTENDED_KNOWN.update({54: '己', 100: '障', 105: '祝', 159: '召', 167: '焼', 173: '猟', 180: '銃', 185: '克', 240: '撹'})
NATIVE46_KNOWN.update({83: '醒', 115: '脈'})

# 2026-10-11: verified original-ROM glyphs used in the complete menu review.
EXTENDED_KNOWN.update({22: '虫', 47: '潰', 67: '狙', 102: '固', 104: '凍', 110: '即', 165: '咲', 170: '狂', 189: '翔', 206: '圧', 211: '匹', 221: '潜', 222: '接', 227: '臓', 230: '喪', 232: '痺', 234: '拍', 235: '縮', 255: '華', 153: '衣', 156: '弾', 79: '縫', 187: '麒', 202: '麟', 103: '百', 155: '繚', 163: '愚', 108: '彗', 136: '冠', 52: '踏', 223: '換'})
NATIVE46_KNOWN.update({16: '蓮', 32: '貨', 69: '冬', 99: '渦', 40: '板', 102: '緋'})

if len(SINGLE) != 256 or any(len(table) != 256 for table in TABLES):
    raise RuntimeError("RS3 text table definition has an invalid length")


def hex_range(start: int, end: int) -> dict[str, int | str]:
    return {"start": f"0x{start:06X}", "end": f"0x{end:06X}", "length": end - start}


def byte_runs(data: bytes, value: int, minimum: int = 0x100) -> list[dict[str, int | str]]:
    found: list[tuple[int, int]] = []
    index = 0
    while index < len(data):
        if data[index] != value:
            index += 1
            continue
        start = index
        while index < len(data) and data[index] == value:
            index += 1
        if index - start >= minimum:
            found.append((index - start, start))
    found.sort(reverse=True)
    return [
        {"start": f"0x{start:06X}", "end": f"0x{start + length - 1:06X}", "length": length}
        for length, start in found[:40]
    ]


def decode_bytes(data: bytes, *, battle: bool = False, native46_glyphs: bool = False) -> str:
    output: list[str] = []
    index = 0
    while index < len(data):
        value = data[index]
        if 0x20 <= value <= 0x23 and index + 1 < len(data):
            output.append(TABLES[value - 0x20][data[index + 1]])
            index += 2
            continue
        if value == 0x18 and index + 1 < len(data) and data[index + 1] >= 0x10:
            low = data[index + 1]
            output.append(EXTENDED_KNOWN.get(low, f"{{EXT18:{low:02X}}}"))
            index += 2
            continue
        if value == 0x18 and index + 1 < len(data):
            output.append(f"{{CODE:18{data[index + 1]:02X}}}")
            index += 2
            continue
        if native46_glyphs and value == 0x46 and index + 1 < len(data):
            low = data[index + 1]
            output.append(NATIVE46_KNOWN.get(low, f"{{EXT46:{low:02X}}}"))
            index += 2
            continue
        if value == 0x24:
            output.append("{NEWLINE}")
        elif value == 0x25 and battle and index + 1 < len(data):
            output.append(f"{{WAIT:{data[index + 1]:02X}}}")
            index += 1
        elif value == 0x25:
            output.append("{CHOICE_START}")
        elif value == 0x26:
            output.append("{CHOICE_ITEM}")
        elif value == 0x27:
            output.append("{CHOICE_END}")
        elif value == 0x28:
            output.append("{WINDOW_SELF}")
        elif value == 0x29:
            output.append("{WINDOW_OTHER}")
        elif value == 0x2A:
            output.append("{WINDOW_CLOSE}")
        elif value == 0x2B and index + 1 < len(data):
            output.append(f"{{WAIT:{data[index + 1]:02X}}}")
            index += 1
        elif value == 0x2C:
            output.append("{BUTTON_WAIT}")
        elif value == 0x2D:
            output.append("{COLOR_TOGGLE}")
        elif value == 0x39 and index + 1 < len(data):
            output.append(f"{{PARTY_NAME:{data[index + 1]:02X}}}")
            index += 1
        elif value == 0x3A and index + 1 < len(data):
            output.append(f"{{ITEM_NAME:{data[index + 1]:02X}}}")
            index += 1
        elif value == 0x3B and index + 1 < len(data):
            output.append(f"{{LOCATION:{data[index + 1]:02X}}}")
            index += 1
        elif value == 0x4A and index + 1 < len(data):
            output.append(f"{{CHARACTER_NAME:{data[index + 1]:02X}}}")
            index += 1
        elif value == 0x50:
            output.append(" ")
        elif value < 0x50:
            output.append(f"{{CODE:{value:02X}}}")
        else:
            output.append(SINGLE[value])
        index += 1
    return "".join(output)


def fixed_record(data: bytes, offset: int, size: int) -> dict[str, object]:
    raw = data[offset : offset + size]
    return {
        "offset": f"0x{offset:06X}",
        "size": size,
        "raw": raw.hex(" "),
        "decoded": decode_bytes(raw),
    }


def battle_messages(data: bytes) -> dict[str, object]:
    pointer_base = 0x3D9800
    text_base = 0x3D9A00
    values: list[int] = []
    for index in range(0x80):
        value = int.from_bytes(data[pointer_base + index * 2 : pointer_base + index * 2 + 2], "little")
        if value == 0xFFFF:
            break
        if values and value < values[-1]:
            break
        values.append(value)
    messages = []
    for index in range(max(0, len(values) - 1)):
        start = text_base + values[index]
        end = text_base + values[index + 1]
        messages.append(
            {
                "id": index,
                "start": f"0x{start:06X}",
                "end": f"0x{end - 1:06X}",
                "length": end - start,
                "text": decode_bytes(data[start:end], battle=True),
            }
        )
    return {
        "pointer_table": hex_range(pointer_base, pointer_base + len(values) * 2),
        "text_base": f"0x{text_base:06X}",
        "pointer_count_including_end": len(values),
        "messages": messages,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    args = parser.parse_args()
    path = args.rom.resolve()
    data = path.read_bytes()
    has_header = len(data) >= 0x200 and len(data) % 0x8000 == 0x200
    body = data[0x200:] if has_header else data
    report = {
        "project": "bokuno_cn",
        "phase": "static_inventory",
        "read_only": True,
        "rom": {
            "path": str(path),
            "file_size": len(data),
            "body_size": len(body),
            "has_512_byte_header": has_header,
            "sha256": hashlib.sha256(body).hexdigest().upper(),
        },
        "known_ranges": {
            "character_name_record": hex_range(0x3D18B8, 0x3D18C0),
            "battle_message_offset_table": hex_range(0x3D9800, 0x3D9A00),
            "battle_message_text_area": hex_range(0x3D9A00, 0x3DA800),
            "monster_name_table_reference": hex_range(0x5A2D00, 0x5A3600),
            "current_graphic_manifest_reserved": hex_range(0x7D0000, 0x800000),
        },
        "fixed_records": {
            "character_name_record": fixed_record(data, 0x3D18B8, 8),
            "monster_name_records_first_8": [fixed_record(data, 0x5A2D00 + index * 12, 12) for index in range(8)],
        },
        "battle_messages": battle_messages(data),
        "free_run_candidates": {
            "ff": byte_runs(data, 0xFF),
            "zero": byte_runs(data, 0x00),
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
