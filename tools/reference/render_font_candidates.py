#!/usr/bin/env python3
"""Render candidate interpretations of the uncompressed 1bpp font data."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from scan_rom_inventory import DEFAULT_ROM


def pixels_8x16(raw: bytes) -> list[list[int]]:
    return [[(raw[y] >> (7 - x)) & 1 for x in range(8)] for y in range(16)]


def pixels_16x8_rows(raw: bytes) -> list[list[int]]:
    return [[(raw[y * 2 + x // 8] >> (7 - (x % 8))) & 1 for x in range(16)] for y in range(8)]


def pixels_16x8_tiles(raw: bytes) -> list[list[int]]:
    return [[(raw[(x // 8) * 8 + y] >> (7 - (x % 8))) & 1 for x in range(16)] for y in range(8)]


def pixels_snes_2bpp(raw: bytes) -> list[list[int]]:
    return [
        [
            ((raw[y * 2] >> (7 - x)) & 1) | (((raw[y * 2 + 1] >> (7 - x)) & 1) << 1)
            for x in range(8)
        ]
        for y in range(8)
    ]


def pixels_16x16_1bpp_tiles(raw: bytes) -> list[list[int]]:
    return [
        [
            (raw[((y // 8) * 2 + (x // 8)) * 8 + (y % 8)] >> (7 - (x % 8))) & 1
            for x in range(16)
        ]
        for y in range(16)
    ]


def pixels_16x16_1bpp_rows(raw: bytes) -> list[list[int]]:
    return [[(raw[y * 2 + x // 8] >> (7 - (x % 8))) & 1 for x in range(16)] for y in range(16)]


def render(data: bytes, base: int, count: int, scale: int) -> Image.Image:
    layouts = [
        ("16x16 1bpp tile quadrants", pixels_16x16_1bpp_tiles, 16, 16),
        ("16x16 1bpp row pairs", pixels_16x16_1bpp_rows, 16, 16),
    ]
    columns = 16
    panel_width = columns * 20 * scale
    rows = (count + columns - 1) // columns
    panel_height = 24 + rows * 24 * scale
    image = Image.new("RGB", (panel_width, panel_height * len(layouts)), "#20242b")
    draw = ImageDraw.Draw(image)
    for panel, (label, decoder, width, height) in enumerate(layouts):
        top = panel * panel_height
        draw.text((4, top + 4), label, fill="white")
        for index in range(count):
            raw = data[base + index * 32 : base + (index + 1) * 32]
            pixels = decoder(raw)
            cell_x = (index % columns) * 20 * scale
            cell_y = top + 24 + (index // columns) * 24 * scale
            for y in range(height):
                for x in range(width):
                    if pixels[y][x]:
                        draw.rectangle(
                            (cell_x + x * scale, cell_y + y * scale,
                             cell_x + (x + 1) * scale - 1, cell_y + (y + 1) * scale - 1),
                            fill="white",
                        )
            draw.text((cell_x, cell_y + 17 * scale), f"{index:02X}", fill="#73c7ff")
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--base", type=lambda value: int(value, 0), default=0x2C0000)
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = args.rom.resolve().read_bytes()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    render(data, args.base, args.count, args.scale).save(output)
    print(output)


if __name__ == "__main__":
    main()
