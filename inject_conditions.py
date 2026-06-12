#!/usr/bin/env python3
"""inject_conditions.py — add a live "Conditions" widget to every character sheet,
wired to the dnd-api ``conditions`` override field.

Clanker tracks status effects (paralyzed, asleep, poisoned, webbed…) as a JSON list
of ``{name, turns?, source?}`` on the ``conditions`` override, counts timed ones down
on ``/turn``, and shows them in ``/sheet``. dnd-api already persists + broadcasts that
field over the sheet WebSocket — but no element on the page consumed it. This injects a
chip readout (``assets/sheet-sync.js`` renders it live): each active condition is a chip
with its remaining-turn count and a ✕ to clear it, plus a small input to add one by hand.
So the voice/turn tracking and a manual table-side edit converge on one value.

Universal (every sheet, not just casters): anchored just before the SPELLS comment, so
it sits right under the Combat block. Plain-string/regex like the sibling inject scripts,
and IDEMPOTENT: a sheet that already has a ``conditions-track`` widget is left untouched.
Run as a post-processing step BEFORE inject_sync.py (the final tagger).
"""
import glob

CHARS_DIR = "characters"

# Universal anchor present on every generated sheet (caster or not).
_ANCHOR = "<!-- ── SPELLS (if caster) ── -->"

_WIDGET = (
    '<section class="conditions-section">\n'
    '  <div class="conditions-track" data-field="conditions"'
    ' title="Active status effects — click ✕ to clear one, or type to add">\n'
    '    <span class="conditions-h">Conditions</span>\n'
    '    <div class="cond-chips"></div>\n'
    '    <input class="cond-add" type="text" placeholder="+ condition" '
    'aria-label="add condition">\n'
    '  </div>\n'
    '</section>\n\n'
)

# CSS injected once, just before the universal .combat-grid rule it sits beside.
_CSS_ANCHOR = "  .combat-grid {"
_CSS = (
    "  .conditions-section { margin: 0 0 12px; }\n"
    "  .conditions-track { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }\n"
    "  .conditions-h { font-size: 10px; text-transform: uppercase; color: #888;"
    " margin-right: 4px; }\n"
    "  .cond-chips { display: flex; flex-wrap: wrap; gap: 6px; }\n"
    "  .cond-chip { display: inline-flex; align-items: center; gap: 5px; font-size: 11px;"
    " padding: 2px 8px; border-radius: 10px; background: rgba(180,60,60,.16);"
    " color: var(--accent, #c44); white-space: nowrap; }\n"
    "  .cond-chip .cond-turns { color: #888; font-variant-numeric: tabular-nums; }\n"
    "  .cond-chip .cond-x { cursor: pointer; color: #888; font-weight: bold;"
    " user-select: none; }\n"
    "  .cond-chip .cond-x:hover { color: var(--accent, #c44); }\n"
    "  .cond-add { font-size: 11px; border: 1px dashed #ccc; border-radius: 10px;"
    " padding: 2px 8px; width: 96px; background: transparent; color: inherit; }\n"
    "  .combat-grid {"
)


def transform(html: str) -> str:
    if 'class="conditions-track"' in html:
        return html                       # already injected — idempotent no-op
    if _ANCHOR not in html:
        return html                       # unexpected sheet shape — leave it alone
    html = html.replace(_ANCHOR, _WIDGET + _ANCHOR, 1)
    if ".conditions-track {" not in html and _CSS_ANCHOR in html:
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
            print(f"  + conditions → {path}")
    print(f"Done — {changed} sheet(s) updated.")


if __name__ == "__main__":
    main()
