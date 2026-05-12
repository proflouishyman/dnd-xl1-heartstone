#!/usr/bin/env python3
"""
Add magic items to all character sheets.
Each entry specifies:
  weapon_replace : (old_text, new_text) or None
  weapon_add     : list of <li> strings to append to weapons ul
  armor_add      : list of item strings to append to armor paragraph
  items          : list of (name, description) for the detailed magic items block
"""
import os, re

CHARS_DIR = "characters"

UPDATES = {
    # ── Level 5 characters (biggest XP gap, most significant items) ─────────
    "zarak": {
        "weapon_replace": (
            "Throwing dagger +1 (returns like a boomerang after each throw)",
            "Bloodwhisper — Intelligent Dagger +2 ✦ (see Magic Items below)",
        ),
        "weapon_add": [],
        "armor_add":   ["Boots of Elvenkind"],
        "items": [
            ("Bloodwhisper — Intelligent Dagger +2",
             "Int 14 · Ego 8 · Chaotic · communicates by whispering in Thieves' Cant. "
             "<em>Always active:</em> Detect Traps 10' (blade pulses cold); Detect Secret Doors 10' (faint vibration); Detect Invisible 20' (whispers location to wielder). "
             "<em>1/day:</em> Telekinesis — move up to 250 lbs at 120' for 6 rounds (concentration); use to pick locks remotely, disarm traps, steal from pockets unseen, manipulate objects through bars. "
             "Personality: obsessively covetous; nudges wielder toward the most valuable nearby item."),
            ("Boots of Elvenkind",
             "Move Silently 95% chance in any terrain or armor. "
             "Stacks with Hide in Shadows; use whichever silent-movement value is higher."),
        ],
    },

    "figgen": {
        "weapon_replace": ("Sling and 20 stones", "Sling +2 and 30 stones"),
        "weapon_add":  [],
        "armor_add":   ["Boots of Elvenkind", "Ring of X-Ray Vision", "Decanter of Endless Water"],
        "items": [
            ("Boots of Elvenkind",
             "Move Silently 95% in any terrain. Combined with Elvenscloak already worn: effectively undetectable while motionless."),
            ("Ring of X-Ray Vision",
             "Concentrate 1 round to see through up to 1' of stone or 3' of wood. "
             "10 minutes/day total use (cumulative; reset each day). "
             "Lead of any thickness blocks vision. "
             "Overuse (>2 turns continuous) causes headache; −4 to all rolls until rested."),
            ("Decanter of Endless Water",
             "Produces fresh water on command word. Three modes: "
             "<strong>TRICKLE</strong> — 1 gal/min; "
             "<strong>STREAM</strong> — 5 gal/min; "
             "<strong>GEYSER</strong> — 30 gal/min, 30' range, 1d4 damage + target must save vs. Stone or be knocked prone."),
        ],
    },

    # ── L6 fighters — each gets one distinct item ────────────────────────────
    "elkhorn": {
        "weapon_replace": ("Sword +1", "Sword +1 (main); Skullcracker — Warhammer +2 (Returning) ✦"),
        "weapon_add":  [],
        "armor_add":   [],
        "items": [
            ("Skullcracker — Warhammer +2 (Returning)",
             "+2 to hit and damage. When thrown (range 60'), returns to wielder's hand at start of next round — never runs out of ammunition. "
             "Deals double damage vs. constructs (golems, animated statues)."),
        ],
    },

    "hawkler": {
        "weapon_replace": None,
        "weapon_add":  [],
        "armor_add":   ["Boots of Speed"],
        "items": [
            ("Boots of Speed",
             "Doubles movement (120' → 240'). In combat: one extra melee attack per round, OR move full speed and still attack. "
             "Cannot wear heavy (plate) armor while benefiting — leather maximum."),
        ],
    },

    "bowmarc": {
        "weapon_replace": None,
        "weapon_add":  [],
        "armor_add":   ["Ring of Protection +2"],
        "items": [
            ("Ring of Protection +2",
             "+2 bonus to Armor Class and all saving throws. Stacks with armor and shield. "
             "With Plate + Shield + Gauntlets already worn, AC drops to 0 (very hard to hit)."),
        ],
    },

    "valkeer": {
        "weapon_replace": ("Sword +1", "Gravesbane — Sword +1, +3 vs. Undead ✦"),
        "weapon_add":  [],
        "armor_add":   ["Ring of Protection +1"],
        "items": [
            ("Gravesbane — Sword +1, +3 vs. Undead",
             "+1 to hit and damage normally. +3 vs. all undead creatures (skeletons, zombies, wights, wraiths, vampires, etc.). "
             "Blade glows faint blue within 30' of undead. Counts as a magic weapon for creatures requiring it."),
            ("Ring of Protection +1",
             "+1 to AC and all saving throws. Combined with Shield: AC 4 in leather — workable frontline defense."),
        ],
    },

    "grimsword": {
        "weapon_replace": None,
        "weapon_add":  [],
        "armor_add":   ["Shield +2"],
        "items": [
            ("Shield +2",
             "+2 to AC (better than a standard shield's +1). "
             "Grimsword's energy-drain sword already makes him extremely dangerous offensively — this shores up his defense."),
        ],
    },

    "zorgar": {
        "weapon_replace": ("Club", "Maul of Thunder — Two-Handed Sword +2 ✦"),
        "weapon_add":  [],
        "armor_add":   ["Gauntlets of Ogre Power"],
        "items": [
            ("Maul of Thunder — Two-Handed Sword +2",
             "+2 to hit and damage. On a natural 20, target must save vs. Death Ray or be stunned for 1 round (loses next action). "
             "Deals 1d10+2 damage (two-handed)."),
            ("Gauntlets of Ogre Power",
             "Strength becomes 18, giving +3 to hit and +3 to damage in melee. "
             "Can force open stuck doors, bars, and portcullises on a 1–3 in 6 (vs. normal 1–2)."),
        ],
    },

    "drex": {
        "weapon_replace": None,
        "weapon_add":  [],
        "armor_add":   ["Cloak of Displacement"],
        "items": [
            ("Cloak of Displacement",
             "The first attack against Drex each round is made at −2 to hit (attacker sees a displaced image). "
             "All ranged attacks against Drex are at −2. "
             "Gives +2 to saves vs. breath weapons and area-of-effect spells."),
        ],
    },

    # ── Other characters needing a boost ────────────────────────────────────
    "molliver": {
        "weapon_replace": None,
        "weapon_add":  [],
        "armor_add":   ["Ring of Protection +2"],
        "items": [
            ("Ring of Protection +2",
             "+2 to AC and all saving throws. With Leather +1 and this ring, AC improves to 5 — "
             "important since thieves cannot use shields."),
        ],
    },

    "mercion": {
        "weapon_replace": ("Mace +1", "Mace +2 ✦"),
        "weapon_add":  [],
        "armor_add":   ["Periapt of Health"],
        "items": [
            ("Mace +2",
             "+2 to hit and damage. Clerics-only blunt weapon; 1d6+2 damage."),
            ("Periapt of Health",
             "Wearer is immune to all diseases, magical or mundane — including mummy rot, lycanthropy (if infected), and filth fever. "
             "Does not cure existing disease; prevents new infection."),
        ],
    },

    "warduke": {
        "weapon_replace": (
            "Sword +1 (flames on command — deals extra 1d6 fire damage when ignited)",
            "Soulcleaver — Sword +2, Flaming ✦ (see Magic Items)",
        ),
        "weapon_add":  [],
        "armor_add":   ["Ring of Protection +2"],
        "items": [
            ("Soulcleaver — Sword +2, Flaming",
             "+2 to hit and damage. On command, blade erupts in black flame: deals +1d6 fire damage per hit. "
             "Black flame also sheds no light (advantage in ambushes). "
             "Creatures killed by Soulcleaver cannot be raised or resurrected by any means short of a Wish."),
            ("Ring of Protection +2",
             "+2 to AC and all saving throws. Warduke in full Plate + this ring reaches AC 0."),
        ],
    },

    "skylla": {
        "weapon_replace": None,
        "weapon_add":  ["Wand of Paralysis (25 charges) ✦ (see Magic Items)"],
        "armor_add":   [],
        "items": [
            ("Wand of Paralysis",
             "25 charges. Range 60'. Target must save vs. Paralysis or be completely paralyzed for 6 turns (1 hour). "
             "One target per charge. Paralyzed target is helpless — allies get automatic backstab/free attack. "
             "Usable by Magic-Users only."),
        ],
    },
}

