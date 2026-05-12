#!/usr/bin/env python3
"""
Inject comprehensive BECMI class tables into character HTML sheets:
  - Extended to-hit matrix (AC 9 → −3) for all 19 characters
  - Fixed daily spell-slot memo grids for all spellcasters
  - Thief skill tables for Molliver (L8) and Zarak (L5)
  - Turn Undead table for Mercion and Zargash (L7 cleric)
  - Fighter sweep-attack note for all fighter-type characters
"""
import os, re

CHARS_DIR = "characters"

# ── Character data ────────────────────────────────────────────────────────────
THAC0 = {
    "strongheart": 12, "elkhorn": 14, "mercion": 17, "ringlerun": 19,
    "peralay": 12, "figgen": 14, "molliver": 17, "hawkler": 17,
    "deeth": 14, "bowmarc": 14, "valkeer": 17, "grimsword": 14,
    "zargash": 17, "kelek": 19, "warduke": 14, "skylla": 19,
    "zorgar": 17, "drex": 17, "zarak": 17,
}

# class → display name for sweep note
SWEEP_CLASS_LABEL = {
    "fighter": "Fighter", "dwarf": "Dwarf", "elf": "Elf", "halfling": "Halfling",
}

CHAR_INFO = {
    "strongheart": {"cls": "fighter",  "level": 8,  "sweep": 8},
    "elkhorn":     {"cls": "dwarf",    "level": 6,  "sweep": 6},
    "mercion":     {"cls": "cleric",   "level": 7,  "sweep": 0},
    "ringlerun":   {"cls": "mage",     "level": 10, "sweep": 0},
    "peralay":     {"cls": "elf",      "level": 10, "sweep": 10},
    "figgen":      {"cls": "halfling", "level": 5,  "sweep": 5},
    "molliver":    {"cls": "thief",    "level": 8,  "sweep": 0},
    "hawkler":     {"cls": "fighter",  "level": 6,  "sweep": 6},
    "deeth":       {"cls": "fighter",  "level": 6,  "sweep": 6},
    "bowmarc":     {"cls": "fighter",  "level": 6,  "sweep": 6},
    "valkeer":     {"cls": "fighter",  "level": 6,  "sweep": 6},
    "grimsword":   {"cls": "fighter",  "level": 6,  "sweep": 6},
    "zargash":     {"cls": "cleric",   "level": 7,  "sweep": 0},
    "kelek":       {"cls": "mage",     "level": 7,  "sweep": 0},
    "warduke":     {"cls": "fighter",  "level": 9,  "sweep": 9},
    "skylla":      {"cls": "mage",     "level": 6,  "sweep": 0},
    "zorgar":      {"cls": "fighter",  "level": 6,  "sweep": 6},
    "drex":        {"cls": "fighter",  "level": 6,  "sweep": 6},
    "zarak":       {"cls": "thief",    "level": 5,  "sweep": 0},
}

# Daily spell slots per spellcaster (BECMI Expert values from module)
SPELL_SLOTS = {
    "mercion":   {"type": "Cleric",     "level": 7,  "slots": [2, 2, 2, 1]},
    "zargash":   {"type": "Cleric",     "level": 7,  "slots": [2, 2, 2, 1]},
    "ringlerun": {"type": "Magic-User", "level": 10, "slots": [3, 2, 2, 1]},
    "kelek":     {"type": "Magic-User", "level": 7,  "slots": [3, 2, 2, 1]},
    "skylla":    {"type": "Magic-User", "level": 6,  "slots": [2, 2, 2]},
    "peralay":   {"type": "Elf",        "level": 10, "slots": [3, 3, 3, 3, 2]},
}

# Thief skills (BECMI Expert)
THIEF_SKILLS = {
    "molliver": {
        "level": 8, "backstab": "×3",
        "skills": [
            ("Open Locks",        "60%"),
            ("Find/Remove Traps", "45%"),
            ("Pick Pockets",      "55%"),
            ("Move Silently",     "55%"),
            ("Climb Walls",       "94%"),
            ("Hide in Shadows",   "37%"),
            ("Hear Noise",        "1–4 on d6"),
        ],
    },
    "zarak": {
        "level": 5, "backstab": "×3",
        "skills": [
            ("Open Locks",        "35%"),
            ("Find/Remove Traps", "30%"),
            ("Pick Pockets",      "40%"),
            ("Move Silently",     "40%"),
            ("Climb Walls",       "91%"),
            ("Hide in Shadows",   "28%"),
            ("Hear Noise",        "1–3 on d6"),
        ],
    },
}

