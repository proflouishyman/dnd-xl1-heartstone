#!/usr/bin/env python3
"""
Inject BECMI saving throws and attack tables into character HTML sheets.
"""
import os, re

CHARS_DIR = "characters"

COMBAT_TABLES = {
    "strongheart": {
        "saves": {"death_poison":6,"magic_wands":7,"paralysis_stone":8,"dragon_breath":8,"spells":10},
        "thac0": 12,
        "to_hit": {"ac5":7,"ac3":9,"ac1":11,"ac0":12,"acm1":13},
    },
    "elkhorn": {
        "saves": {"death_poison":4,"magic_wands":5,"paralysis_stone":6,"dragon_breath":10,"spells":8},
        "thac0": 14,
        "to_hit": {"ac5":9,"ac3":11,"ac1":13,"ac0":14,"acm1":15},
        "save_note": "Dwarf: −4 to death/poison, wands, paralysis, spells; no dragon breath bonus",
    },
    "mercion": {
        "saves": {"death_poison":9,"magic_wands":10,"paralysis_stone":12,"dragon_breath":14,"spells":12},
        "thac0": 17,
        "to_hit": {"ac5":12,"ac3":14,"ac1":16,"ac0":17,"acm1":18},
    },
    "ringlerun": {
        "saves": {"death_poison":8,"magic_wands":9,"paralysis_stone":8,"dragon_breath":11,"spells":8},
        "thac0": 19,
        "to_hit": {"ac5":14,"ac3":16,"ac1":18,"ac0":19,"acm1":20},
    },
    "peralay": {
        "saves": {"death_poison":6,"magic_wands":5,"paralysis_stone":6,"dragon_breath":8,"spells":8},
        "thac0": 12,
        "to_hit": {"ac5":7,"ac3":9,"ac1":11,"ac0":12,"acm1":13},
        "save_note": "Elf: −2 to wands, paralysis/stone, spells",
    },
    "figgen": {
        "saves": {"death_poison":8,"magic_wands":5,"paralysis_stone":6,"dragon_breath":6,"spells":8},
        "thac0": 14,
        "to_hit": {"ac5":9,"ac3":11,"ac1":13,"ac0":14,"acm1":15},
        "save_note": "Halfling: −4 to wands, paralysis/stone, dragon breath, spells",
    },
    "molliver": {
        "saves": {"death_poison":12,"magic_wands":13,"paralysis_stone":11,"dragon_breath":14,"spells":13},
        "thac0": 17,
        "to_hit": {"ac5":12,"ac3":14,"ac1":16,"ac0":17,"acm1":18},
    },
    "hawkler": {
        "saves": {"death_poison":10,"magic_wands":11,"paralysis_stone":12,"dragon_breath":13,"spells":14},
        "thac0": 17,
        "to_hit": {"ac5":12,"ac3":14,"ac1":16,"ac0":17,"acm1":18},
    },
    "deeth": {
        "saves": {"death_poison":8,"magic_wands":9,"paralysis_stone":10,"dragon_breath":10,"spells":12},
        "thac0": 14,
        "to_hit": {"ac5":9,"ac3":11,"ac1":13,"ac0":14,"acm1":15},
    },
    "bowmarc": {
        "saves": {"death_poison":8,"magic_wands":9,"paralysis_stone":10,"dragon_breath":10,"spells":12},
        "thac0": 14,
        "to_hit": {"ac5":9,"ac3":11,"ac1":13,"ac0":14,"acm1":15},
    },
    "valkeer": {
        "saves": {"death_poison":10,"magic_wands":11,"paralysis_stone":12,"dragon_breath":13,"spells":14},
        "thac0": 17,
        "to_hit": {"ac5":12,"ac3":14,"ac1":16,"ac0":17,"acm1":18},
    },
    "grimsword": {
        "saves": {"death_poison":8,"magic_wands":9,"paralysis_stone":10,"dragon_breath":10,"spells":12},
        "thac0": 14,
        "to_hit": {"ac5":9,"ac3":11,"ac1":13,"ac0":14,"acm1":15},
    },
    "zargash": {
        "saves": {"death_poison":9,"magic_wands":10,"paralysis_stone":12,"dragon_breath":14,"spells":12},
        "thac0": 17,
        "to_hit": {"ac5":12,"ac3":14,"ac1":16,"ac0":17,"acm1":18},
    },
    "kelek": {
        "saves": {"death_poison":8,"magic_wands":9,"paralysis_stone":8,"dragon_breath":11,"spells":8},
        "thac0": 19,
        "to_hit": {"ac5":14,"ac3":16,"ac1":18,"ac0":19,"acm1":20},
    },
    "warduke": {
        "saves": {"death_poison":8,"magic_wands":9,"paralysis_stone":10,"dragon_breath":10,"spells":12},
        "thac0": 14,
        "to_hit": {"ac5":9,"ac3":11,"ac1":13,"ac0":14,"acm1":15},
    },
    "skylla": {
        "saves": {"death_poison":11,"magic_wands":12,"paralysis_stone":11,"dragon_breath":14,"spells":12},
        "thac0": 19,
        "to_hit": {"ac5":14,"ac3":16,"ac1":18,"ac0":19,"acm1":20},
    },
    "zorgar": {
        "saves": {"death_poison":10,"magic_wands":11,"paralysis_stone":12,"dragon_breath":13,"spells":14},
        "thac0": 17,
        "to_hit": {"ac5":12,"ac3":14,"ac1":16,"ac0":17,"acm1":18},
    },
    "drex": {
        "saves": {"death_poison":10,"magic_wands":11,"paralysis_stone":12,"dragon_breath":13,"spells":14},
        "thac0": 17,
        "to_hit": {"ac5":12,"ac3":14,"ac1":16,"ac0":17,"acm1":18},
    },
    "zarak": {
        "saves": {"death_poison":12,"magic_wands":13,"paralysis_stone":11,"dragon_breath":14,"spells":13},
        "thac0": 17,
        "to_hit": {"ac5":12,"ac3":14,"ac1":16,"ac0":17,"acm1":18},
    },
}

