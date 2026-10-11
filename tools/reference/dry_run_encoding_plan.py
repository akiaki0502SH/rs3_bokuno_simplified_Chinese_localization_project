#!/usr/bin/env python3
"""Encode reviewed Chinese in memory and audit layout; never writes a ROM."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from scan_rom_inventory import EXTENDED_KNOWN, TABLES


TOKEN_RE = re.compile(r"\{([^{}]+)\}")
SIMPLE_TOKENS = {
    "NEWLINE": b"\x24", "CHOICE_START": b"\x25", "CHOICE_ITEM": b"\x26",
    "CHOICE_END": b"\x27", "WINDOW_SELF": b"\x28", "WINDOW_OTHER": b"\x29",
    "WINDOW_CLOSE": b"\x2a", "BUTTON_WAIT": b"\x2c", "COLOR_TOGGLE": b"\x2d",
}
POOL_CAPACITY = {
    "indexed_pool_3d6200": 0x1600,
    "indexed_pool_3d7d00": 0x1B00,
    "battle_ui_strings_3d9a00": 0x140,
    "battle_event_messages_3d9a00": 0xEC0,
}


def base_encoding() -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for high, table in zip(range(0x20, 0x24), TABLES):
        for low, character in enumerate(table):
            if character != "□":
                result.setdefault(character, bytes((high, low)))
    # Single-byte aliases are shorter and refer to the first 176 standard glyphs.
    for low in range(0xB0):
        character = TABLES[0][low]
        if character != "□":
            result[character] = bytes((0x50 + low,))
    for low, character in EXTENDED_KNOWN.items():
        result.setdefault(character, bytes((0x18, low)))
    return result


def token_bytes(name: str, *, battle: bool) -> bytes:
    if name in SIMPLE_TOKENS:
        return SIMPLE_TOKENS[name]
    if name.startswith("WAIT:"):
        return bytes((0x25 if battle else 0x2B, int(name.split(":", 1)[1], 16)))
    dynamic = {"PARTY_NAME": 0x39, "ITEM_NAME": 0x3A, "LOCATION": 0x3B, "CHARACTER_NAME": 0x4A}
    prefix, separator, value = name.partition(":")
    if prefix in dynamic and separator:
        return bytes((dynamic[prefix], int(value, 16)))
    if name.startswith("EXT18:"):
        return bytes((0x18, int(name.split(":", 1)[1], 16)))
    if name.startswith("CODE:"):
        value = name.split(":", 1)[1]
        return bytes.fromhex(value) if len(value) % 2 == 0 else bytes((int(value, 16),))
    raise ValueError(f"unsupported token {{{name}}}")


def encode(text: str, mapping: dict[str, bytes], *, battle: bool) -> tuple[bytes, set[str], list[str]]:
    output = bytearray()
    missing: set[str] = set()
    errors: list[str] = []
    cursor = 0
    def append_literal(value_text: str) -> None:
        index = 0
        while index < len(value_text):
            key = value_text[index:index + 2] if value_text[index:index + 2] in mapping else value_text[index]
            value = mapping.get(key)
            if value is None:
                missing.add(key)
            else:
                output.extend(value)
            index += len(key)
    for match in TOKEN_RE.finditer(text):
        append_literal(text[cursor : match.start()])
        try:
            output.extend(token_bytes(match.group(1), battle=battle))
        except ValueError as exc:
            errors.append(str(exc))
        cursor = match.end()
    append_literal(text[cursor:])
    return bytes(output), missing, errors


def visible_line_lengths(text: str) -> list[int]:
    lines = text.split("{NEWLINE}")
    lengths = []
    for line in lines:
        stripped = TOKEN_RE.sub("", line)
        dynamic_count = sum(
            8 for token in TOKEN_RE.findall(line)
            if token.startswith(("PARTY_NAME:", "ITEM_NAME:", "LOCATION:", "CHARACTER_NAME:"))
        )
        lengths.append(len(stripped) + dynamic_count)
    return lengths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--glyph-usage", type=Path,
                        help="Existing source-glyph usage report for legacy tentative allocation.")
    parser.add_argument("--allocation", type=Path,
                        help="A planned allocation from optimize_glyph_allocation.py.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-reviewed", action="store_true")
    args = parser.parse_args()
    if args.glyph_usage is None and args.allocation is None:
        parser.error("one of --glyph-usage or --allocation is required")
    catalog = json.loads(args.catalog.resolve().read_text(encoding="utf-8"))
    statuses = {"approved", "reviewed"} if args.include_reviewed else {"approved"}
    selected = [entry for entry in catalog["entries"] if entry.get("translation_status") in statuses]

    planned_allocation = None
    if args.allocation is not None:
        planned_allocation = json.loads(args.allocation.resolve().read_text(encoding="utf-8"))
        mapping = {" ": b"\x50"}
        for item in planned_allocation.get("allocation", []):
            if item.get("class") != "composite_pair":
                mapping[item["character"]] = bytes.fromhex(item["code"])
        fixed_mapping = dict(mapping)
        for item in planned_allocation.get("allocation", []):
            if item.get("fixed_code"):
                fixed_mapping[item["character"]] = bytes.fromhex(item["fixed_code"])
    else:
        usage = json.loads(args.glyph_usage.resolve().read_text(encoding="utf-8"))
        mapping = base_encoding()

    required_missing = sorted({ch for entry in selected for ch in entry["translation_zh_cn"] if ch not in mapping and ch != "{" and ch != "}"})
    # Remove token text from the missing-character set.
    required_missing = sorted({ch for entry in selected for ch in TOKEN_RE.sub("", entry["translation_zh_cn"]) if ch not in mapping})
    tentative = {}
    if planned_allocation is None:
        used_codes = set(usage.get("canonical_codes", []))
        available_codes = [
            bytes((high, low))
            for high in range(0x20, 0x24)
            for low in range(256)
            if f"{high:02X}{low:02X}" not in used_codes
        ] + [
            bytes((0x18, low)) for low in range(0x10, 0x100) if f"18{low:02X}" not in used_codes
        ]
        for character, code in zip(required_missing, available_codes):
            mapping[character] = code
            tentative[character] = code.hex().upper()
    else:
        available_codes = []

    entry_results = []
    pool_lengths: dict[str, int] = defaultdict(int)
    overflow = []
    line_overflow = []
    missing_counter: Counter[str] = Counter()
    token_errors = []
    for entry in selected:
        table = entry.get("metadata", {}).get("table", "")
        battle = table.startswith("battle_")
        record_size = entry.get("metadata", {}).get("record_size")
        compact_indexed = entry.get("kind") == "indexed_text" and not table.startswith("battle_")
        entry_mapping = fixed_mapping if planned_allocation is not None and (record_size is not None or compact_indexed) else mapping
        encoded, missing, errors = encode(entry["translation_zh_cn"], entry_mapping, battle=battle)
        missing_counter.update(missing)
        token_errors.extend({"text_id": entry["text_id"], "error": error} for error in errors)
        if record_size is not None and len(encoded) > int(record_size):
            overflow.append({"text_id": entry["text_id"], "encoded_length": len(encoded), "capacity": int(record_size)})
        if entry["kind"] == "indexed_text":
            pool_lengths[table] += len(encoded)
        if table == "battle_event_messages_3d9a00":
            lengths = visible_line_lengths(entry["translation_zh_cn"])
            if lengths and max(lengths) > 10:
                line_overflow.append({"text_id": entry["text_id"], "line_lengths": lengths})
        entry_results.append({"text_id": entry["text_id"], "encoded_length": len(encoded)})

    pool_report = {
        table: {
            "translated_bytes_only": length,
            "full_pool_capacity": POOL_CAPACITY.get(table),
            "note": "Partial until every entry in this pool is translated.",
        }
        for table, length in sorted(pool_lengths.items())
    }
    report = {
        "project": "bokuno_cn",
        "phase": "encoding_dry_run",
        "rom_write_performed": False,
        "included_translation_statuses": sorted(statuses),
        "allocation_plan": str(args.allocation.resolve()) if args.allocation is not None else None,
        "selected_entries": len(selected),
        "tentative_new_glyph_count": len(tentative),
        "tentative_new_glyph_codes": tentative,
        "available_unused_source_codes": len(available_codes),
        "unallocated_characters": required_missing[len(available_codes):],
        "fixed_record_overflow_count": len(overflow),
        "fixed_record_overflows": overflow,
        "battle_line_overflow_count": len(line_overflow),
        "battle_line_overflows": line_overflow,
        "unsupported_token_count": len(token_errors),
        "unsupported_tokens": token_errors,
        "missing_after_tentative_allocation": dict(missing_counter),
        "indexed_pool_partial_lengths": pool_report,
        "entries": entry_results,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("selected_entries", "tentative_new_glyph_count", "available_unused_source_codes", "fixed_record_overflow_count", "battle_line_overflow_count", "unsupported_token_count")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
