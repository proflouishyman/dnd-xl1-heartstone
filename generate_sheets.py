#!/usr/bin/env python3
"""
Generate individual HTML character sheets for XL-1 Quest for the Heartstone.
Each file is self-contained (base64 portrait) and opens in any browser.
Upload to Google Drive → open with Google Docs, or share directly via Discord.
"""

import os, io, base64
from PIL import Image

CHARS_DIR = "extracted/characters"
OUT_DIR   = "extracted/character_sheets"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Source page filenames (1-indexed) ────────────────────────────────────────
PAGES = {
    1: "characters_lawful_1_strongheart_elkhorn_ringlerun_mercion_peralay_figgen.jpg",
    2: "characters_lawful_2_molliver_hawkler_deeth_bowmarc_valkeer.jpg",
    3: "characters_chaotic_1_grimsword_zargash_kelek_warduke.jpg",
    4: "characters_chaotic_2_skylla_zorgar_drex_zarak.jpg",
}

# ── Character data ────────────────────────────────────────────────────────────
# crop = (left, top, right, bottom) in actual pixels on the source page image
CHARACTERS = [
    # ── PAGE 1 ────────────────────────────────────────────────────────────────
    {
        "name": "STRONGHEART",
        "epithet": "Good Paladin",
        "alignment": "Lawful",
        "class_level": "10th Level Lord (Fighter)",
        "race": "Human",
        "page": 1,
        "crop": (50, 25, 1060, 1200),
        "stats": {"STR":13,"DEX":12,"INT":12,"CON":11,"WIS":13,"CHA":17},
        "ac": 2, "hp_max": 68, "mv": 60, "attacks": 1,
        "save_as": "Fighter 10",
        "weapons": [
            "Dagger",
            "Sword +2 — intelligent, lawful; Intelligence 8; detects evil; heals 6 HP/day",
        ],
        "armor": "Plate mail; Shield; Helmet",
        "special": [],
        "languages": ["Common", "Lawful"],
        "spells": {},
    },
    {
        "name": "ELKHORN",
        "epithet": "Good Dwarf Fighter",
        "alignment": "Lawful",
        "class_level": "Dwarven Champion (7th Level Fighter)",
        "race": "Dwarf",
        "page": 1,
        "crop": (1530, 90, 2552, 900),
        "stats": {"STR":9,"DEX":13,"INT":9,"CON":16,"WIS":10,"CHA":11},
        "ac": 2, "hp_max": 67, "mv": 60, "attacks": 1,
        "save_as": "Fighter 7",
        "weapons": ["Sword +1", "Hand axe", "Dagger"],
        "armor": "Plate mail; Shield; Helmet",
        "special": ["Dwarf racial bonuses vs. giants/kobolds; +4 saves vs. magic/poison"],
        "languages": ["Common", "Dwarvish", "Gnomish", "Goblin", "Kobold"],
        "spells": {},
    },
    {
        "name": "MERCION",
        "epithet": "Good Cleric Female",
        "alignment": "Lawful",
        "class_level": "Elder (7th Level Cleric)",
        "race": "Human",
        "page": 1,
        "crop": (0, 1020, 430, 2100),
        "stats": {"STR":10,"DEX":9,"INT":12,"CON":9,"WIS":17,"CHA":14},
        "ac": 2, "hp_max": 35, "mv": 60, "attacks": 1,
        "save_as": "Cleric 7",
        "weapons": ["Mace +1"],
        "armor": "Plate mail; Shield",
        "special": [],
        "languages": ["Common", "Lawful"],
        "spells": {
            1: ["Cure Light Wounds ×2", "Detect Evil", "Light", "Protection from Evil"],
            2: ["Bless", "Find Traps", "Hold Person", "Silence 15' Radius"],
            3: ["Cure Disease", "Remove Curse", "Striking"],
            4: ["Cure Serious Wounds", "Neutralize Poison"],
        },
    },
    {
        "name": "RINGLERUN",
        "epithet": "Good Wizard",
        "alignment": "Lawful",
        "class_level": "Sorcerer (7th Level Magic-User)",
        "race": "Human",
        "page": 1,
        "crop": (1500, 760, 2552, 1860),
        "stats": {"STR":9,"DEX":10,"INT":14,"CON":9,"WIS":13,"CHA":11},
        "ac": 9, "hp_max": 23, "mv": 120, "attacks": 1,
        "save_as": "Magic-User 7",
        "weapons": ["Dagger +1", "Staff of Power (21 charges)"],
        "armor": "Ring of Protection +1",
        "special": ["Additional Language: Hobgoblin"],
        "languages": ["Common", "Lawful", "Hobgoblin"],
        "spells": {
            1: ["Charm Person", "Detect Magic", "Magic Missile", "Read Magic", "Sleep"],
            2: ["ESP", "Knock", "Levitate", "Web"],
            3: ["Dispel Magic", "Fireball", "Haste"],
            4: ["Ice Storm / Wall of Ice"],
        },
    },
    {
        "name": "PERALAY",
        "epithet": "Fighter Mage Elf",
        "alignment": "Lawful",
        "class_level": "10th Level Lord Wizard (Elf)",
        "race": "Elf",
        "page": 1,
        "crop": (0, 1800, 810, 3303),
        "stats": {"STR":14,"DEX":14,"INT":15,"CON":17,"WIS":10,"CHA":14},
        "ac": 1, "hp_max": 72, "mv": 120, "attacks": 1,
        "save_as": "Elf 10",
        "weapons": ["Sword +2", "Dagger", "Longbow and 15 arrows"],
        "armor": "Chain mail +3; Shield",
        "special": [
            "Elf racial: detect secret doors, immune to ghoul paralysis",
            "Additional Language: Ogre",
        ],
        "languages": ["Common", "Lawful", "Elvish", "Gnoll", "Hobgoblin", "Ogre", "Orcish"],
        "spells": {
            1: ["Charm Person", "Light", "Magic Missile", "Read Languages", "Read Magic", "Shield"],
            2: ["Detect Invisible", "Invisibility", "Mirror Image", "Web", "Wizard Lock"],
            3: ["Dispel Magic", "Fireball", "Hold Person", "Lightning Bolt", "Water Breathing"],
            4: ["Charm Monster", "Confusion"],
            5: ["Cloudkill"],
        },
    },
    {
        "name": "FIGGEN",
        "epithet": "Good Halfling",
        "alignment": "Lawful",
        "class_level": "Sheriff (8th Level Halfling)",
        "race": "Halfling",
        "page": 1,
        "crop": (1370, 1800, 2552, 2700),
        "stats": {"STR":13,"DEX":13,"INT":10,"CON":12,"WIS":9,"CHA":10},
        "ac": 2, "hp_max": 45, "mv": 90, "attacks": 1,
        "save_as": "Fighter 8",
        "weapons": ["Dagger +2", "Short sword", "Sling and 20 stones"],
        "armor": "Plate mail; Shield; Helmet; Elvenscloak",
        "special": [
            "Halfling racial: +1 to hit with missiles, +2 initiative, hide in undergrowth",
            "+4 saves vs. magic/dragon breath",
        ],
        "languages": ["Common", "Lawful", "Halfling"],
        "spells": {},
    },

    # ── PAGE 2 ────────────────────────────────────────────────────────────────
    {
        "name": "MOLLIVER",
        "epithet": "Good Thief",
        "alignment": "Lawful",
        "class_level": "8th Level Thief",
        "race": "Human",
        "page": 2,
        "crop": (140, 0, 1340, 860),
        "stats": {"STR":9,"DEX":16,"INT":10,"CON":16,"WIS":9,"CHA":17},
        "ac": 7, "hp_max": 40, "mv": 120, "attacks": 1,
        "save_as": "Thief 8",
        "weapons": ["Sword +2", "Dagger ×2"],
        "armor": "Leather +1; Boots of Levitation",
        "special": [
            "Thief skills: Pick Locks 50%, Find/Remove Traps 40%, Pick Pockets 50%, Move Silently 55%, Climb Walls 93%, Hide in Shadows 37%, Hear Noise 1–3",
            "Backstab: ×3 damage",
            "Boots of Levitation: float up/down 10'/round, duration indefinite",
        ],
        "languages": ["Common", "Lawful"],
        "spells": {},
    },
    {
        "name": "HAWKLER",
        "epithet": "Good Ranger",
        "alignment": "Lawful",
        "class_level": "Myrmidon (6th Level Fighter)",
        "race": "Human",
        "page": 2,
        "crop": (1440, 0, 2552, 940),
        "stats": {"STR":13,"DEX":16,"INT":11,"CON":13,"WIS":10,"CHA":12},
        "ac": 7, "hp_max": 45, "mv": 120, "attacks": 1,
        "save_as": "Fighter 6",
        "weapons": ["Long bow", "12 arrows +1", "Sword +1", "Dagger"],
        "armor": "Leather",
        "special": [],
        "languages": ["Common", "Lawful"],
        "spells": {},
    },
    {
        "name": "DEETH",
        "epithet": "Good Fighter",
        "alignment": "Lawful",
        "class_level": "Superhero (8th Level Fighter)",
        "race": "Human",
        "page": 2,
        "crop": (35, 740, 1040, 1880),
        "stats": {"STR":12,"DEX":13,"INT":11,"CON":16,"WIS":13,"CHA":14},
        "ac": 2, "hp_max": 58, "mv": 60, "attacks": 1,
        "save_as": "Fighter 8",
        "weapons": ["Flail +2 (1d8+2 damage)", "Sword +2"],
        "armor": "Plate mail; Shield; Helmet; Scarab of Protection",
        "special": [
            "Scarab of Protection: grants 2 additional saves vs. death magic; absorbs up to 12 levels of energy drain",
        ],
        "languages": ["Common", "Lawful"],
        "spells": {},
    },
    {
        "name": "BOWMARC",
        "epithet": "Good Crusader",
        "alignment": "Lawful",
        "class_level": "Champion (7th Level Fighter)",
        "race": "Human",
        "page": 2,
        "crop": (35, 1730, 1100, 2960),
        "stats": {"STR":11,"DEX":12,"INT":9,"CON":13,"WIS":10,"CHA":12},
        "ac": 2, "hp_max": 45, "mv": 60, "attacks": 1,
        "save_as": "Fighter 7",
        "weapons": ["Battle axe +1", "Sword +1"],
        "armor": "Plate mail; Shield; Helmet; Gauntlets of Ogre Power",
        "special": [
            "Gauntlets of Ogre Power: treat STR as 18 for attack/damage rolls",
        ],
        "languages": ["Common", "Lawful"],
        "spells": {},
    },
    {
        "name": "VALKEER",
        "epithet": "Good Norseman",
        "alignment": "Lawful",
        "class_level": "Swashbuckler (5th Level Fighter)",
        "race": "Human",
        "page": 2,
        "crop": (1310, 1730, 2552, 2960),
        "stats": {"STR":16,"DEX":16,"INT":12,"CON":12,"WIS":11,"CHA":12},
        "ac": 6, "hp_max": 39, "mv": 120, "attacks": 1,
        "save_as": "Fighter 5",
        "weapons": ["Sword +1", "War hammer", "Hand axe"],
        "armor": "Leather; Shield; Helmet",
        "special": [],
        "languages": ["Common", "Lawful"],
        "spells": {},
    },

    # ── PAGE 3 ────────────────────────────────────────────────────────────────
    {
        "name": "GRIMSWORD",
        "epithet": "Evil Knight",
        "alignment": "Chaotic",
        "class_level": "Champion (7th Level Fighter)",
        "race": "Human",
        "page": 3,
        "crop": (0, 40, 1040, 1750),
        "stats": {"STR":15,"DEX":13,"INT":10,"CON":12,"WIS":9,"CHA":7},
        "ac": 2, "hp_max": 52, "mv": 60, "attacks": 1,
        "save_as": "Fighter 7",
        "weapons": ["Sword +1 (energy drain — victim loses 1 level on hit, no save)", "Flail"],
        "armor": "Plate mail; Chain mail; Shield; Helmet",
        "special": [],
        "languages": ["Common", "Chaotic"],
        "spells": {},
    },
    {
        "name": "ZARGASH",
        "epithet": "Evil Cleric",
        "alignment": "Chaotic",
        "class_level": "Bishop (7th Level Cleric)",
        "race": "Human",
        "page": 3,
        "crop": (1160, 40, 2552, 1360),
        "stats": {"STR":8,"DEX":10,"INT":10,"CON":10,"WIS":15,"CHA":16},
        "ac": 2, "hp_max": 38, "mv": 60, "attacks": 1,
        "save_as": "Cleric 7",
        "weapons": ["Mace +1", "War hammer", "Snake staff"],
        "armor": "Plate mail; Shield; Helmet",
        "special": [
            "Snake staff: acts as quarterstaff +1; once per day can be thrown to become a real snake (HD 3, AC 6, damage 1d4 + poison) for 1 turn",
        ],
        "languages": ["Common", "Chaotic"],
        "spells": {
            1: ["Cause Light Wounds ×2", "Darkness", "Protection from Good"],
            2: ["Blight", "Hold Person ×2", "Silence 15' Radius"],
            3: ["Animate Dead", "Cause Disease", "Curse"],
            4: ["Cause Serious Wounds", "Speak with Dead"],
        },
    },
    {
        "name": "KELEK",
        "epithet": "Evil Sorcerer",
        "alignment": "Chaotic",
        "class_level": "Chaotic Sorcerer (7th Level Magic-User)",
        "race": "Human",
        "page": 3,
        "crop": (0, 1320, 1360, 3000),
        "stats": {"STR":15,"DEX":10,"INT":15,"CON":14,"WIS":13,"CHA":7},
        "ac": 9, "hp_max": 33, "mv": 120, "attacks": 1,
        "save_as": "Magic-User 7",
        "weapons": [
            "Dagger +1",
            "Wand of Cold (5 charges — 6d6 cold damage, 60' range, save for half)",
            "Staff of Striking (12 charges — +2 to hit, 2d6+2 damage per charge)",
        ],
        "armor": "Ring of Protection +1",
        "special": ["Additional Language: Orc"],
        "languages": ["Common", "Chaotic", "Orc"],
        "spells": {
            1: ["Charm Person", "Magic Missile", "Read Magic", "Shield", "Sleep"],
            2: ["ESP", "Knock", "Mirror Image", "Web"],
            3: ["Fireball", "Fly", "Haste"],
            4: ["Charm Monsters"],
        },
    },
    {
        "name": "WARDUKE",
        "epithet": "Evil Fighter",
        "alignment": "Chaotic",
        "class_level": "Superhero (8th Level Fighter)",
        "race": "Human",
        "page": 3,
        "crop": (1160, 1520, 2552, 3050),
        "stats": {"STR":16,"DEX":11,"INT":9,"CON":14,"WIS":11,"CHA":11},
        "ac": 2, "hp_max": 59, "mv": 60, "attacks": 1,
        "save_as": "Fighter 8",
        "weapons": [
            "Sword +1 (flames on command — deals extra 1d6 fire damage when ignited)",
            "Battle axe",
            "Dagger",
        ],
        "armor": "Plate mail; Magical helmet (infravision 60 ft; wearer's eyes glow red)",
        "special": [
            "Magical Helmet: grants infravision 60 ft; cosmetic: eyes glow red in darkness",
        ],
        "languages": ["Common", "Chaotic"],
        "spells": {},
    },

    # ── PAGE 4 ────────────────────────────────────────────────────────────────
    {
        "name": "SKYLLA",
        "epithet": "Evil Magic-User",
        "alignment": "Chaotic",
        "class_level": "Chaotic Warlock (6th Level Magic-User)",
        "race": "Human",
        "page": 4,
        "crop": (0, 0, 1020, 1630),
        "stats": {"STR":9,"DEX":11,"INT":12,"CON":10,"WIS":15,"CHA":11},
        "ac": 9, "hp_max": 22, "mv": 120, "attacks": 1,
        "save_as": "Magic-User 6",
        "weapons": [
            "Dagger +1",
            "Staff of Commanding (10 charges — command any single creature, WIS save negates)",
        ],
        "armor": "Ring of Protection +1",
        "special": [],
        "languages": ["Common", "Chaotic"],
        "spells": {
            1: ["Charm Person", "Floating Disc", "Light", "Magic Missile", "Read Magic"],
            2: ["Detect Invisible", "Knock", "Levitate", "Wizard Lock"],
            3: ["Hold Person", "Lightning Bolt"],
        },
    },
    {
        "name": "ZORGAR",
        "epithet": "Evil Barbarian",
        "alignment": "Chaotic",
        "class_level": "Swashbuckler (5th Level Fighter)",
        "race": "Human",
        "page": 4,
        "crop": (950, 0, 2565, 1470),
        "stats": {"STR":18,"DEX":13,"INT":10,"CON":16,"WIS":9,"CHA":12},
        "ac": 5, "hp_max": 37, "mv": 120, "attacks": 1,
        "save_as": "Fighter 5",
        "weapons": ["Dagger +1", "Club"],
        "armor": "Chain mail",
        "special": [],
        "languages": ["Common", "Chaotic"],
        "spells": {},
    },
    {
        "name": "DREX",
        "epithet": "Evil Warrior",
        "alignment": "Chaotic",
        "class_level": "Myrmidon (6th Level Fighter)",
        "race": "Human",
        "page": 4,
        "crop": (500, 1450, 1450, 3000),
        "stats": {"STR":15,"DEX":14,"INT":9,"CON":11,"WIS":10,"CHA":10},
        "ac": 6, "hp_max": 39, "mv": 120, "attacks": 1,
        "save_as": "Fighter 6",
        "weapons": ["Sword +1", "Dagger"],
        "armor": "Leather +1; Shield; Helmet",
        "special": [],
        "languages": ["Common", "Chaotic"],
        "spells": {},
    },
    {
        "name": "ZARAK",
        "epithet": "Evil Half-Orc Assassin",
        "alignment": "Chaotic",
        "class_level": "Chaotic Cutpurse (5th Level Thief)",
        "race": "Half-Orc",
        "page": 4,
        "crop": (1340, 1450, 2565, 3050),
        "stats": {"STR":13,"DEX":12,"INT":11,"CON":16,"WIS":15,"CHA":6},
        "ac": 7, "hp_max": 27, "mv": 120, "attacks": 1,
        "save_as": "Thief 5",
        "weapons": [
            "Throwing dagger +1 (returns like a boomerang after each throw)",
        ],
        "armor": "Leather; Potion of Invisibility",
        "special": [
            "Thief skills: Pick Locks 35%, Find/Remove Traps 25%, Pick Pockets 35%, Move Silently 40%, Climb Walls 91%, Hide in Shadows 28%, Hear Noise 1–3",
            "Backstab: ×2 damage",
            "Potion of Invisibility: one use, lasts until attacking or casting",
        ],
        "languages": ["Common", "Chaotic", "Orcish"],
        "spells": {},
    },
]