SECTION_CSS = """
  /* ── Combat tables ── */
  .combat-tables { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
  .save-table, .attack-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .save-table th, .attack-table th {
    background: var(--accent); color: white;
    padding: 4px 6px; text-align: left; font-size: 11px;
  }
  .save-table td, .attack-table td { padding: 4px 6px; border: 1px solid var(--faint); }
  .save-table tr:nth-child(even) td,
  .attack-table tr:nth-child(even) td { background: rgba(0,0,0,0.03); }
  .save-val { font-weight: bold; text-align: center; font-size: 14px; }
  .thac0-val { font-size: 22px; font-weight: bold; color: var(--accent); }
  .save-note { font-size: 10px; color: #888; font-style: italic; margin-top: 4px; }
"""

def combat_html(name, data):
    s = data["saves"]
    h = data["to_hit"]
    note = data.get("save_note", "")
    note_html = f'<p class="save-note">★ {note}</p>' if note else ""

    return f"""
<!-- ── COMBAT TABLES ── -->
<div class="combat-tables">
  <section>
    <h3>Saving Throws <span style="font-size:10px;color:#888;">(roll d20, need this or higher)</span></h3>
    <table class="save-table">
      <thead><tr><th>Category</th><th style="text-align:center;">Target</th></tr></thead>
      <tbody>
        <tr><td>Death Ray / Poison</td><td class="save-val">{s['death_poison']}</td></tr>
        <tr><td>Magic Wands</td>        <td class="save-val">{s['magic_wands']}</td></tr>
        <tr><td>Paralysis / Stone</td>  <td class="save-val">{s['paralysis_stone']}</td></tr>
        <tr><td>Dragon Breath</td>      <td class="save-val">{s['dragon_breath']}</td></tr>
        <tr><td>Spells / Rods / Staves</td><td class="save-val">{s['spells']}</td></tr>
      </tbody>
    </table>
    {note_html}
  </section>
  <section>
    <h3>Attack Rolls</h3>
    <div style="margin-bottom:8px;">
      <span style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;">THAC0</span>
      <span class="thac0-val" style="margin-left:10px;">{data['thac0']}</span>
      <span style="font-size:11px;color:#888;margin-left:6px;">(roll d20 + AC ≥ THAC0)</span>
    </div>
    <table class="attack-table">
      <thead><tr><th>Target AC</th><th style="text-align:center;">Need (d20)</th></tr></thead>
      <tbody>
        <tr><td>AC 5</td> <td class="save-val">{h['ac5']}</td></tr>
        <tr><td>AC 3</td> <td class="save-val">{h['ac3']}</td></tr>
        <tr><td>AC 1</td> <td class="save-val">{h['ac1']}</td></tr>
        <tr><td>AC 0</td> <td class="save-val">{h['ac0']}</td></tr>
        <tr><td>AC −1</td><td class="save-val">{h['acm1']}</td></tr>
      </tbody>
    </table>
  </section>
</div>
"""

# ── Patch each character sheet ───────────────────────────────────────────────
updated = 0
for name, data in COMBAT_TABLES.items():
    path = os.path.join(CHARS_DIR, f"{name}.html")
    if not os.path.exists(path):
        print(f"  SKIP {name} (file not found)")
        continue

    html = open(path, encoding="utf-8").read()

    # 1. Inject CSS into <style> block (only once)
    if "combat-tables" not in html:
        html = html.replace("  @media print {", SECTION_CSS + "\n  @media print {", 1)

    # 2. Inject the combat section right before <!-- ── INVENTORY ── -->
    marker = "<!-- ── INVENTORY ── -->"
    if marker in html and "Saving Throws" not in html:
        html = html.replace(marker, combat_html(name, data) + marker, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    updated += 1
    print(f"  ✓ {name}")

print(f"\nUpdated {updated} / {len(COMBAT_TABLES)} sheets")
