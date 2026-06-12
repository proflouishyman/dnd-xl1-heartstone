#!/usr/bin/env python3
"""gen_manifest.py — emit api/manifest.json from the canonical character data.

dnd-api needs each character's *base* (pre-rolled) values to render the homepage
roster, resolve a renamed character back to its immutable id, and — for the
clanker Discord bot — serve a full sheet (GET /characters/{id}/full) so the bot
can roll with the right modifiers and apply damage/inventory without re-deriving
any BECMI tables.

We pull from the single sources of truth already in the repo:
  - generate_sheets.CHARACTERS        stats, ac, hp_max, mv, attacks, weapons, …
  - inject_combat_tables.COMBAT_TABLES thac0, the five saving throws, to-hit
  - inject_class_tables.{CHAR_INFO, THIEF_SKILLS, SPELL_SLOTS}  class/level, skills

All three import side-effect-free (their work is under a __main__ guard), so the
manifest never drifts from the sheets. Run after editing any of them; commit the
resulting api/manifest.json (it is baked into the api image).
"""
import json
import os

from generate_sheets import CHARACTERS
from inject_acquired import ARMOR_ROWS, LEARN_ROWS, MAGIC_ROWS, WEAPON_ROWS
from inject_combat_tables import COMBAT_TABLES
from inject_class_tables import CHAR_INFO, SPELL_SLOTS, THIEF_SKILLS
from set_xp import char_xp

OUT = os.path.join("api", "manifest.json")

INV_ROWS = 20  # generate_sheets renders inv rows 1..20 (range(1, 21))


def main():
    manifest = {}
    for c in CHARACTERS:
        slug = c["name"].lower()
        combat = COMBAT_TABLES.get(slug, {})
        info = CHAR_INFO.get(slug, {})
        thief = THIEF_SKILLS.get(slug, {})
        slots = SPELL_SLOTS.get(slug, {}).get("slots")
        xp_floor, xp_next = char_xp(slug)       # BECMI level floor + next-level threshold
        manifest[slug] = {
            "id": slug,
            "name": c["name"].title(),          # display name; slug/id stays name.lower()
            "epithet": c.get("epithet", ""),
            "class_level": c.get("class_level", ""),
            "race": c.get("race", ""),
            "alignment": c.get("alignment", ""),
            "save_as": c.get("save_as", ""),
            "languages": ", ".join(c.get("languages", [])),
            # mechanical class/level (drives sweep / backstab / turn-undead)
            "class": info.get("cls"),
            "level": info.get("level"),
            "sweep": info.get("sweep", 0),
            # XP: the level's floor (so clanker awards accumulate from the real value,
            # not 0) + the next-level threshold (for the web progress bar)
            "xp": xp_floor,
            "xp_next": xp_next,
            # base ability scores + combat values
            "stats": c.get("stats", {}),
            "ac": c.get("ac"),
            "hp_max": c.get("hp_max"),
            "mv": c.get("mv"),
            "attacks": c.get("attacks", 1),
            # pre-computed combat tables (already include class/race adjustments)
            "thac0": combat.get("thac0"),
            "saves": combat.get("saves", {}),
            "to_hit": combat.get("to_hit", {}),
            "save_note": combat.get("save_note", ""),
            # equipment + magic
            "weapons": c.get("weapons", []),
            "armor": c.get("armor", ""),
            "special": c.get("special", []),
            "spells": c.get("spells", {}),
            "spell_slots": slots,
            # thief
            "thief_skills": thief.get("skills"),
            "backstab": thief.get("backstab"),
            # sheet structure constants the bot needs to address fields
            "inv_rows": INV_ROWS,
            "memo_slots": sum(slots) if slots else 0,
            # additive "acquired" override rows (inject_acquired.py): learned spells
            # (casters only), magic items, and extra weapons/armor
            "learn_rows": LEARN_ROWS if slots else 0,
            "magic_rows": MAGIC_ROWS,
            "weapon_rows": WEAPON_ROWS,
            "armor_rows": ARMOR_ROWS,
        }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT} — {len(manifest)} characters")


if __name__ == "__main__":
    main()
