#!/usr/bin/env python3
"""inject_xp_bar.py — add a read-only "XP → next level" progress bar beside the XP
field on each character sheet, plus fix the XP input's baked value.

Each sheet's XP input is ``<input type="number" … value="32,000">`` — but a comma is
invalid for a number input, so the field renders *empty* until an override lands. This
strips the comma (so the real XP shows) and injects a progress bar whose floor/next come
from the BECMI per-class XP table (set_xp.char_xp). ``assets/sheet-sync.js`` recomputes
the fill live whenever the ``xp`` field changes (clanker award or manual edit); the bar
itself persists nothing — ``xp`` is already a synced scalar.

Plain-string/regex like the sibling inject scripts, and IDEMPOTENT: a sheet that already
has an ``xp-bar`` is left untouched. Run AFTER inject_sync.py tags the xp input.
"""
import glob
import os
import re

from set_xp import char_xp

CHARS_DIR = "characters"

_XP_INPUT = re.compile(r'(<input\b[^>]*class="xp-input"[^>]*>)')
_XP_VALUE = re.compile(r'(class="xp-input"[^>]*value=")([\d,]+)(")')

_CSS_ANCHOR = "  .xp-block {"
_CSS = (
    "  .xp-bar { position: relative; width: 130px; height: 9px; margin: 3px 0 0 auto;"
    " background: rgba(0,0,0,.12); border-radius: 5px; overflow: hidden; }\n"
    "  .xp-bar .xp-fill { position: absolute; inset: 0 auto 0 0; width: 0;"
    " background: var(--accent, #4a8a5a); transition: width .3s ease; }\n"
    "  .xp-bar.maxed .xp-fill { width: 100%; }\n"
    "  .xp-bar-label { font-size: 9px; color: #888; text-align: right;"
    " margin-top: 1px; font-variant-numeric: tabular-nums; }\n"
    "  .xp-block {"
)


def _bar_html(floor, nxt):
    nxt_attr = "" if nxt is None else str(nxt)
    return (
        f'\n        <div class="xp-bar" data-floor="{floor}" data-next="{nxt_attr}">'
        f'<div class="xp-fill"></div></div>'
        f'\n        <div class="xp-bar-label"></div>'
    )


def transform(html: str, slug: str) -> str:
    if 'class="xp-bar"' in html:
        return html                       # already injected — idempotent no-op
    if not _XP_INPUT.search(html):
        return html
    floor, nxt = char_xp(slug)
    # Strip the comma from the baked number value so it actually renders.
    html = _XP_VALUE.sub(lambda m: m.group(1) + m.group(2).replace(",", "") + m.group(3),
                         html, count=1)
    # Inject the bar right after the xp input (literal HTML → function replacement).
    bar = _bar_html(floor, nxt)
    html = _XP_INPUT.sub(lambda m: m.group(1) + bar, html, count=1)
    if ".xp-bar {" not in html and _CSS_ANCHOR in html:
        html = html.replace(_CSS_ANCHOR, _CSS, 1)
    return html


def main() -> None:
    changed = 0
    for path in sorted(glob.glob(f"{CHARS_DIR}/*.html")):
        slug = os.path.splitext(os.path.basename(path))[0].lower()
        src = open(path, encoding="utf-8").read()
        out = transform(src, slug)
        if out != src:
            open(path, "w", encoding="utf-8").write(out)
            changed += 1
            print(f"  + xp-bar → {path}")
    print(f"Done — {changed} sheet(s) updated.")


if __name__ == "__main__":
    main()