# Turn Undead — Cleric L7 (BECMI Expert)
# D=Destroyed, T=Turned, number=d20 roll needed, —=impossible
TURN_UNDEAD_L7 = [
    ("Skeleton",  "1 HD",   "D"),
    ("Zombie",    "2 HD",   "D"),
    ("Ghoul",     "2 HD",   "D"),
    ("Wight",     "3 HD",   "D"),
    ("Wraith",    "4 HD",   "T"),
    ("Mummy",     "5–6 HD", "T"),
    ("Spectre",   "6 HD",   "7"),
    ("Vampire",   "7–9 HD", "9"),
    ("Ghost",     "10 HD",  "11"),
    ("Lich",      "11+ HD", "—"),
]

# ── CSS additions ─────────────────────────────────────────────────────────────
EXTRA_CSS = """
  /* ── Extended class tables ── */
  .class-tables-wrap { margin-bottom: 12px; }
  .class-tables-wrap h3 { font-size: 13px; margin: 10px 0 4px; }
  .thief-tbl, .turn-tbl {
    width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 8px;
  }
  .thief-tbl th, .turn-tbl th {
    background: var(--accent); color: white;
    padding: 4px 6px; text-align: left; font-size: 11px;
  }
  .thief-tbl td, .turn-tbl td { padding: 4px 6px; border: 1px solid var(--faint); }
  .thief-tbl tr:nth-child(even) td,
  .turn-tbl tr:nth-child(even) td { background: rgba(0,0,0,0.03); }
  .skill-val { font-weight: bold; text-align: center; }
  .turn-result { font-weight: bold; text-align: center; font-size: 15px; }
  .turn-D { color: #c62828; }
  .turn-T { color: #1565c0; }
  .sweep-callout {
    font-size: 12px; background: rgba(0,0,0,0.04);
    border-left: 3px solid var(--accent); padding: 6px 10px;
    margin-bottom: 10px; border-radius: 3px;
  }
  .backstab-badge {
    display: inline-block; background: var(--accent); color: white;
    font-size: 11px; font-weight: bold; padding: 2px 8px;
    border-radius: 4px; margin-bottom: 6px;
  }
"""

# ── HTML generators ────────────────────────────────────────────────────────────

def extended_attack_table(thac0_val):
    """Replace the 5-row attack table with a full AC 9 → −3 matrix."""
    rows = ""
    for ac in range(9, -4, -1):
        roll = thac0_val - ac
        if roll > 20:
            disp = "—"
        elif roll < 2:
            disp = "2★"
        else:
            disp = str(roll)
        label = f"AC {ac}" if ac >= 0 else f"AC −{abs(ac)}"
        rows += f'        <tr><td>{label}</td><td class="save-val">{disp}</td></tr>\n'
    return (
        '    <table class="attack-table">\n'
        '      <thead><tr>'
        '<th>Target AC</th>'
        '<th style="text-align:center;">Need (d20)</th>'
        '</tr></thead>\n'
        '      <tbody>\n'
        + rows +
        '      </tbody>\n'
        '    </table>'
    )


def memo_grid_html(slots):
    """Generate corrected memo-grid with one input per daily spell slot."""
    inner = ""
    for lvl, count in enumerate(slots, 1):
        inputs = "".join(
            '<input type="text" class="memo-input" placeholder="spell…">'
            for _ in range(count)
        )
        inner += f'<div class="memo-slot"><span class="memo-lvl">Lvl {lvl}</span>{inputs}</div>'
    return f'<div class="memo-grid">{inner}</div>'


def thief_html(data):
    rows = "".join(
        f'      <tr><td>{skill}</td><td class="skill-val">{val}</td></tr>\n'
        for skill, val in data["skills"]
    )
    return f"""
<div class="class-tables-wrap">
  <h3>Thief Skills — Level {data['level']}</h3>
  <span class="backstab-badge">Backstab {data['backstab']} damage (surprise, melee)</span>
  <table class="thief-tbl">
    <thead><tr><th>Skill</th><th style="text-align:center;">Success</th></tr></thead>
    <tbody>
{rows}    </tbody>
  </table>
</div>"""


