#!/usr/bin/env python3
"""inject_slot_track.py — add a live "Slots left" pip readout of remaining daily
spell slots to each spellcaster's sheet, wired to the dnd-api ``spell_slots_used``
field.

Clanker now decrements a caster's daily slot on a definitive cast (``spell_slots_used``
is a per-level list of how many have been spent today); dnd-api persists it and
broadcasts the change over the sheet WebSocket. This surfaces the *remaining* slots
(max − used) as a row of pips under "Daily Memorized Spells": filled = available,
hollow = spent. ``assets/sheet-sync.js`` re-renders it live on every update, and a
click on a pip spends/restores a slot (same persisted field clanker writes), so the
voice tracking and a manual table-side click converge on one value.

The per-level maxima are read straight out of each sheet's existing
``Daily spell slots: <strong>3/2/2/1</strong>`` line, so this naturally targets only
the six casters and needs no duplicate slot table.

Plain-string/regex like the sibling inject scripts, and IDEMPOTENT: a sheet that
already has a ``slot-track`` widget is left untouched, so it is safe to re-run.
Run on characters/*.html as a post-processing step (after inject_class_tables.py,
which renders the maxima line this reads).
"""
import glob
import re

CHARS_DIR = "characters"

# The maxima line inject_class_tables.py renders for every caster.
_SLOTS_LINE = re.compile(r"Daily spell slots: <strong>([\d/]+)</strong>")

# The memorized-spells grid is a single line; the widget goes right after it so the
# memorized spells and the remaining-slot pips sit together.
_MEMO_GRID = re.compile(r'(<div class="memo-grid">.*</div>)')


def _pips_html(max_list):
    """Pre-render the all-available state (a sensible no-JS / pre-snapshot fallback;
    sheet-sync.js overwrites it with live state on boot)."""
    rows = ""
    for i, m in enumerate(max_list):
        if m <= 0:
            continue
        pips = "".join(
            f'<span class="pip on" data-lvl="{i}" data-k="{k}">●</span>'
            for k in range(m)
        )
        rows += (f'<div class="slot-row"><span class="slot-lvl">L{i + 1}</span>'
                 f'<span class="pips">{pips}</span>'
                 f'<span class="slot-num">{m}/{m}</span></div>')
    return rows


def _widget_html(max_list):
    data_max = ",".join(str(m) for m in max_list)
    return (
        f'<div class="slot-track" data-field="spell_slots_used" data-max="{data_max}" '
        f'title="Daily spell slots remaining — click a pip to spend or restore one">'
        f'<span class="slot-track-h">Slots left</span>'
        f'<div class="slot-rows">{_pips_html(max_list)}</div></div>'
    )


# CSS for the widget, injected once just before the .memo-grid rule it sits beside.
_MEMO_CSS = re.compile(r'(\s*)(\.memo-grid \{)')
_SLOT_CSS = (
    r'\1.slot-track { margin-top: 8px; }'
    r'\1.slot-track-h { font-size: 10px; text-transform: uppercase; color: #888;'
    r' display: block; margin-bottom: 3px; }'
    r'\1.slot-rows { display: flex; flex-wrap: wrap; gap: 4px 14px; }'
    r'\1.slot-row { display: flex; align-items: center; gap: 5px; font-size: 11px; }'
    r'\1.slot-lvl { color: #888; min-width: 18px; }'
    r'\1.slot-track .pips { letter-spacing: 2px; }'
    r'\1.slot-track .pip { cursor: pointer; color: #ccc; user-select: none; }'
    r'\1.slot-track .pip.on { color: var(--accent); }'
    r'\1.slot-num { color: #888; font-variant-numeric: tabular-nums; }'
    r'\1\2'
)


def transform(html: str) -> str:
    if 'class="slot-track"' in html:
        return html                       # already injected — idempotent no-op
    m = _SLOTS_LINE.search(html)
    if not m:
        return html                       # not a caster (no daily-slots line)
    max_list = [int(x) for x in m.group(1).split("/") if x]
    if not max_list:
        return html
    widget = _widget_html(max_list)
    # Function replacement: the widget is literal HTML, so keep re.sub from
    # interpreting any backslash/group-ref escapes in it.
    html = _MEMO_GRID.sub(lambda mm: mm.group(1) + "\n      " + widget, html, count=1)
    if ".slot-track {" not in html:
        html = _MEMO_CSS.sub(_SLOT_CSS, html, count=1)
    return html


def main() -> None:
    changed = 0
    for path in sorted(glob.glob(f"{CHARS_DIR}/*.html")):
        src = open(path, encoding="utf-8").read()
        out = transform(src)
        if out != src:
            open(path, "w", encoding="utf-8").write(out)
            changed += 1
            print(f"  + slot-track → {path}")
    print(f"Done — {changed} sheet(s) updated.")


if __name__ == "__main__":
    main()
