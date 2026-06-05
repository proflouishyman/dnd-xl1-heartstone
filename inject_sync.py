#!/usr/bin/env python3
"""inject_sync.py — final pipeline step: wire each character sheet to dnd-api.

Run AFTER generate_sheets.py and all the other inject_*.py post-processors. For
every characters/*.html it:

  1. Removes the legacy localStorage save block (so server state isn't clobbered
     on load).
  2. Tags the clanker-relevant fields with stable, semantic ``data-field`` ids
     (name, ability scores, AC/HP/XP, inventory, treasure, notes, portrait …).
     The long tail of "every other cell" is tagged generically at runtime by
     sheet-sync.js (a deterministic DOM walk), so we only need clean keys here.
  3. Marks display fields ``data-editable`` (edit-mode toggles contenteditable).
  4. Injects /assets/edit.css, a data-char hook, and /assets/sheet-sync.js.

Idempotent: re-running is a no-op once the marker is present (and the pipeline
regenerates files from scratch anyway). Plain-string/regex like the sibling
inject scripts — no extra dependencies.
"""
import glob
import os
import re

CHARS_DIR = "characters"
MARKER = "<!-- sync-injected -->"

HEAD_INJECT = '<link rel="stylesheet" href="/assets/edit.css">\n'
BODY_INJECT = '\n<script src="/assets/sheet-sync.js" defer></script>\n' + MARKER + "\n"

COMBAT = {"Armor Class": "ac", "Movement": "mv", "HP Maximum": "hp_max", "Attacks/Round": "attacks"}
COINS = {"PP": "coin_pp", "GP": "coin_gp", "EP": "coin_ep", "SP": "coin_sp", "CP": "coin_cp"}


def strip_legacy(h):
    h = re.sub(r"\s*<div id=\"save-status\">.*?</div>", "", h, flags=re.S, count=1)

    def drop_ls(m):
        return "" if "localStorage" in m.group(0) else m.group(0)

    return re.sub(r"<script\b[^>]*>.*?</script>", drop_ls, h, flags=re.S)


def tag(h, slug):
    # ── header ──
    h = h.replace('<div class="char-name">',
                  '<div class="char-name" data-field="name" data-editable>', 1)
    h = h.replace('<div class="char-epithet">',
                  '<div class="char-epithet" data-field="epithet" data-editable>', 1)
    h = h.replace('<img class="portrait" ',
                  '<img class="portrait" data-field="portrait" ', 1)
    h = h.replace('<input type="number" class="hp-current" id="hp-cur"',
                  '<input type="number" class="hp-current" id="hp-cur" data-field="hp_current"', 1)
    h = h.replace('<input type="number" class="xp-input"',
                  '<input type="number" class="xp-input" data-field="xp"', 1)
    h = h.replace('<textarea class="notes-area"',
                  '<textarea class="notes-area" data-field="notes"', 1)

    # ── ability scores (keyed by the adjacent STR/DEX/… label) ──
    def ability(m):
        stat = m.group(1).lower()
        return m.group(0).replace(
            '<div class="ability-score">',
            '<div class="ability-score" data-field="%s_score" data-editable>' % stat)

    h = re.sub(r'<div class="ability-name">(STR|DEX|INT|CON|WIS|CHA)</div>\s*'
               r'<div class="ability-score">', ability, h)

    # ── combat values (keyed by the adjacent label) ──
    def combat(m):
        key = COMBAT.get(m.group(1).strip())
        if not key:
            return m.group(0)
        return m.group(0).replace(
            '<div class="combat-value">',
            '<div class="combat-value" data-field="%s" data-editable>' % key)

    h = re.sub(r'<div class="combat-label">([^<]+)</div><div class="combat-value">', combat, h)

    # ── treasure coins (keyed by the adjacent label) ──
    def coin(m):
        label = m.group(1)
        key = next((k for ab, k in COINS.items() if "(%s)" % ab in label), None)
        if not key:
            return m.group(0)
        return m.group(0).replace(
            '<input type="number" class="coin-input"',
            '<input type="number" class="coin-input" data-field="%s"' % key)

    h = re.sub(r'<div class="coin-label">([^<]+)</div>'
               r'<input type="number" class="coin-input"', coin, h)

    # ── inventory rows + memorized spells (positional counters) ──
    def counter():
        n = [0]
        def nxt(_):
            n[0] += 1
            return n[0]
        return nxt

    ic, qc, nc, mc = counter(), counter(), counter(), counter()
    h = re.sub(r'<input type="text" class="inv-item"',
               lambda m: '<input type="text" class="inv-item" data-field="inv_item_%d"' % ic(m), h)
    h = re.sub(r'<input type="number" class="inv-qty"',
               lambda m: '<input type="number" class="inv-qty" data-field="inv_qty_%d"' % qc(m), h)
    h = re.sub(r'<input type="text" class="inv-notes"',
               lambda m: '<input type="text" class="inv-notes" data-field="inv_notes_%d"' % nc(m), h)
    h = re.sub(r'<input type="text" class="memo-input"',
               lambda m: '<input type="text" class="memo-input" data-field="memo_%d"' % mc(m), h)

    # ── document hooks + asset injection ──
    h = re.sub(r"<body(\b[^>]*)>",
               lambda m: '<body%s data-char="%s">' % (m.group(1), slug), h, count=1)
    h = h.replace("</head>", HEAD_INJECT + "</head>", 1)
    h = h.replace("</body>", BODY_INJECT + "</body>", 1)
    return h


def process(path):
    slug = os.path.splitext(os.path.basename(path))[0].lower()
    h = open(path, encoding="utf-8").read()
    if MARKER in h:
        return "skip (already injected)"
    h = strip_legacy(h)
    h = tag(h, slug)
    with open(path, "w", encoding="utf-8") as f:
        f.write(h)
    return "ok"


if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(CHARS_DIR, "*.html")))
    for p in files:
        print(f"  sync-injecting {os.path.basename(p)}…", end="", flush=True)
        print(f" {process(p)}")
    print(f"\nDone — {len(files)} sheets.")
