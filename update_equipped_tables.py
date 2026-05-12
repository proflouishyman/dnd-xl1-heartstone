#!/usr/bin/env python3
"""
Replace 2-column attack/save tables with 3-column Base / Equipped versions.
  Base    = pure Cyclopedia class/level value
  Equipped = Base adjusted for STR, magic weapon, WIS (rod only), Ring of Protection
Updates the THAC0 display in the stats block.
Adds an AC note for characters whose ring/shield bonus is not yet in the sheet AC.
"""
import os, re

CHARS_DIR = "characters"

SAVE_CATS = [
    "Death Ray / Poison",
    "Magic Wands",
    "Paralysis / Stone",
    "Dragon Breath",
    "Spells / Rods / Staves",
]

# Per Cyclopedia class/level saving throws + equipped adjustments:
#   STR bonus reduces THAC0; WIS 13-15 = -1 to Rod, 16-17 = -2; Ring reduces all saves
CHAR_DATA = {
    "strongheart": {
        "thac0_base": 15, "thac0_eq": 12,
        "saves_base": [8,  9, 10, 11, 12],
        "saves_eq":   [8,  9, 10, 11, 11],   # WIS 13 → rod -1
        "ac_note": None,
    },
    "elkhorn": {
        "thac0_base": 17, "thac0_eq": 15,
        "saves_base": [6,  7,  8, 10,  9],   # Dwarf L4-6
        "saves_eq":   [6,  7,  8, 10,  9],
        "ac_note": None,
    },
    "mercion": {
        "thac0_base": 17, "thac0_eq": 15,
        "saves_base": [9, 10, 12, 14, 13],   # Cleric L5-8
        "saves_eq":   [9, 10, 12, 14, 11],   # WIS 17 → rod -2
        "ac_note": None,
    },
    "ringlerun": {
        "thac0_base": 19, "thac0_eq": 18,
        "saves_base": [11, 12, 11, 14, 12],  # MU L6-10
        "saves_eq":   [10, 11, 10, 13, 10],  # Ring+1 → all -1; WIS 13 → rod -1
        "ac_note": "Ring of Protection +1 → <strong>AC 8</strong> equipped",
    },
    "peralay": {
        "thac0_base": 13, "thac0_eq": 10,
        "saves_base": [2,  4,  4,  3,  3],   # Elf L10 (max level)
        "saves_eq":   [2,  4,  4,  3,  3],
        "ac_note": None,
    },
    "figgen": {
        "thac0_base": 17, "thac0_eq": 14,
        "saves_base": [5,  6,  7,  9,  8],   # Halfling L4-6
        "saves_eq":   [5,  6,  7,  9,  8],
        "ac_note": None,
    },
    "molliver": {
        "thac0_base": 17, "thac0_eq": 15,
        "saves_base": [11, 12, 11, 14, 13],  # Thief L5-8
        "saves_eq":   [9,  10,  9, 12, 11],  # Ring+2 → all -2
        "ac_note": "Ring of Protection +2 → <strong>AC 5</strong> equipped",
    },
    "hawkler": {
        "thac0_base": 17, "thac0_eq": 15,
        "saves_base": [10, 11, 12, 13, 14],  # Fighter L4-6
        "saves_eq":   [10, 11, 12, 13, 14],
        "ac_note": None,
    },
    "deeth": {
        "thac0_base": 17, "thac0_eq": 15,
        "saves_base": [10, 11, 12, 13, 14],
        "saves_eq":   [10, 11, 12, 13, 13],  # WIS 13 → rod -1
        "ac_note": None,
    },
    "bowmarc": {
        "thac0_base": 17, "thac0_eq": 13,
        "saves_base": [10, 11, 12, 13, 14],
        "saves_eq":   [8,   9, 10, 11, 12],  # Ring+2 → all -2
        "ac_note": "Ring of Protection +2 → <strong>AC 0</strong> equipped",
    },
    "valkeer": {
        "thac0_base": 17, "thac0_eq": 14,
        "saves_base": [10, 11, 12, 13, 14],
        "saves_eq":   [9,  10, 11, 12, 13],  # Ring+1 → all -1
        "ac_note": "Ring of Protection +1 → <strong>AC 5</strong> equipped",
    },
    "grimsword": {
        "thac0_base": 17, "thac0_eq": 15,
        "saves_base": [10, 11, 12, 13, 14],
        "saves_eq":   [10, 11, 12, 13, 14],
        "ac_note": "Shield +2 (vs. normal +1) → <strong>AC 0</strong> equipped",
    },
    "zargash": {
        "thac0_base": 17, "thac0_eq": 17,
        "saves_base": [9,  10, 12, 14, 13],  # Cleric L5-8
        "saves_eq":   [9,  10, 12, 14, 12],  # WIS 15 → rod -1
        "ac_note": None,
    },
    "kelek": {
        "thac0_base": 19, "thac0_eq": 17,
        "saves_base": [11, 12, 11, 14, 12],  # MU L6-10
        "saves_eq":   [10, 11, 10, 13, 10],  # Ring+1 → all -1; WIS 13 → rod -1
        "ac_note": "Ring of Protection +1 → <strong>AC 8</strong> equipped",
    },
    "warduke": {
        "thac0_base": 15, "thac0_eq": 11,
        "saves_base": [8,   9, 10, 11, 12],  # Fighter L7-9
        "saves_eq":   [6,   7,  8,  9, 10],  # Ring+2 → all -2
        "ac_note": "Ring of Protection +2 → <strong>AC 0</strong> equipped",
    },
    "skylla": {
        "thac0_base": 19, "thac0_eq": 18,
        "saves_base": [11, 12, 11, 14, 12],  # MU L6-10
        "saves_eq":   [10, 11, 10, 13, 10],  # Ring+1 → all -1; WIS 15 → rod -1
        "ac_note": "Ring of Protection +1 → <strong>AC 8</strong> equipped",
    },
    "zorgar": {
        "thac0_base": 17, "thac0_eq": 12,
        "saves_base": [10, 11, 12, 13, 14],
        "saves_eq":   [10, 11, 12, 13, 14],
        "ac_note": None,
    },
    "drex": {
        "thac0_base": 17, "thac0_eq": 15,
        "saves_base": [10, 11, 12, 13, 14],
        "saves_eq":   [10, 11, 12, 13, 14],
        "ac_note": None,
    },
    "zarak": {
        "thac0_base": 17, "thac0_eq": 14,
        "saves_base": [11, 12, 11, 14, 13],  # Thief L5-8
        "saves_eq":   [11, 12, 11, 14, 12],  # WIS 15 → rod -1
        "ac_note": None,
    },
}