# ── Stat modifier (BECMI) ─────────────────────────────────────────────────────
def modifier(score):
    if score <= 3:  return -3
    if score <= 5:  return -2
    if score <= 8:  return -1
    if score <= 12: return  0
    if score <= 15: return +1
    if score <= 17: return +2
    return +3

def fmt_mod(score):
    m = modifier(score)
    return f"+{m}" if m >= 0 else str(m)

# ── Crop and base64-encode portrait ──────────────────────────────────────────
def portrait_b64(char):
    path = os.path.join(CHARS_DIR, PAGES[char["page"]])
    img  = Image.open(path)
    l, t, r, b = char["crop"]
    # clamp to image bounds
    W, H = img.size
    crop = img.crop((max(0,l), max(0,t), min(W,r), min(H,b)))
    buf  = io.BytesIO()
    crop.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()

# ── HTML generator ────────────────────────────────────────────────────────────
ALIGNMENT_COLOR = {"Lawful": "#2c4a7c", "Chaotic": "#7c2c2c", "Neutral": "#4a5c2c"}

def spell_html(spells):
    if not spells:
        return ""
    rows = ""
    for lvl in sorted(spells):
        names = "; ".join(spells[lvl])
        rows += f"""
        <tr>
          <td class="spell-lvl">Level {lvl}</td>
          <td>{names}</td>
        </tr>"""
    return f"""
    <section class="spells">
      <h3>Spellbook</h3>
      <table class="spell-table">
        <thead><tr><th>Level</th><th>Known Spells</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <h4>Daily Memorized Spells</h4>
      <div class="memo-grid">{"".join(
          f'<div class="memo-slot"><span class="memo-lvl">Lvl {lvl}</span>'
          + "".join(
              f'<input type="text" class="memo-input" placeholder="spell…">'
              for _ in spells[lvl]
          )
          + "</div>"
          for lvl in sorted(spells)
      )}</div>
    </section>"""

