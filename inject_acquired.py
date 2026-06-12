#!/usr/bin/env python3
"""inject_acquired.py — add the live, player-editable "acquired" sections to each
character sheet so clanker can drop a found weapon/armor/magic-item/spell into the right
place (and players hand-edit it). The baked Spellbook / Weapons / Armor / Magic-Items
reference blocks stay read-only; these are ADDITIVE override-backed sections:

  - "Learned / Added Spells"  (casters only)  learn_spell_N / learn_lvl_N
  - "Magic Items"             (all sheets)     magic_item_N / magic_item_desc_N / magic_item_charges_N
  - "Acquired Weapons & Armor"(all sheets)     weapon_N / armor_N

Each cell is a pre-tagged ``data-field`` input, so dnd-api persists it and sheet-sync.js
wires it like any other field (no bespoke JS). dnd-api's /full reads these rows back
(see api/app.py) and merges learned spells into the spellbook + weapon/armor extras onto
the baked lists, so clanker casts/encumbers them correctly.

Row counts are exported here and imported by gen_manifest.py (the *_rows the bot reads to
know how many slots exist). Plain-string/regex + IDEMPOTENT like the sibling injectors;
run as a post-processing step (anchors on universal markers, so order is flexible).
"""
import glob
import os
import re

CHARS_DIR = "characters"

LEARN_ROWS = 6
MAGIC_ROWS = 8
WEAPON_ROWS = 4
ARMOR_ROWS = 3

_INV_ANCHOR = "<!-- ── INVENTORY ── -->"
_CSS_ANCHOR = "  .magic-items-section {"
_CASTER = re.compile(r"Daily spell slots:")        # only caster sheets get the spell rows

_CSS = (
    "  .acquired-section { margin-bottom: 14px; }\n"
    "  .acquired-section h3 { font-size: 13px; margin: 0 0 6px; }\n"
    "  .acquired-table { width: 100%; border-collapse: collapse; }\n"
    "  .acquired-table th { font-size: 9px; text-transform: uppercase; color: #888;"
    " text-align: left; font-weight: normal; padding: 0 4px 2px; }\n"
    "  .acquired-table td { padding: 1px 3px; }\n"
    "  .acquired-table input { width: 100%; box-sizing: border-box; font-size: 12px;"
    " padding: 2px 4px; border: 1px solid transparent; border-radius: 3px;"
    " background: rgba(0,0,0,.03); color: inherit; }\n"
    "  .acquired-table input:focus { border-color: var(--accent, #4a8a5a);"
    " background: #fff; outline: none; }\n"
    "  .acquired-table .acq-kind { font-size: 10px; color: #888; width: 56px;"
    " white-space: nowrap; }\n"
    "  .magic-items-section {"
)


def _learned_section() -> str:
    body = "".join(
        f'<tr><td><input type="text" data-field="learn_spell_{n}" placeholder="spell…"></td>'
        f'<td><input type="number" data-field="learn_lvl_{n}" min="1" max="9" '
        f'placeholder="lvl"></td></tr>'
        for n in range(1, LEARN_ROWS + 1))
    return (
        '<section class="acquired-section">\n'
        '  <h3>Learned / Added Spells</h3>\n'
        '  <table class="acquired-table"><thead><tr><th>Spell</th>'
        '<th style="width:54px;">Level</th></tr></thead>\n'
        f'  <tbody>{body}</tbody></table>\n'
        '</section>\n')


def _magic_section() -> str:
    body = "".join(
        f'<tr><td><input type="text" data-field="magic_item_{n}" placeholder="item…"></td>'
        f'<td><input type="text" data-field="magic_item_desc_{n}" '
        f'placeholder="effect / description…"></td>'
        f'<td><input type="number" data-field="magic_item_charges_{n}" min="0" '
        f'placeholder="—"></td></tr>'
        for n in range(1, MAGIC_ROWS + 1))
    return (
        '<section class="acquired-section">\n'
        '  <h3>Magic Items</h3>\n'
        '  <table class="acquired-table"><thead><tr><th style="width:30%;">Item</th>'
        '<th>Description</th><th style="width:46px;">Chg</th></tr></thead>\n'
        f'  <tbody>{body}</tbody></table>\n'
        '</section>\n')


def _equip_section() -> str:
    rows = "".join(
        f'<tr><td class="acq-kind">Weapon</td>'
        f'<td><input type="text" data-field="weapon_{n}" placeholder="weapon…"></td></tr>'
        for n in range(1, WEAPON_ROWS + 1))
    rows += "".join(
        f'<tr><td class="acq-kind">Armor</td>'
        f'<td><input type="text" data-field="armor_{n}" placeholder="armor…"></td></tr>'
        for n in range(1, ARMOR_ROWS + 1))
    return (
        '<section class="acquired-section">\n'
        '  <h3>Acquired Weapons &amp; Armor</h3>\n'
        f'  <table class="acquired-table"><tbody>{rows}</tbody></table>\n'
        '</section>\n')


def transform(html: str) -> str:
    if 'class="acquired-section"' in html:
        return html                       # already injected — idempotent no-op
    if _INV_ANCHOR not in html:
        return html
    block = ""
    if _CASTER.search(html):
        block += _learned_section()
    block += _magic_section() + _equip_section()
    html = html.replace(_INV_ANCHOR, block + "\n" + _INV_ANCHOR, 1)
    if ".acquired-section {" not in html and _CSS_ANCHOR in html:
        html = html.replace(_CSS_ANCHOR, _CSS, 1)
    return html


def main() -> None:
    changed = 0
    for path in sorted(glob.glob(f"{CHARS_DIR}/*.html")):
        src = open(path, encoding="utf-8").read()
        out = transform(src)
        if out != src:
            open(path, "w", encoding="utf-8").write(out)
            changed += 1
            print(f"  + acquired → {os.path.basename(path)}")
    print(f"Done — {changed} sheet(s) updated.")


if __name__ == "__main__":
    main()
