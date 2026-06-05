#!/usr/bin/env python3
"""inject_sync.py — final pipeline step: wire each character sheet to dnd-api.

Run AFTER generate_sheets.py and all the other inject_*.py post-processors. For
every characters/*.html it:

  1. Removes the legacy localStorage save block (so server state isn't clobbered
     on load).
  2. Tags the clanker-relevant fields with stable, semantic ``data-field`` ids
     (name, ability scores, AC/HP/XP, inventory, treasure, notes, portrait, plus
     the header meta — race/class/alignment/save-as/languages — and a Player
     "claim" field). Only genuine *values* are tagged; labels and the derived
     reference tables (THAC0/saves/thief/turn-undead) stay read-only.
  3. Marks display fields ``data-editable`` (sheet-sync.js makes them editable).
  4. Injects /assets/edit.css, a data-char hook, and /assets/sheet-sync.js.

Idempotent and re-runnable on already-injected files: the heavy semantic tagging
(steps 1–4, some of whose search prefixes survive tagging) is guarded by the
``sync-injected`` marker, while the header-meta + Player tagging is written to be
naturally idempotent so a second pass only adds what's missing. Plain-string/regex
like the sibling inject scripts — no extra dependencies.
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

# Header meta values rendered as "<b>Label:</b> value" — wrap the value editable.
META = [("Race", "race"), ("Class", "class_level"), ("Languages", "languages")]

# New "Player" claim line, inserted just above the Race/Class meta row.
PLAYER_LINE = (
    '<div class="char-meta" style="margin-top:6px;">'
    '<span><b>Player:</b> <span class="player-claim" data-field="player" data-editable></span></span>'
    "</div>\n      "
)


def strip_legacy(h):
    h = re.sub(r"\s*<div id=\"save-status\">.*?</div>", "", h, flags=re.S, count=1)

    def drop_ls(m):
        return "" if "localStorage" in m.group(0) else m.group(0)

    return re.sub(r"<script\b[^>]*>.*?</script>", drop_ls, h, flags=re.S)


def tag(h, slug):
    """Semantic tagging that is NOT naturally idempotent — guarded by MARKER."""
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


def tag_meta(h):
    """Tag the header-meta values + add the Player claim line. Naturally idempotent
    (once a value is wrapped, the unwrapped pattern no longer matches), so this can
    run on both fresh and already-injected sheets."""
    for label, key in META:
        h = re.sub(r'(<span><b>%s:</b> )([^<]*)(</span>)' % label,
                   r'\1<span data-field="%s" data-editable>\2</span>\3' % key, h, count=1)
    h = h.replace('<span class="badge">',
                  '<span class="badge" data-field="alignment" data-editable>', 1)
    h = re.sub(r'(Save As: )([^<]*)(</span>)',
               r'\1<span data-field="save_as" data-editable>\2</span>\3', h, count=1)
    if 'data-field="player"' not in h:
        h = h.replace('<div class="char-meta" style="margin-top:8px;">',
                      PLAYER_LINE + '<div class="char-meta" style="margin-top:8px;">', 1)
    return h


def process(path):
    slug = os.path.splitext(os.path.basename(path))[0].lower()
    h = before = open(path, encoding="utf-8").read()
    if MARKER not in h:                     # first pass: heavy (non-idempotent) tagging
        h = strip_legacy(h)
        h = tag(h, slug)
    h = tag_meta(h)                         # always: idempotent meta + player tagging
    if h == before:
        return "unchanged"
    with open(path, "w", encoding="utf-8") as f:
        f.write(h)
    return "ok"


if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(CHARS_DIR, "*.html")))
    for p in files:
        print(f"  sync-injecting {os.path.basename(p)}…", end="", flush=True)
        print(f" {process(p)}")
    print(f"\nDone — {len(files)} sheets.")
