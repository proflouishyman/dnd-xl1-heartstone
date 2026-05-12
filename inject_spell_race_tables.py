#!/usr/bin/env python3
"""
Inject BECMI demi-human racial abilities and spell quick-reference tables
(with values computed for each character's level) into character sheets.
"""
import os, re

CHARS_DIR = "characters"

# ── Helper ─────────────────────────────────────────────────────────────────────
def res(v, L):
    """Resolve a string or lambda(level) to a string."""
    return v(L) if callable(v) else v

def mm(L):
    """Magic Missile missile count: 1 per 2 levels above 1st, max 5."""
    return min(5, 1 + (L - 1) // 2)

# ── Spell quick-reference ──────────────────────────────────────────────────────
# Format: name -> (range, duration, effect)
# Any field may be a lambda(caster_level) -> str for level-scaled values.
SPELL_REF = {
    # ── Cleric L1 ──────────────────────────────────────────────────────────────
    "Cure Light Wounds":    ("Touch",     "Instant",         "Heals 1d6+1 HP"),
    "Cause Light Wounds":   ("Touch",     "Instant",         "Deals 1d6+1 HP; save vs. spells negates"),
    "Detect Evil":          ("120'",      "6 turns",         "Senses evil intent, creatures, or items within range"),
    "Light":                ("120'",      "6 turns",         "30'-radius illumination; vs. eyes: blinds (save negates)"),
    "Darkness":             ("120'",      "6 turns",         "30'-radius darkness; reverses Light spells"),
    "Protection from Evil": ("Touch",     "12 turns",        "+1 AC & saves vs. evil creatures; blocks evil mental control"),
    "Protection from Good": ("Touch",     "12 turns",        "+1 AC & saves vs. good creatures; blocks good mental control"),
    # ── Cleric L2 ──────────────────────────────────────────────────────────────
    "Bless":                ("60'",       "6 turns",         "Allies in 25'-sq: +1 attacks & morale checks"),
    "Blight":               ("60'",       "6 turns",         "Enemies in 25'-sq: −1 attacks & morale (reverse of Bless)"),
    "Find Traps":           ("30'",       "3 turns",         "All traps within range glow with faint blue light (visible only to caster)"),
    "Hold Person":          ("180'",      "9 turns",         "1d4 humanoids paralyzed; single target saves at −2; save vs. spells"),
    "Silence 15' Radius":   ("180'",      "12 turns",        "No sound in 15' sphere; impossible to cast spells inside"),
    # ── Cleric L3 ──────────────────────────────────────────────────────────────
    "Animate Dead":         ("60'",       "Permanent",       lambda L: f"Animates {L} HD worth of skeletons/zombies under caster's control"),
    "Cause Disease":        ("Touch",     "Permanent",       "Wasting disease: −1d4 to one ability per day until magically cured; save negates"),
    "Cure Disease":         ("Touch",     "Instant",         "Cures any disease; cast within 3 days also cures lycanthropy"),
    "Curse":                ("25' sq",    "Permanent",       "−1 attacks & saves (or DM-chosen penalty); save vs. spells negates"),
    "Remove Curse":         ("Touch",     "Instant",         "Removes one magical curse from a person or object"),
    "Striking":             ("Touch",     "1 turn",          "One weapon deals +1d6 bonus damage for entire duration"),
    # ── Cleric L4 ──────────────────────────────────────────────────────────────
    "Cure Serious Wounds":  ("Touch",     "Instant",         "Heals 2d6+2 HP"),
    "Cause Serious Wounds": ("Touch",     "Instant",         "Deals 2d6+2 HP; save vs. spells negates"),
    "Neutralize Poison":    ("Touch",     "Instant",         "Removes all poison effects; if poisoned death within 10 min, revives at 1 HP"),
    "Speak with Dead":      ("10'",       "3 questions",     "Corpse answers 3 brief factual questions; HD 9+ may resist (save vs. spells)"),
    # ── MU / Elf L1 ────────────────────────────────────────────────────────────
    "Charm Person":         ("120'",      "Until dispelled", "One humanoid saves vs. spells or treats caster as trusted ally"),
    "Detect Magic":         ("60' line",  "2 turns",         "Detects all magical auras within range; shows location but not type"),
    "Floating Disc":        ("20'",       "6 turns",         "Disc holds 500 lbs, floats at hip height, follows caster at walk speed"),
    "Magic Missile":        ("150'",      "Instant",         lambda L: f"{mm(L)} missile(s) × 1d6+1 = {mm(L)}d6+{mm(L)} max; unerring, no save"),
    "Read Languages":       ("Self",      "2 turns",         "Read any non-magical written language, including treasure maps"),
    "Read Magic":           ("Self",      "1 turn",          "Read magic text/runes; required to use any found scroll"),
    "Shield":               ("Self",      "2 turns",         "AC 2 vs. missiles, AC 4 vs. melee; immune to Magic Missile spells"),
    "Sleep":                ("240'",      "Instant",         "2d8 HD of creatures sleep (≤4 HD each); no save; wake if slapped"),
    # ── MU / Elf L2 ────────────────────────────────────────────────────────────
    "Detect Invisible":     (lambda L: f"{L * 10}'", "6 turns", "See invisible creatures and objects within range"),
    "ESP":                  ("60' line",  "12 turns",        "Read surface thoughts of one creature per round; save vs. spells negates"),
    "Invisibility":         ("Touch",     "Until attacks",   "Target invisible until it attacks or casts; also breaks if target is hit"),
    "Knock":                ("60'",       "Instant",         "Opens any locked, stuck, barred, or magically-held door or container"),
    "Levitate":             ("Self",      lambda L: f"{6+L} turns", "Float up/down 20'/round; no horizontal movement; hands free"),
    "Mirror Image":         ("Self",      "6 turns",         "1d4 illusory duplicates; each attack randomly targets an image or caster"),
    "Web":                  ("30'",       "48 turns",        "10'-cube sticky webs; STR 18+ escapes in 2d4 rounds; fire destroys in 2 rounds"),
    "Wizard Lock":          ("Touch",     "Permanent",       "Magically locks door/container; Knock or MU 3+ levels higher can bypass"),
    # ── MU / Elf L3 ────────────────────────────────────────────────────────────
    "Dispel Magic":         ("120'",      "Instant",         "Removes magic: 50% base ±5%/caster level vs. original caster's level"),
    "Fireball":             ("240'",      "Instant",         lambda L: f"{L}d6 dmg in 20'-radius sphere; save vs. spells for half"),
    "Fly":                  ("Touch",     lambda L: f"1d6+{L} turns", "Fly 120'/turn; duration rolled secretly; safe landing on expiry"),
    "Haste":                ("240'",      "3 turns",         "Up to 24 creatures: double move & attacks; ages each target 1 year"),
    "Hold Person":          ("120'",      "9 turns",         "1d4 humanoids paralyzed; 1 target saves at −2; save vs. spells"),
    "Lightning Bolt":       ("180'",      "Instant",         lambda L: f"{L}d6 dmg in 60'×5' bolt; save vs. spells for half; bounces off solid walls"),
    "Water Breathing":      ("Touch",     "1 day",           "Target breathes underwater freely; does not affect air-breathing"),
    # ── MU / Elf L4 ────────────────────────────────────────────────────────────
    "Charm Monster":        ("120'",      "Until dispelled", "Any creature type saves vs. spells or is charmed; monthly save to break"),
    "Charm Monsters":       ("120'",      "Until dispelled", "Any creature type saves vs. spells or is charmed; monthly save to break"),
    "Confusion":            ("120'",      "12 rounds",       "2d8 creatures ≤5 HD act randomly each round; save vs. spells each round"),
    "Ice Storm / Wall of Ice": ("240'",   "Instant / Perm",  "Choice: 3d10 hail dmg in 40'-radius (no save)  OR  wall of ice 1\"/level thick, melts if fire-balled"),
    # ── MU / Elf L5 ────────────────────────────────────────────────────────────
    "Cloudkill":            ("30'",       "6 turns",         "20'×10' cloud moves 20'/round: ≤4 HD die (no save); 5–6 HD save vs. poison or die; 7+ HD 1d10/round"),
}

# ── Demi-human racial abilities ────────────────────────────────────────────────
# Each entry: list of (ability name, value, note) tuples
DEMI_ABILITIES = {
    "elkhorn": {
        "race": "Dwarf", "level": 6,
        "rows": [
            ("Infravision",       "60'",                     "See in total darkness (no color)"),
            ("Underground sense", "2-in-6 (searching)",      "Detect: slanting passages, stone traps, sliding/shifting walls, new construction"),
            ("Combat bonus",      "+1 to hit",               "vs. goblins, hobgoblins, kobolds, orcs"),
            ("Hard to hit",       "Attackers −4",            "Giants, ogres, trolls, cyclopes attack Elkhorn at −4 penalty"),
            ("Save bonus",        "+4 vs. magic & poison",   "Already built into saving throw numbers above"),
            ("Languages",         "Dwarf, Gnome, Goblin, Kobold, Common", ""),
            ("Max level",         "12",                      ""),
        ],
    },
    "peralay": {
        "race": "Elf", "level": 10,
        "rows": [
            ("Infravision",       "60'",                     "See in total darkness (no color)"),
            ("Ghoul immunity",    "Immune",                  "Elf flesh cannot be paralyzed by ghoul touch"),
            ("Detect secret doors","1-in-6 / 2-in-6",       "Auto-notice within 10' while moving; 2-in-6 when actively searching"),
            ("Surprise",          "Only on 1 (in 6)",        "Less likely to be surprised than non-elves (who are surprised on 1–2)"),
            ("Fighter + MU",      "Both classes",            "Casts MU spells in any armor; uses any weapon; gains both class abilities"),
            ("Save bonus",        "+2 vs. wands, paralysis, spells", "Already built into saving throw numbers above"),
            ("Languages",         "Elf, Gnoll, Hobgoblin, Orc, Ogre, Common", ""),
            ("Max level",         "10",                      ""),
        ],
    },
    "figgen": {
        "race": "Halfling", "level": 5,
        "rows": [
            ("Initiative",        "+1 to initiative",        "Add +1 to all individual initiative rolls"),
            ("Missile accuracy",  "+1 to hit",               "All attacks with ranged/missile weapons"),
            ("Outdoor hide",      "9-in-10",                 "Hide in natural terrain (woods, fields, undergrowth); 2-in-6 in dungeons"),
            ("Hard to hit",       "Attackers −4",            "Man-sized and larger creatures attack Figgen at −4 penalty"),
            ("Save bonus",        "+4 vs. magic & dragon breath", "Already built into saving throw numbers above"),
            ("Languages",         "Halfling, Common",        ""),
            ("Max level",         "8",                       ""),
        ],
    },
}

# Which caster each sheet belongs to (for spell-level context)
CASTER_LEVELS = {
    "mercion":   7,
    "zargash":   7,
    "ringlerun": 10,
    "kelek":     7,
    "skylla":    6,
    "peralay":   10,
}

# ── CSS additions ──────────────────────────────────────────────────────────────
EXTRA_CSS = """
  /* ── Racial ability table ── */
  .race-block { margin-bottom: 10px; }
  .race-block h4 { margin: 0 0 4px; font-size: 13px; }
  .race-tbl { width: 100%; border-collapse: collapse; font-size: 11px; }
  .race-tbl th { background: var(--accent); color: white; padding: 3px 6px; text-align: left; }
  .race-tbl td { padding: 3px 6px; border: 1px solid var(--faint); vertical-align: top; }
  .race-tbl tr:nth-child(even) td { background: rgba(0,0,0,0.03); }
  .race-val { font-weight: bold; white-space: nowrap; }
  /* ── Spell quick-reference table ── */
  .spell-qref { margin: 8px 0 10px; }
  .spell-qref h4 { margin: 0 0 4px; font-size: 12px; color: var(--accent); }
  .qref-tbl { width: 100%; border-collapse: collapse; font-size: 11px; }
  .qref-tbl th { background: var(--accent); color: white; padding: 3px 5px; text-align: left; }
  .qref-tbl td { padding: 3px 5px; border: 1px solid var(--faint); vertical-align: top; }
  .qref-tbl tr:nth-child(even) td { background: rgba(0,0,0,0.03); }
  .qref-tbl .sn { font-weight: bold; white-space: nowrap; }
  .qref-tbl .sr, .qref-tbl .sd { white-space: nowrap; color: #555; }
  .qref-lvl { font-size: 10px; font-weight: bold; color: white; background: var(--accent);
    padding: 1px 6px; margin: 6px 0 2px; display: inline-block; border-radius: 3px; }
"""

# ── HTML generators ────────────────────────────────────────────────────────────

def race_block_html(name, data):
    rows = ""
    for ability, val, note in data["rows"]:
        note_td = f'<td style="color:#888;font-size:10px;">{note}</td>' if note else '<td></td>'
        rows += f'  <tr><td>{ability}</td><td class="race-val">{val}</td>{note_td}</tr>\n'
    return (
        f'<div class="race-block">\n'
        f'  <h4>{data["race"]} Racial Abilities (L{data["level"]})</h4>\n'
        f'  <table class="race-tbl">\n'
        f'    <thead><tr><th>Ability</th><th>Value</th><th>Notes</th></tr></thead>\n'
        f'    <tbody>\n{rows}    </tbody>\n'
        f'  </table>\n'
        f'</div>'
    )


def spell_qref_html(name, level, spellbook_html_section):
    """
    Parse the spellbook section from the HTML to extract spell names per level,
    then build a quick-reference table with level-computed values.
    """
    # Extract level blocks: find all "Level N" rows in the spellbook table
    level_blocks = re.findall(
        r'<td class="spell-lvl">Level (\d+)</td>\s*<td>(.*?)</td>',
        spellbook_html_section,
        re.DOTALL,
    )
    if not level_blocks:
        return ""

    rows_html = ""
    for spell_level_str, spell_list_raw in level_blocks:
        spell_level = int(spell_level_str)
        # Split by semicolons, strip whitespace and ×N suffix
        spells = [
            re.sub(r'\s*×\d+\s*$', '', s.strip())
            for s in spell_list_raw.split(";")
            if s.strip()
        ]
        rows_html += f'<tr><td colspan="4" class="qref-lvl">Spell Level {spell_level}</td></tr>\n'
        for spell_name in spells:
            ref = SPELL_REF.get(spell_name)
            if ref:
                rng, dur, eff = ref
                rows_html += (
                    f'<tr>'
                    f'<td class="sn">{spell_name}</td>'
                    f'<td class="sr">{res(rng, level)}</td>'
                    f'<td class="sd">{res(dur, level)}</td>'
                    f'<td>{res(eff, level)}</td>'
                    f'</tr>\n'
                )
            else:
                # Unknown spell — show name only with a placeholder
                rows_html += (
                    f'<tr>'
                    f'<td class="sn">{spell_name}</td>'
                    f'<td colspan="3" style="color:#aaa;">— see rulebook —</td>'
                    f'</tr>\n'
                )

    return (
        '<div class="spell-qref">\n'
        '  <h4>Quick Reference (values at caster level)</h4>\n'
        '  <table class="qref-tbl">\n'
        '    <thead><tr><th>Spell</th><th>Range</th><th>Duration</th><th>Effect</th></tr></thead>\n'
        '    <tbody>\n'
        + rows_html +
        '    </tbody>\n'
        '  </table>\n'
        '</div>\n'
    )


# ── Main patching loop ─────────────────────────────────────────────────────────
all_names = list(DEMI_ABILITIES) + list(CASTER_LEVELS)
# de-duplicate while preserving order
seen = set()
targets = []
for n in all_names:
    if n not in seen:
        seen.add(n)
        targets.append(n)

updated = 0
for name in targets:
    path = os.path.join(CHARS_DIR, f"{name}.html")
    if not os.path.exists(path):
        print(f"  SKIP {name} (file not found)")
        continue

    html = open(path, encoding="utf-8").read()

    if "race-block" in html or "spell-qref" in html:
        print(f"  SKIP {name} (already patched)")
        continue

    # 1. Inject CSS
    if "race-tbl" not in html:
        html = html.replace("  @media print {", EXTRA_CSS + "\n  @media print {", 1)

    # 2. Replace demi-human "Special Abilities" one-liner with full race block
    if name in DEMI_ABILITIES:
        new_block = race_block_html(name, DEMI_ABILITIES[name])
        html = re.sub(
            r"<h4 style='margin-top:8px;'>Special Abilities</h4><ul class='equip-list'>.*?</ul>",
            new_block,
            html,
        )

    # 3. Inject spell quick-reference table into the SPELLS section
    if name in CASTER_LEVELS:
        level = CASTER_LEVELS[name]
        # Grab the full spells section to parse spell names
        spells_match = re.search(
            r'<!-- ── SPELLS.*?-->.*?<!-- ── COMBAT',
            html,
            re.DOTALL,
        )
        if spells_match:
            qref = spell_qref_html(name, level, spells_match.group(0))
            if qref:
                # Inject the quick-ref table right before the "Daily Memorized" header
                html = html.replace(
                    "<h4>Daily Memorized Spells</h4>",
                    qref + "<h4>Daily Memorized Spells</h4>",
                    1,
                )

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    updated += 1
    print(f"  ✓ {name}")

print(f"\nUpdated {updated} / {len(targets)} sheets")
