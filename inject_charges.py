#!/usr/bin/env python3
"""inject_charges.py — add a per-item "Charges" column to each character sheet's
inventory table and wire it to the dnd-api ``inv_charges_N`` override field.

Wands / rods / staves are charged items; clanker now decrements an item's charges
when a player uses one ("I fire my wand of cold"), and dnd-api persists + serves
``charges`` per inventory slot. This surfaces that value as an editable cell on the
web sheet, between Qty and Notes.

Plain-string/regex like the sibling inject scripts, and IDEMPOTENT: a sheet that
already has an ``inv-charges`` input is left untouched, so it is safe to re-run
(and to run after inject_sync.py, which is marker-guarded and won't re-tag).
Run on characters/*.html as a post-processing step.
"""
import glob
import re

CHARS_DIR = "characters"

# Header: insert a Charges column header just before the Notes header, and
# slim the Notes column so the row still fits.
_NOTES_TH = re.compile(r'<th style="width:240px;">Notes</th>')
_NEW_TH = ('<th style="width:70px;">Charges</th>\n'
           '        <th style="width:200px;">Notes</th>')

# Row: the notes cell carries the slot index in its data-field; mirror it into a
# new charges cell placed immediately before the notes cell.
_NOTES_TD = re.compile(
    r'(<td><input type="text" class="inv-notes" '
    r'data-field="inv_notes_(\d+)" placeholder="notes…"></td>)'
)


def _charges_td(m: re.Match) -> str:
    n = m.group(2)
    cell = (f'<td><input type="number" class="inv-charges" '
            f'data-field="inv_charges_{n}" placeholder="—" min="0"></td>')
    return cell + "\n          " + m.group(1)


# CSS for the new input, mirroring .inv-qty. Injected once, before .inv-notes.
_INV_NOTES_CSS = re.compile(r'(\s*)(\.inv-notes \{)')
_CHARGES_CSS = (
    r'\1.inv-charges { width: 60px; text-align: center; font-size: 12px; '
    r'border: none; background: var(--input-bg); padding: 3px; }'
    r'\1\2'
)


def transform(html: str) -> str:
    if 'class="inv-charges"' in html:
        return html                       # already injected — idempotent no-op
    html = _NOTES_TH.sub(_NEW_TH, html, count=1)
    html = _NOTES_TD.sub(_charges_td, html)
    if ".inv-charges {" not in html:
        html = _INV_NOTES_CSS.sub(_CHARGES_CSS, html, count=1)
    return html


def main() -> None:
    changed = 0
    for path in sorted(glob.glob(f"{CHARS_DIR}/*.html")):
        src = open(path, encoding="utf-8").read()
        out = transform(src)
        if out != src:
            open(path, "w", encoding="utf-8").write(out)
            changed += 1
            print(f"  + charges column → {path}")
    print(f"Done — {changed} sheet(s) updated.")


if __name__ == "__main__":
    main()