# ── CSS for the magic items block ─────────────────────────────────────────────
MAGIC_CSS = """
  /* ── Magic items section ── */
  .magic-items-section { margin-bottom: 14px; }
  .magic-items-section h3 { font-size: 13px; margin: 0 0 6px;
    color: var(--accent); border-bottom: 1px solid var(--faint); padding-bottom: 4px; }
  .magic-item { margin-bottom: 8px; padding: 7px 10px;
    border: 1px solid #c9a84c55;
    border-left: 3px solid #c9a84c;
    border-radius: 3px; background: rgba(201,168,76,0.05); }
  .magic-item-name { font-weight: bold; font-size: 12px; color: #8a6914; margin-bottom: 3px; }
  .magic-item-desc { font-size: 11px; line-height: 1.5; }
"""

# ── HTML generators ────────────────────────────────────────────────────────────

def magic_items_html(items):
    inner = ""
    for name, desc in items:
        inner += (
            f'<div class="magic-item">'
            f'<div class="magic-item-name">✦ {name}</div>'
            f'<div class="magic-item-desc">{desc}</div>'
            f'</div>\n'
        )
    return (
        '\n<div class="magic-items-section">\n'
        '  <h3>Magic Items</h3>\n'
        + inner +
        '</div>\n'
    )

# ── Main patching loop ─────────────────────────────────────────────────────────
updated = 0
for name, upd in UPDATES.items():
    path = os.path.join(CHARS_DIR, f"{name}.html")
    if not os.path.exists(path):
        print(f"  SKIP {name} (file not found)")
        continue

    html = open(path, encoding="utf-8").read()

    if "magic-items-section" in html:
        print(f"  SKIP {name} (already patched)")
        continue

    # 1. Inject CSS
    if "magic-item-name" not in html:
        html = html.replace("  @media print {", MAGIC_CSS + "\n  @media print {", 1)

    # 2. Replace a weapon entry if specified
    if upd["weapon_replace"]:
        old_w, new_w = upd["weapon_replace"]
        if old_w in html:
            html = html.replace(old_w, new_w, 1)

    # 3. Append new weapon <li> items to the weapons <ul>
    if upd["weapon_add"]:
        new_lis = "".join(f"<li>{item}</li>" for item in upd["weapon_add"])
        # Find weapons ul and append before its closing tag
        html = re.sub(
            r'(<h4>Weapons</h4>\s*<ul class="equip-list">.*?)(</ul>)',
            lambda m: m.group(1) + new_lis + m.group(2),
            html,
            count=1,
            flags=re.DOTALL,
        )

    # 4. Append to armor & protection paragraph
    if upd["armor_add"]:
        addition = "; ".join(upd["armor_add"])
        html = re.sub(
            r'(<h4 style="margin-top:8px;">Armor &amp; Protection</h4>\s*'
            r'<p[^>]*>)(.*?)(</p>)',
            lambda m: m.group(1) + m.group(2).rstrip() + "; " + addition + m.group(3),
            html,
            count=1,
            flags=re.DOTALL,
        )

    # 5. Inject magic items section before INVENTORY marker
    if upd["items"]:
        marker = "<!-- ── INVENTORY ── -->"
        if marker in html:
            html = html.replace(
                marker,
                magic_items_html(upd["items"]) + marker,
                1,
            )

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    updated += 1
    added = [i[0] for i in upd["items"]]
    print(f"  ✓ {name:12s}  → {', '.join(added)}")

print(f"\nUpdated {updated} / {len(UPDATES)} sheets")
