#!/usr/bin/env python3
"""
Populate the XP field on each character sheet with the minimum BECMI XP
required to reach that character's level.

XP tables from the BECMI Rules Cyclopedia.
"""
import os

CHARS_DIR = "characters"

# Minimum XP to reach level N (index = level, 1-based)
XP_TABLE = {
    "fighter":  [0, 0, 2_000, 4_000, 8_000, 16_000, 32_000, 64_000, 120_000, 240_000, 360_000],
    "cleric":   [0, 0, 1_500, 3_000, 6_000, 12_000, 25_000, 50_000, 100_000, 200_000, 300_000],
    "mage":     [0, 0, 2_500, 5_000, 10_000, 20_000, 40_000, 75_000, 150_000, 300_000, 450_000],
    "thief":    [0, 0, 1_200, 2_400, 4_800,  9_600, 20_000, 40_000,  80_000, 160_000, 280_000],
    "dwarf":    [0, 0, 2_200, 4_400, 8_800, 17_000, 35_000, 70_000, 140_000, 270_000, 400_000],
    "elf":      [0, 0, 4_000, 8_000, 16_000, 32_000, 64_000, 130_000, 260_000, 500_000, 900_000],
    "halfling": [0, 0, 2_000, 4_000, 8_000,  16_000, 32_000, 65_000, 120_000],  # max L8
}

CHAR_INFO = {
    "strongheart": ("fighter",  8),
    "elkhorn":     ("dwarf",    6),
    "mercion":     ("cleric",   7),
    "ringlerun":   ("mage",    10),
    "peralay":     ("elf",     10),
    "figgen":      ("halfling", 5),
    "molliver":    ("thief",    8),
    "hawkler":     ("fighter",  6),
    "deeth":       ("fighter",  6),
    "bowmarc":     ("fighter",  6),
    "valkeer":     ("fighter",  6),
    "grimsword":   ("fighter",  6),
    "zargash":     ("cleric",   7),
    "kelek":       ("mage",     7),
    "warduke":     ("fighter",  9),
    "skylla":      ("mage",     6),
    "zorgar":      ("fighter",  6),
    "drex":        ("fighter",  6),
    "zarak":       ("thief",    5),
}

OLD = 'class="xp-input" placeholder="0 XP"'

updated = 0
for name, (cls, level) in CHAR_INFO.items():
    xp = XP_TABLE[cls][level]
    path = os.path.join(CHARS_DIR, f"{name}.html")
    html = open(path, encoding="utf-8").read()
    new = f'class="xp-input" placeholder="0 XP" value="{xp:,}"'
    if OLD in html:
        html = html.replace(OLD, new, 1)
        open(path, "w", encoding="utf-8").write(html)
        updated += 1
        print(f"  {name:12s}  {cls:8s} L{level:2d}  →  {xp:>10,} XP")
    else:
        print(f"  SKIP {name} (XP already set or field not found)")

print(f"\nUpdated {updated} / {len(CHAR_INFO)} sheets")