# ── CSS ──────────────────────────────────────────────────────────────────────
EXTRA_CSS = """
  /* ── Equipped tables ── */
  .eq-val { text-align: center; font-weight: bold; color: var(--accent); }
  .ac-equipped-note {
    font-size: 11px; margin-top: 6px; padding: 5px 8px;
    background: rgba(201,168,76,0.08); border-left: 3px solid var(--accent);
    border-radius: 3px;
  }
"""

# ── HTML generators ──────────────────────────────────────────────────────────

def roll_display(roll):
    if roll > 20: return "—"
    if roll < 2:  return "2★"
    return str(roll)


def three_col_attack_table(base_thac0, eq_thac0):
    rows = ""
    for ac in range(9, -4, -1):
        label = f"AC {ac}" if ac >= 0 else f"AC −{abs(ac)}"
        b = roll_display(base_thac0 - ac)
        e = roll_display(eq_thac0   - ac)
        rows += (
            f'        <tr>'
            f'<td>{label}</td>'
            f'<td class="save-val">{b}</td>'
            f'<td class="eq-val">{e}</td>'
            f'</tr>\n'
        )
    return (
        '    <table class="attack-table">\n'
        '      <thead><tr>'
        '<th>Target AC</th>'
        '<th style="text-align:center;">Base</th>'
        '<th style="text-align:center;">Equipped</th>'
        '</tr></thead>\n'
        '      <tbody>\n'
        + rows +
        '      </tbody>\n'
        '    </table>'
    )


def three_col_save_table(base_saves, eq_saves):
    rows = ""
    for i, cat in enumerate(SAVE_CATS):
        b, e = base_saves[i], eq_saves[i]
        rows += (
            f'      <tr>'
            f'<td>{cat}</td>'
            f'<td class="save-val">{b}</td>'
            f'<td class="eq-val">{e}</td>'
            f'</tr>\n'
        )
    return (
        '    <table class="save-table">\n'
        '      <thead><tr>'
        '<th>Category</th>'
        '<th style="text-align:center;">Base</th>'
        '<th style="text-align:center;">Equipped</th>'
        '</tr></thead>\n'
        '      <tbody>\n'
        + rows +
        '      </tbody>\n'
        '    </table>'
    )


# ── Main loop ────────────────────────────────────────────────────────────────
updated = 0
for name, data in CHAR_DATA.items():
    path = os.path.join(CHARS_DIR, f"{name}.html")
    if not os.path.exists(path):
        print(f"  SKIP {name} (file not found)")
        continue

    html = open(path, encoding="utf-8").read()

    if "equipped-tables-done" in html:
        print(f"  SKIP {name} (already patched)")
        continue

    # 1. Inject CSS (before @media print)
    if "eq-val" not in html:
        html = html.replace("  @media print {", EXTRA_CSS + "\n  @media print {", 1)

    # 2. Replace attack table (full AC 9 → −3 matrix already set by prior script)
    new_atk = three_col_attack_table(data["thac0_base"], data["thac0_eq"])
    html = re.sub(
        r'<table class="attack-table">.*?</table>',
        new_atk,
        html,
        count=1,
        flags=re.DOTALL,
    )

    # 3. Replace save table
    new_saves = three_col_save_table(data["saves_base"], data["saves_eq"])
    html = re.sub(
        r'<table class="save-table">.*?</table>',
        new_saves,
        html,
        count=1,
        flags=re.DOTALL,
    )

    # 4. Update THAC0 display: replace current value with "BASE / EQ equipped"
    base_t, eq_t = data["thac0_base"], data["thac0_eq"]
    html = re.sub(
        r'<span class="thac0-val"[^>]*>[\d]+</span>',
        f'<span class="thac0-val" style="margin-left:10px;">{base_t}</span>'
        f'<span style="font-size:11px;color:var(--accent);margin-left:6px;">/ {eq_t} equipped</span>',
        html,
        count=1,
    )

    # 5. Inject AC equipped note (after combat-grid closing div, before Weapons h4)
    if data["ac_note"]:
        ac_note_html = (
            f'\n    <div class="ac-equipped-note">✦ {data["ac_note"]}</div>'
        )
        html = html.replace(
            '    <h4>Weapons</h4>',
            ac_note_html + '\n    <h4>Weapons</h4>',
            1,
        )

    # 6. Mark as patched
    html = html.replace("</body>", "<!-- equipped-tables-done -->\n</body>", 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    updated += 1
    print(f"  ✓ {name:12s}  THAC0 {base_t}/{eq_t}  saves updated")

print(f"\nUpdated {updated} / {len(CHAR_DATA)} sheets")
