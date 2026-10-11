"""Resolve the five user-reviewed tables and audit impact without changing ROMs."""
from __future__ import annotations

import collections
import hashlib
import html
import json
from pathlib import Path
import re
import sys

from dry_run_encoding_plan import encode

P = Path(__file__).resolve().parents[1]
REVIEW = P / "docs/missing_translation_review_20261011"
OUT = P / "qa/MISSING_TRANSLATION_GLOBAL_IMPACT_20261011_01.json"


def read_json(path):
    return json.loads((P / path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256((P / path).read_bytes()).hexdigest().upper()


def norm(text):
    text = re.sub(r"\{CODE:00\}", "", text)
    text = re.sub(r"(?<=[ァ-ヶ])一(?=[ァ-ヶ]|$)", "ー", text)
    return re.sub(r"\s+", "", text)


def parse_review():
    result = []
    for path in sorted(REVIEW.glob("0*.md")):
        internal = False
        for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if line.startswith("## "):
                internal = "内部占位" in line
            line = line.strip()
            if not re.match(r"\|\s*[KTMUI][0-9]{3}\s*\|", line):
                continue
            assert line.endswith("|"), (path, line_number)
            # Remove exactly one framing pipe: strip('|') loses empty final cells.
            cells = [html.unescape(s).strip() for s in line[1:-1].split("|")]
            assert len(cells) == 4, (path, line_number, cells)
            identifier, jp, suggestion, confirmed = cells
            assert suggestion or confirmed, identifier
            result.append({
                "file": path.relative_to(P).as_posix(), "line": line_number,
                "id": identifier, "jp": jp, "suggested_zh": suggestion,
                "confirmed_zh": confirmed, "resolved_zh": confirmed or suggestion,
                "selection": "confirmed_column" if confirmed else "suggested_column_fallback",
                "internal_or_input_character": internal,
            })
    return result


def main():
    manifest = read_json("text/translations/translation_sources_current.json")
    inventory_file = "text/extracted/missing_menu_inventory_v282_20261011_01.json"
    inventory = read_json(inventory_file)
    original_rows = {x["id"]: x for x in inventory["rows"]}
    rows = parse_review()
    assert len(rows) == len({x["id"] for x in rows}) == 703
    assert set(original_rows) == {x["id"] for x in rows}
    mapping_file = "qa/V281_CURRENT_SINGLE_GLYPH_MAPPING_20261011_06.json"
    pairs_file = "qa/V281_CURRENT_FIXED_MENU_PAIRS_20261011_02.json"
    atlas_file = "docs/SINGLE_GLYPH_ATLAS_V281_FEEDBACK_20261011_06.json"
    mapping = {k: bytes.fromhex(v) for k, v in read_json(mapping_file).items()}
    pairs = {k: bytes.fromhex(v) for k, v in read_json(pairs_file).items()}
    atlas = read_json(atlas_file)
    # ASCII aliases can use existing full-width letter glyphs; this is an encoding
    # proposal, not a new installed mapping or evidence of half-width rendering.
    aliases = {}
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789":
        wide = chr(ord(ch) + 0xFEE0)
        if ch not in mapping and wide in mapping:
            aliases[ch] = mapping[wide]
    effective = mapping | aliases
    missing_by_char = collections.defaultdict(list)
    missing_literal_by_char = collections.defaultdict(list)
    for row in rows:
        original = original_rows[row["id"]]
        row.update({k: original[k] for k in ["kind", "index", "offset", "capacity", "related"]})
        row["inventory_confirmed_column_outdated"] = row["confirmed_zh"] != original["confirmed_zh"]
        row["inventory_suggestion_outdated"] = row["suggested_zh"] != original["suggested_zh"]
        row["review_annotations"] = re.findall(r"〔[^〕]*〕|（[^）]*保留[^）]*）|（[^）]*待核[^）]*）|（输入字符）", row["resolved_zh"])
        row["menu_subfields"] = row["resolved_zh"].split("／") if row["kind"] == "U" else []
        row["direct_literal_import_allowed"] = not row["internal_or_input_character"] and not row["review_annotations"] and row["kind"] != "U"
        literal_bytes, literal_missing, errors = encode(row["resolved_zh"], mapping, battle=False)
        assert not errors, (row["id"], errors)
        row["missing_literal_mapping"] = sorted(literal_missing)
        row["ascii_aliases_needed"] = sorted(set(row["resolved_zh"]) & set(aliases))
        text = row["resolved_zh"]
        if row["internal_or_input_character"]:
            text = ""  # Internal placeholders/input characters are not new prose.
        elif row["kind"] == "U":
            text = re.sub(r"〔[^〕]*〕|（[^）]*待核[^）]*）", "", text).replace("／", "")
            if row["id"] == "U060":
                # The displayed kana is an unresolved field, not an approved
                # Japanese literal to add to the Chinese font budget.
                text = text.replace("へ", "")
        _, missing, errors = encode(text, effective, battle=False)
        assert not errors
        row["required_new_glyphs_after_ascii_aliases"] = sorted(missing)
        for ch in missing:
            missing_by_char[ch].append(row["id"])
        if not row["internal_or_input_character"]:
            for ch in literal_missing:
                missing_literal_by_char[ch].append(row["id"])
        # Placeholder bytes are for conservative sizing only, never ROM payloads.
        projected = effective | {ch: b"\x10\x00" for ch in missing}
        encoded, left, errors = encode(text, projected, battle=False)
        assert not left and not errors
        row["projected_unwrapped_bytes"] = len(encoded)
        row["resolved_character_count"] = len(row["resolved_zh"])
        row["compiled_current_bytes_differ_from_original"] = None
        if row["kind"] == "K" and not row["internal_or_input_character"]:
            compact, left, errors = encode(text, projected | pairs, battle=False)
            assert not left and not errors
            row["projected_fixed_menu_compact_bytes"] = len(compact)
            row["name_over_10_bytes"] = len(encoded) > 10
            row["name_over_10_bytes_even_with_existing_pairs"] = len(compact) > 10
        if row["kind"] in {"T", "M", "I"}:
            row["description_over_63_bytes_unwrapped"] = len(encoded) > 63
            # Fourteen cells is the existing ordinary description wrapper's limit.
            # Expanded comment renderers still need their own visual verification.
            line_count = (len(text) + 13) // 14
            row["14_cell_lines_estimate"] = line_count
            row["projected_bytes_with_14_cell_breaks"] = len(encoded) + max(0, line_count - 1)
            row["description_over_63_bytes_with_14_cell_breaks"] = row["projected_bytes_with_14_cell_breaks"] > 63

    typed = read_json(manifest["latest_typed_review"])["translations"]
    skills = read_json(manifest["latest_techniques_and_spells"])
    items = read_json(manifest["latest_items"])["translations"]
    current_names = collections.defaultdict(list)
    for item in typed:
        if not item["id"].startswith(("P", "E", "N", "I")):
            continue
        for jp in set(filter(None, [item.get("jp"), item.get("source_corrected")])):
            current_names[norm(jp)].append({
                "source_file": manifest["latest_typed_review"], "id": item["id"],
                "jp": jp, "zh": item["translation_zh_cn"], "offset": item.get("source_offset"),
            })
    for group in ["techniques", "spells"]:
        for item in skills[group]:
            current_names[norm(item["jp"])].append({
                "source_file": manifest["latest_techniques_and_spells"],
                "id": item["id"], "jp": item["jp"], "zh": item["zh"],
                "offset": item.get("name_offset", item.get("source_name_offset")),
            })
    for item in items:
        current_names[norm(item["source_jp"])].append({
            "source_file": manifest["latest_items"], "id": item.get("complete_review_id", item.get("id")),
            "jp": item["source_jp"], "zh": item["translation_zh_cn"], "offset": item.get("offset"),
        })
    conflicts = []
    for row in rows:
        if row["kind"] != "K" or row["internal_or_input_character"]:
            continue
        matches = current_names[norm(row["jp"])]
        unique = {(m["source_file"], m["id"], m["zh"]): m for m in matches}
        row["existing_name_matches"] = list(unique.values())
        differing = [m for m in unique.values() if m["zh"] != row["resolved_zh"]]
        if differing:
            conflicts.append({"id": row["id"], "jp": row["jp"], "new_zh": row["resolved_zh"], "selection": row["selection"], "existing_differing": differing})
    duplicate_disagreements = []
    group_rows = collections.defaultdict(list)
    for row in rows:
        group_rows[(row["kind"], norm(row["jp"]))].append(row)
    for group in group_rows.values():
        if len({r["resolved_zh"] for r in group}) > 1:
            duplicate_disagreements.append({"jp": group[0]["jp"], "rows": [{"id": r["id"], "zh": r["resolved_zh"]} for r in group]})
    collisions = []
    by_translation = collections.defaultdict(list)
    for row in rows:
        if row["kind"] == "K" and not row["internal_or_input_character"]:
            by_translation[row["resolved_zh"]].append(row)
    for zh, group in by_translation.items():
        if len({norm(r["jp"]) for r in group}) > 1:
            collisions.append({"zh": zh, "rows": [{"id": r["id"], "jp": r["jp"]} for r in group]})

    rom_file = manifest["latest_test_ROM"]["file"]
    rom = (P / rom_file).read_bytes()
    assert digest(rom_file) == manifest["latest_test_ROM"]["SHA256"]
    source = (P / "../roms/source/bokuno_proto_1.123_analysis.sfc").read_bytes()
    assert hashlib.sha256(source).hexdigest().upper() == inventory["source_SHA256"]
    for row in rows:
        at = int(row["offset"], 16)
        size = row["capacity"]
        assert source[at:at+size] == bytes.fromhex(original_rows[row["id"]]["raw_hex"]), row["id"]
        row["compiled_current_bytes_differ_from_original"] = rom[at:at+size] != source[at:at+size]
        if row["kind"] == "U" and row["index"] < 72:
            ptr = int.from_bytes(rom[0x3DF976+row["index"]*2:0x3DF978+row["index"]*2], "little") + 0x3DFA08
            row["current_menu_pointer_offset"] = f"{ptr:06X}"
            row["current_menu_pointer_relocated"] = ptr != at

    counts = {}
    for kind in "KTMIU":
        selected = [r for r in rows if r["kind"] == kind]
        counts[kind] = {
            "total": len(selected), "confirmed_column": sum(bool(r["confirmed_zh"]) for r in selected),
            "suggestion_fallback": sum(not r["confirmed_zh"] for r in selected),
            "internal_or_input": sum(r["internal_or_input_character"] for r in selected),
            "original_records_unchanged_in_current_ROM": sum(not r["compiled_current_bytes_differ_from_original"] for r in selected),
            "missing_new_glyph_rows": sum(bool(r["required_new_glyphs_after_ascii_aliases"]) for r in selected),
        }
    protected_files = [r["file"] for r in rows]
    protected_files = sorted(set(protected_files)) + [
        inventory_file, "text/translations/translation_sources_current.json",
        manifest["latest_typed_review"], manifest["latest_techniques_and_spells"], manifest["latest_items"],
        mapping_file, pairs_file, atlas_file, rom_file, manifest["latest_test_package"]["file"],
    ]
    report = {
        "schema": "missing-translation-global-impact-v1",
        "policy": "Only the five named 20261011 tables: confirmed column first; blank/HTML nbsp uses suggested column. Preserve older policy outside this scope.",
        "status": "ASSESSMENT_ONLY_NOT_COMPILED",
        "current_build_revision": manifest["build_revision"],
        "no_ROM_current_source_or_review_document_writes": True,
        "input_SHA256": {f: digest(f) for f in protected_files},
        "counts": counts, "total_rows": len(rows),
        "confirmed_column_total": sum(bool(r["confirmed_zh"]) for r in rows),
        "suggestion_fallback_total": sum(not r["confirmed_zh"] for r in rows),
        "internal_rows": [r["id"] for r in rows if r["internal_or_input_character"]],
        "empty_original_slots_preserved_count": len(inventory["empty_slots"]),
        "inventory_confirmed_stale_ids": [r["id"] for r in rows if r["inventory_confirmed_column_outdated"]],
        "inventory_suggested_stale_ids": [r["id"] for r in rows if r["inventory_suggestion_outdated"]],
        "font_capacity": atlas["summary"],
        "missing_new_glyph_count_after_ascii_aliases": len(missing_by_char),
        "missing_mapping_note": "These characters need a verified encoding or glyph. Map absence alone does not prove a new bitmap/slot is needed; native bitmap reuse must be checked separately.",
        "missing_new_glyph_occurrences": dict(sorted(missing_by_char.items())),
        "literal_missing_before_menu_annotation_removal_and_ascii_aliases": dict(sorted(missing_literal_by_char.items())),
        "proposed_ASCII_aliases": {k: v.hex(" ").upper() for k, v in aliases.items()},
        "ASCII_alias_note": "Reuses existing letter bitmap; no promise of half-width Latin rendering. Installed mappings remain unchanged.",
        "names_over_10_bytes_ids": [r["id"] for r in rows if r.get("name_over_10_bytes")],
        "names_over_10_bytes_even_with_current_fixed_pairs_ids": [r["id"] for r in rows if r.get("name_over_10_bytes_even_with_existing_pairs")],
        "descriptions_over_63_bytes_unwrapped_ids": [r["id"] for r in rows if r.get("description_over_63_bytes_unwrapped")],
        "descriptions_over_63_bytes_with_14_cell_breaks_ids": [r["id"] for r in rows if r.get("description_over_63_bytes_with_14_cell_breaks")],
        "description_layout_note": "14-cell estimate comes from ordinary pool builder; expanded technique/spell/item comment UI is not visually accepted by this audit.",
        "menu_review_annotation_ids": [r["id"] for r in rows if r["kind"] == "U" and not r["internal_or_input_character"] and r["review_annotations"]],
        "menu_subfield_split_ids": [r["id"] for r in rows if r["kind"] == "U" and not r["internal_or_input_character"] and len(r["menu_subfields"]) > 1],
        "name_conflicts_with_current_sources": conflicts,
        "name_conflict_unique_original_count": len({norm(c["jp"]) for c in conflicts}),
        "same_original_different_translation_within_five_tables": duplicate_disagreements,
        "different_original_same_inherent_translation": collisions,
        "special_source_correction": {
            "review_id": "T218", "current_player_name_id": "P0219",
            "original_name": "天衣無縫", "current_zh": "天骑无限", "corrected_zh_recommendation": "天衣无缝",
            "evidence": "docs/missing_translation_review_20261011/README.md; original ROM glyph review already recorded",
            "applied": False,
        },
        "arena_reserved_directory": "7F8E00-7F9D19 (v282 bank72)",
        "current_tail_arena_end": read_json("qa/V282_TWO_DISPLAY_FIXES_BUILD_20261011_01.json")["arena_end"],
        "tail_room_before_7FFE00": 0x7FFE00-int(read_json("qa/V282_TWO_DISPLAY_FIXES_BUILD_20261011_01.json")["arena_end"], 16),
        "tail_reserved_bytes": 496,
        "reclaim_candidates_absent_from_frozen_literals_and_review": [
            {"atom": g["atom"], "code": g["code"], "status": "UNPROVEN_LIVE_USAGE_RECHECK_REQUIRED"}
            for g in atlas["glyphs"] if g["class"] == "single"
            and g["atom"] not in read_json("qa/V281_FONT_LITERAL_GUARD_20261011_01.json")["known_translation_characters"]
            and not any(g["atom"] in r["resolved_zh"] for r in rows)
        ],
        "rows": rows,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    summary_keys = ["total_rows", "confirmed_column_total", "suggestion_fallback_total", "counts", "missing_new_glyph_count_after_ascii_aliases", "missing_new_glyph_occurrences", "names_over_10_bytes_ids", "names_over_10_bytes_even_with_current_fixed_pairs_ids", "descriptions_over_63_bytes_unwrapped_ids", "descriptions_over_63_bytes_with_14_cell_breaks_ids", "menu_review_annotation_ids", "same_original_different_translation_within_five_tables", "different_original_same_inherent_translation", "tail_room_before_7FFE00"]
    print(json.dumps({k: report[k] for k in summary_keys}, ensure_ascii=False, indent=2))
    print("NAME_CONFLICTS", len(conflicts))
    for conflict in conflicts:
        print(conflict["id"], conflict["jp"], "=>", conflict["new_zh"], "; existing:", ", ".join(sorted({f"{m['id']}={m['zh']}" for m in conflict["existing_differing"]})))
    print("REPORT", str(OUT))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