def make_html(char):
    portrait = portrait_b64(char)
    acolor   = ALIGNMENT_COLOR.get(char["alignment"], "#555")
    stats    = char["stats"]
    spells   = char.get("spells", {})
    is_caster = bool(spells)

    weapon_items = "".join(f"<li>{w}</li>" for w in char["weapons"])
    special_items = "".join(f"<li>{s}</li>" for s in char.get("special", []))
    lang_str = ", ".join(char.get("languages", []))

    inventory_rows = "".join(
        f"""<tr>
          <td class="inv-num">{i}</td>
          <td><input type="text" class="inv-item" placeholder="item name…"></td>
          <td><input type="number" class="inv-qty" placeholder="1" min="0"></td>
          <td><input type="text" class="inv-notes" placeholder="notes…"></td>
        </tr>"""
        for i in range(1, 21)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{char["name"]} — XL-1 Quest for the Heartstone</title>
<style>
  :root {{
    --bg:       #f5f0e6;
    --paper:    #faf7f0;
    --border:   #8b6914;
    --accent:   {acolor};
    --text:     #2a1f0a;
    --faint:    #b8a878;
    --input-bg: #fff8e8;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Georgia', serif;
    font-size: 13px;
    padding: 16px;
    max-width: 960px;
    margin: 0 auto;
  }}

  /* ── Header ── */
  .sheet-header {{
    display: grid;
    grid-template-columns: 220px 1fr;
    gap: 16px;
    border: 3px double var(--border);
    background: var(--paper);
    padding: 12px;
    margin-bottom: 12px;
  }}
  .portrait {{ width: 100%; border: 2px solid var(--faint); }}
  .header-info {{ display: flex; flex-direction: column; justify-content: space-between; }}
  .char-name {{
    font-size: 28px;
    font-weight: bold;
    color: var(--accent);
    letter-spacing: 2px;
    text-transform: uppercase;
  }}
  .char-epithet {{ font-size: 14px; font-style: italic; color: #666; margin-top: 2px; }}
  .char-meta {{ margin-top: 6px; }}
  .char-meta span {{ display: inline-block; margin-right: 16px; font-size: 12px; }}
  .badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: bold;
    color: white;
    background: var(--accent);
    letter-spacing: 1px;
    text-transform: uppercase;
  }}

  /* ── HP bar ── */
  .hp-bar {{
    margin-top: 10px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 10px;
    background: #fff3e0;
    border: 1px solid var(--border);
    border-radius: 4px;
  }}
  .hp-label {{ font-weight: bold; font-size: 13px; }}
  .hp-current {{
    width: 64px; text-align: center;
    font-size: 22px; font-weight: bold; color: #a00;
    border: 2px solid #a00; border-radius: 4px;
    padding: 2px; background: #fff;
  }}
  .hp-max {{ font-size: 13px; color: #555; }}
  .xp-block {{ margin-left: auto; text-align: right; }}
  .xp-input {{
    width: 90px; text-align: center; font-size: 13px;
    border: 1px solid var(--faint); border-radius: 4px; padding: 3px;
    background: var(--input-bg);
  }}

  /* ── Two-column stats ── */
  .stats-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }}
  section {{
    background: var(--paper);
    border: 2px solid var(--border);
    padding: 10px 12px;
  }}
  h3 {{
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--accent);
    border-bottom: 1px solid var(--faint);
    padding-bottom: 4px;
    margin-bottom: 8px;
  }}
  h4 {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #666;
    margin: 10px 0 5px;
  }}

  /* ── Ability scores ── */
  .ability-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }}
  .ability {{
    text-align: center;
    padding: 6px 4px;
    border: 1px solid var(--faint);
    border-radius: 4px;
    background: var(--input-bg);
  }}
  .ability-name {{ font-size: 10px; text-transform: uppercase; color: #888; }}
  .ability-score {{ font-size: 22px; font-weight: bold; line-height: 1.2; }}
  .ability-mod {{ font-size: 11px; color: #555; }}

  /* ── Combat stats ── */
  .combat-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }}
  .combat-stat {{
    padding: 5px 8px;
    border: 1px solid var(--faint);
    border-radius: 4px;
    background: var(--input-bg);
  }}
  .combat-label {{ font-size: 10px; text-transform: uppercase; color: #888; }}
  .combat-value {{ font-size: 17px; font-weight: bold; }}

  /* ── Equipment ── */
  .equip-list {{ list-style: none; padding: 0; }}
  .equip-list li {{
    padding: 3px 0 3px 12px;
    border-bottom: 1px dotted var(--faint);
    position: relative;
    font-size: 12px;
  }}
  .equip-list li::before {{ content: '⚔'; position: absolute; left: 0; font-size: 10px; top: 4px; }}

  /* ── Spells ── */
  .spell-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  .spell-table th, .spell-table td {{ padding: 3px 6px; border: 1px solid var(--faint); }}
  .spell-table th {{ background: var(--accent); color: white; text-align: left; }}
  .spell-lvl {{ font-weight: bold; white-space: nowrap; }}
  .memo-grid {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }}
  .memo-slot {{ border: 1px solid var(--faint); border-radius: 4px; padding: 5px 8px; background: var(--input-bg); }}
  .memo-lvl {{ font-size: 10px; text-transform: uppercase; color: #888; display: block; margin-bottom: 3px; }}
  .memo-input {{
    display: block; width: 160px; font-size: 11px;
    border: 1px solid #ddd; border-radius: 3px;
    padding: 2px 4px; background: white; margin-top: 2px;
  }}

  /* ── Inventory ── */
  .inv-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .inv-table th {{ background: var(--accent); color: white; padding: 5px 6px; text-align: left; }}
  .inv-table td {{ border: 1px solid var(--faint); padding: 2px 4px; }}
  .inv-num {{ text-align: center; width: 28px; color: #aaa; font-size: 11px; }}
  .inv-item  {{ width: 100%; font-size: 12px; border: none; background: var(--input-bg); padding: 3px; }}
  .inv-qty   {{ width: 50px; text-align: center; font-size: 12px; border: none; background: var(--input-bg); padding: 3px; }}
  .inv-notes {{ width: 100%; font-size: 11px; border: none; background: var(--input-bg); padding: 3px; color: #555; }}
  input[type="text"], input[type="number"] {{ font-family: inherit; }}

  /* ── Treasure ── */
  .treasure-grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
  }}
  .coin {{ text-align: center; }}
  .coin-label {{ font-size: 10px; text-transform: uppercase; color: #888; }}
  .coin-input {{
    width: 100%; text-align: center; font-size: 16px; font-weight: bold;
    border: 1px solid var(--faint); border-radius: 4px;
    padding: 4px; background: var(--input-bg);
  }}

  /* ── Notes ── */
  .notes-area {{
    width: 100%; min-height: 100px; font-family: Georgia, serif;
    font-size: 12px; border: 1px solid var(--faint); border-radius: 4px;
    padding: 6px; background: var(--input-bg); resize: vertical;
  }}

  @media print {{
    body {{ padding: 0; }}
    input {{ border-color: #ccc !important; }}
  }}
</style>
</head>
<body>

<!-- ── HEADER ── -->
<div class="sheet-header">
  <img class="portrait" src="data:image/jpeg;base64,{portrait}" alt="{char["name"]}">
  <div class="header-info">
    <div>
      <div class="char-name">{char["name"]}</div>
      <div class="char-epithet">{char["epithet"]}</div>
      <div class="char-meta" style="margin-top:8px;">
        <span><b>Race:</b> {char["race"]}</span>
        <span><b>Class:</b> {char["class_level"]}</span>
      </div>
      <div class="char-meta" style="margin-top:4px;">
        <span class="badge">{char["alignment"]}</span>
        <span style="font-size:11px; color:#666; margin-left:8px;">Save As: {char["save_as"]}</span>
      </div>
      <div class="char-meta" style="margin-top:4px;">
        <span><b>Languages:</b> {lang_str}</span>
      </div>
    </div>
    <div class="hp-bar">
      <span class="hp-label">HP</span>
      <input type="number" class="hp-current" id="hp-cur" value="{char["hp_max"]}" min="0" max="{char["hp_max"]}">
      <span class="hp-max">/ {char["hp_max"]} max</span>
      <div class="xp-block">
        <div style="font-size:10px; color:#888; text-transform:uppercase; margin-bottom:2px;">Experience</div>
        <input type="number" class="xp-input" placeholder="0 XP">
      </div>
    </div>
  </div>
</div>

<!-- ── STATS + COMBAT ── -->
<div class="stats-row">
  <section>
    <h3>Ability Scores</h3>
    <div class="ability-grid">
      {"".join(f'''<div class="ability">
        <div class="ability-name">{stat}</div>
        <div class="ability-score">{val}</div>
        <div class="ability-mod">{fmt_mod(val)}</div>
      </div>''' for stat, val in stats.items())}
    </div>
  </section>
  <section>
    <h3>Combat</h3>
    <div class="combat-grid">
      <div class="combat-stat"><div class="combat-label">Armor Class</div><div class="combat-value">{char["ac"]}</div></div>
      <div class="combat-stat"><div class="combat-label">Movement</div><div class="combat-value">{char["mv"]}'</div></div>
      <div class="combat-stat"><div class="combat-label">HP Maximum</div><div class="combat-value">{char["hp_max"]}</div></div>
      <div class="combat-stat"><div class="combat-label">Attacks/Round</div><div class="combat-value">{char["attacks"]}</div></div>
    </div>
    <h4>Weapons</h4>
    <ul class="equip-list">{"".join(f"<li>{w}</li>" for w in char["weapons"])}</ul>
    <h4 style="margin-top:8px;">Armor &amp; Protection</h4>
    <p style="font-size:12px; padding:3px 0;">{char["armor"]}</p>
    {"<h4 style='margin-top:8px;'>Special Abilities</h4><ul class='equip-list'>" + special_items + "</ul>" if char.get("special") else ""}
  </section>
</div>

<!-- ── SPELLS (if caster) ── -->
{spell_html(spells)}

<!-- ── INVENTORY ── -->
<section style="margin-bottom:12px;">
  <h3>Inventory</h3>
  <table class="inv-table">
    <thead>
      <tr>
        <th style="width:28px;">#</th>
        <th>Item</th>
        <th style="width:60px;">Qty</th>
        <th style="width:240px;">Notes</th>
      </tr>
    </thead>
    <tbody>{inventory_rows}</tbody>
  </table>
</section>

<!-- ── TREASURE ── -->
<section style="margin-bottom:12px;">
  <h3>Treasure</h3>
  <div class="treasure-grid">
    {"".join(f'<div class="coin"><div class="coin-label">{c}</div><input type="number" class="coin-input" value="0" min="0"></div>' for c in ["Platinum (PP)", "Gold (GP)", "Electrum (EP)", "Silver (SP)", "Copper (CP)"])}
  </div>
</section>

<!-- ── NOTES ── -->
<section>
  <h3>Notes &amp; Journal</h3>
  <textarea class="notes-area" placeholder="Session notes, quest hooks, NPC relationships…"></textarea>
</section>

</body>
</html>"""

# ── Main ─────────────────────────────────────────────────────────────────────
for char in CHARACTERS:
    name = char["name"].lower()
    print(f"  Generating {char['name']}…", end="", flush=True)
    html = make_html(char)
    out  = os.path.join(OUT_DIR, f"{name}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    size = os.path.getsize(out) // 1024
    print(f" {size} KB")

print(f"\nDone — {len(CHARACTERS)} sheets in {OUT_DIR}/")