def turn_undead_html(is_chaotic):
    action = "Control" if is_chaotic else "Turn"
    legend = "C=Controlled" if is_chaotic else "D=Destroyed, T=Turned"
    rows = ""
    for undead, hd, result in TURN_UNDEAD_L7:
        if result == "D":
            cls = "turn-D"
            disp = "C" if is_chaotic else "D"
        elif result == "T":
            cls = "turn-T"
            disp = "C" if is_chaotic else "T"
        else:
            cls = ""
            disp = result
        rows += (
            f'      <tr><td>{undead}</td>'
            f'<td style="color:#888;font-size:10px;">{hd}</td>'
            f'<td class="turn-result {cls}">{disp}</td></tr>\n'
        )
    return f"""
<div class="class-tables-wrap">
  <h3>{action} Undead — Cleric Level 7</h3>
  <p style="font-size:10px;color:#888;">{legend}, # = roll d20 equal or higher; affects 2d6 HD</p>
  <table class="turn-tbl">
    <thead><tr><th>Undead</th><th>HD</th><th style="text-align:center;">Result</th></tr></thead>
    <tbody>
{rows}    </tbody>
  </table>
</div>"""


def sweep_html(cls, level):
    label = SWEEP_CLASS_LABEL.get(cls, "Fighter")
    return f"""
<div class="sweep-callout">
  <strong>Multiple Attacks ({label} L{level}):</strong>
  Against creatures with 1 HD or fewer, attack <strong>{level}×</strong> per round (1 per level).
  Roll each attack separately. Normal 1 attack vs creatures with more than 1 HD.
</div>"""


# ── Main patching loop ────────────────────────────────────────────────────────
updated = 0
for name, info in CHAR_INFO.items():
    path = os.path.join(CHARS_DIR, f"{name}.html")
    if not os.path.exists(path):
        print(f"  SKIP {name} (file not found)")
        continue

    html = open(path, encoding="utf-8").read()

    # Idempotency: skip if already patched
    if "class-tables-wrap" in html or "extended-class-tables-done" in html:
        print(f"  SKIP {name} (already patched)")
        continue

    # 1. Inject additional CSS (before @media print block)
    if "thief-tbl" not in html:
        html = html.replace("  @media print {", EXTRA_CSS + "\n  @media print {", 1)

    # 2. Replace the 5-row attack table with full AC 9→−3 matrix
    new_atk = extended_attack_table(THAC0[name])
    html = re.sub(
        r'<table class="attack-table">.*?</table>',
        new_atk,
        html,
        flags=re.DOTALL,
    )

    # 3. Fix memo-grid slot counts for spellcasters
    if name in SPELL_SLOTS:
        slots = SPELL_SLOTS[name]["slots"]
        new_grid = memo_grid_html(slots)
        # memo-grid is on one line; greedy .* matches the full outer div
        html = re.sub(r'<div class="memo-grid">.*</div>', new_grid, html)

    # 4. Build class-specific section to insert before INVENTORY
    extra = ""
    if name in SPELL_SLOTS:
        si = SPELL_SLOTS[name]
        slot_display = "/".join(str(s) for s in si["slots"])
        extra += f'\n<p style="font-size:11px;color:#888;margin:0 0 6px;">Daily spell slots: <strong>{slot_display}</strong> ({si["type"]} L{si["level"]})</p>'

    if name in THIEF_SKILLS:
        extra += thief_html(THIEF_SKILLS[name])

    if name in ("mercion", "zargash"):
        extra += turn_undead_html(is_chaotic=(name == "zargash"))

    if info["sweep"] > 0:
        extra += sweep_html(info["cls"], info["sweep"])

    if extra:
        marker = "<!-- ── INVENTORY ── -->"
        if marker in html:
            html = html.replace(
                marker,
                f"\n<!-- ── CLASS TABLES ── -->\n{extra}\n{marker}",
                1,
            )

    # 5. Mark as patched
    html = html.replace("</body>", "<!-- extended-class-tables-done -->\n</body>", 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    updated += 1
    print(f"  ✓ {name}")

print(f"\nUpdated {updated} / {len(CHAR_INFO)} sheets")
