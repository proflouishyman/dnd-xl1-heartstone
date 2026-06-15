#!/usr/bin/env python3
"""tools/rc_catalogs.py — parse the RC markdown into structured *catalogs* the clanker
bot looks up when a character ACQUIRES something, so an added weapon / armor / spell /
magic item arrives with its RC stats + description. Sibling to rc_extract.py (which owns
the monster DB + encumbrance weights); same no-LLM, exact-dict-lookup build-step contract.

    python tools/rc_catalogs.py [--rc docs/rules-cyclopedia] [--out data/rc]

Emits, under --out:
  weapons_catalog.json     {name_lower: {display, damage, range, enc, cost, notes}}
  armor_catalog.json       {name_lower: {display, ac, enc, cost, notes}}
  spells_catalog.json      {name_lower: {name, class, level, range, duration, effect, desc}}
  magic_items_catalog.json {name_lower: {name, category, desc}}
  equipment_catalog.json   {name_lower: {display, cost, enc[, desc]}}  (general gear)

It also prints a COVERAGE report (4A.0 gate): determination-subtable item names in
16-treasure/01-magical-items.md that have no description entry — author/fix those in the
RC markdown before relying on the catalog.

By default it then SHIPS the catalogs into the clanker bot's data dir (the only consumer),
renaming `<name>_catalog.json` → `rc_<name>.json` (e.g. equipment_catalog → rc_equipment).
Pass --no-ship to skip, or --clanker-data to point elsewhere.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from rc_extract import _first_int, _norm_minus

_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
             "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9}

# magic-item description files → category
_MAGIC_FILES = {
    "02-potions.md": "potion", "03-scrolls.md": "scroll",
    "04-wands-staves-rods.md": "wand", "05-rings.md": "ring",
    "06-misc-items.md": "misc", "07-weapons-and-armor.md": "weapon-armor",
}
_SPELL_FILES = {
    "cleric-spells.md": "cleric", "druid-spells.md": "druid",
    "mu-spells-levels-1-3.md": "mu", "mu-spells-levels-4-6.md": "mu",
    "mu-spells-levels-7-9.md": "mu",
}

_BULLET = re.compile(r"^\s*[-*] \*\*(?P<name>[^*]+?):\*\*\s*(?P<desc>.*)")
_LEVEL_HDR = re.compile(r"^##\s+(\w+)\s+Level\b", re.I)
_SPELL_HDR = re.compile(r"^###\s+(.+?)\s*$")


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _cells(row: str) -> list:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _strip_md(s: str) -> str:
    return re.sub(r"\\?\*+", "", str(s or "")).strip()


# ── weapons + armor (04-equipment.md tables) ─────────────────────────────────
def parse_equipment_tables(rc: Path) -> tuple[dict, dict]:
    text = (rc / "04-equipment" / "04-equipment.md").read_text(encoding="utf-8")
    rows = text.splitlines()
    weapons: dict = {}
    armor: dict = {}
    k = 0
    while k < len(rows):
        line = rows[k]
        if line.lstrip().startswith("|") and "enc" in line.lower():
            hdr = [c.lower() for c in _cells(line)]

            def find(key):
                return next((i for i, c in enumerate(hdr) if key in c), None)

            col = {"enc": find("enc"), "dmg": find("damage"), "rng": find("range"),
                   "cost": find("cost"), "ac": find("ac"), "notes": find("note")}
            name_col = next((i for i, c in enumerate(hdr) if any(
                key in c for key in ("item", "armor type", "weapon", "name"))), 0)
            is_weapon = col["dmg"] is not None
            is_armor = col["ac"] is not None and not is_weapon
            k += 1
            if k < len(rows) and set(rows[k].strip()) <= set("|-: "):
                k += 1
            while k < len(rows) and rows[k].lstrip().startswith("|"):
                cs = _cells(rows[k])

                def cell(key):
                    i = col[key]
                    return _strip_md(cs[i]) if i is not None and i < len(cs) else ""

                if len(cs) > name_col:
                    nm = _strip_md(cs[name_col])
                    enc = _first_int(cell("enc")) if col["enc"] is not None else None
                    ac_val = _first_int(_norm_minus(cell("ac"))) if is_armor else None
                    if nm and is_weapon and cell("dmg"):   # skip group rows (empty dmg)
                        weapons.setdefault(_norm(nm), {
                            "display": nm, "damage": cell("dmg"), "range": cell("rng"),
                            "enc": enc, "cost": cell("cost"), "notes": cell("notes")})
                    elif nm and is_armor and ac_val is not None:
                        armor.setdefault(_norm(nm), {
                            "display": nm, "ac": ac_val, "enc": enc,
                            "cost": cell("cost"), "notes": cell("notes")})
                k += 1
            continue
        k += 1
    return weapons, armor


# ── spells (03-spells-and-spellcasting/*) ────────────────────────────────────
def _parse_spell_body(buf: list) -> tuple:
    text = "\n".join(buf).strip()
    if not text:
        return "", "", "", ""
    first, _, rest = text.partition("\n")
    fd = {k.lower(): v.strip() for k, v in
          re.findall(r"\*\*(Range|Duration|Effect):\*\*\s*([^·\n]*)", first)}
    if fd:
        return fd.get("range", ""), fd.get("duration", ""), fd.get("effect", ""), rest.strip()
    return "", "", "", text


def parse_spells(rc: Path) -> dict:
    spells: dict = {}
    base = rc / "03-spells-and-spellcasting"
    for fname, cls in _SPELL_FILES.items():
        p = base / fname
        if not p.exists():
            continue
        level = None
        name = None
        buf: list = []

        def flush():
            if name and level:
                rng, dur, eff, desc = _parse_spell_body(buf)
                spells.setdefault(_norm(name), {
                    "name": name, "class": cls, "level": level,
                    "range": rng, "duration": dur, "effect": eff, "desc": desc})

        for line in p.read_text(encoding="utf-8").splitlines():
            mh = _LEVEL_HDR.match(line)
            if mh:
                flush()
                level = _ORDINALS.get(mh.group(1).lower())
                name, buf = None, []
                continue
            ms = _SPELL_HDR.match(line)
            if ms:
                flush()
                name, buf = _strip_md(ms.group(1)), []
                continue
            if name is not None:
                buf.append(line)
        flush()
    return spells


# ── magic items (16-treasure/02..07 description bullets) ─────────────────────
def parse_magic_items(rc: Path) -> dict:
    items: dict = {}
    base = rc / "16-treasure"
    for fname, category in _MAGIC_FILES.items():
        p = base / fname
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            m = _BULLET.match(line)
            if not m:
                continue
            nm = _strip_md(m.group("name"))
            desc = m.group("desc").strip()
            if nm and desc:
                items.setdefault(_norm(nm), {
                    "name": nm, "category": category, "desc": desc})
    return items


# ── general adventuring gear (04-equipment.md "Adventuring Gear Table") ───────
def _parse_gear_descs(rows: list, start: int) -> dict:
    """Best-effort {name_lower: sentence} from the bold-led 'Key notes' prose that
    follows the Adventuring Gear Table (lantern/torch/rations/rope/thieves' tools/…).
    The blob is '…text **Name** desc; a **Name** desc. …', so splitting on '**'
    alternates plain-text / bold-name / desc; we trim the trailing 'a/an' lead-in
    that introduces the next bold item."""
    k = start
    while k < len(rows) and "key notes" not in rows[k].lower():
        if rows[k].startswith("## "):           # stayed inside the gear section
            return {}
        k += 1
    buf: list = []
    while k < len(rows) and rows[k].strip():     # the wrapped 'Key notes' paragraph
        buf.append(rows[k].strip())
        k += 1
    parts = " ".join(buf).split("**")            # …text, NAME, desc, NAME, desc…
    descs: dict = {}
    for i in range(1, len(parts) - 1, 2):
        name = _strip_md(parts[i])
        d = re.sub(r"[;.]\s+an?\s*$", "", parts[i + 1].strip(), flags=re.I)
        d = d.strip().rstrip(" ;,")
        if name and d:
            descs[_norm(name)] = d
    return descs


def parse_general_equipment(rc: Path) -> dict:
    """The single 'Adventuring Gear Table' (rope, torch, rations, oil, holy water, …)
    → {name_lower: {display, cost, enc[, desc]}}. Heading-anchored on 'Adventuring
    Gear' so it never grabs the weapons/ammunition/armor/transport/siege tables that
    also carry cost+enc columns."""
    text = (rc / "04-equipment" / "04-equipment.md").read_text(encoding="utf-8")
    rows = text.splitlines()
    gear: dict = {}
    k = 0
    while k < len(rows) and "adventuring gear" not in rows[k].lower():
        k += 1
    while k < len(rows) and not (
            rows[k].lstrip().startswith("|") and "enc" in rows[k].lower()):
        k += 1
    if k >= len(rows):
        return gear
    hdr = [c.lower() for c in _cells(rows[k])]
    cost_col = next((i for i, c in enumerate(hdr) if "cost" in c), None)
    enc_col = next((i for i, c in enumerate(hdr) if "enc" in c), None)
    name_col = next((i for i, c in enumerate(hdr)
                     if any(key in c for key in ("item", "name"))), 0)
    k += 1
    if k < len(rows) and set(rows[k].strip()) <= set("|-: "):     # separator row
        k += 1
    while k < len(rows) and rows[k].lstrip().startswith("|"):
        cs = _cells(rows[k])
        if len(cs) > name_col:
            nm = _strip_md(cs[name_col])
            cost = (_strip_md(cs[cost_col])
                    if cost_col is not None and cost_col < len(cs) else "")
            enc = (_first_int(_strip_md(cs[enc_col]))
                   if enc_col is not None and enc_col < len(cs) else None)
            if nm and (cost or enc is not None):
                gear.setdefault(_norm(nm), {"display": nm, "cost": cost, "enc": enc})
        k += 1
    for nm, desc in _parse_gear_descs(rows, k).items():     # attach best-effort descs
        dw = set(re.findall(r"[a-z0-9]+", nm))
        for key, entry in gear.items():
            if dw and dw <= set(re.findall(r"[a-z0-9]+", key)):
                entry.setdefault("desc", desc)
                break
    return gear


# ── 4A.0 coverage gate: subtable item names vs described items ───────────────
def subtable_names(rc: Path) -> list:
    """Item names from the d100 determination subtables in 01-magical-items.md."""
    p = rc / "16-treasure" / "01-magical-items.md"
    if not p.exists():
        return []
    names: list = []
    in_sub = False        # skip the Main Table (category labels); only parse Subtables
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_sub = in_sub or line.lower().startswith("## subtable")
            continue
        if not in_sub or not line.lstrip().startswith("|"):
            continue
        cs = _cells(line)
        # data rows are: | range | name | range | name | … and start with a die range;
        # skip the "| 1d100 | Item |" header rows.
        if not cs or "d100" in cs[0].lower() or not re.match(r"^\d", cs[0]):
            continue
        for i in range(1, len(cs), 2):
            nm = re.sub(r"\([^)]*\)", "", cs[i]).strip()   # drop "(C, DR)"-style notes
            if nm and not re.match(r"^[\d–\-]+$", nm):
                names.append(nm)
    return names


def coverage_gaps(items: dict, names: list) -> list:
    """Subtable names with no plausible description entry (best-effort match: a catalog
    name contains, or is contained by, the subtable name, word-set aware)."""
    keys = list(items)
    gaps = []
    for nm in names:
        q = _norm(re.sub(r"\s*\+\d+.*$", "", nm))          # 'Protection +1' → 'protection'
        qw = set(re.findall(r"[a-z0-9]+", q))
        if not qw:
            continue
        hit = any(q in k or k in q or qw <= set(re.findall(r"[a-z0-9]+", k))
                  for k in keys)
        if not hit:
            gaps.append(nm)
    return sorted(set(gaps))


# default clanker data dir: sibling repo …/clanker_discord/clanker/data (consumer of these)
_CLANKER_DATA = (Path(__file__).resolve().parent.parent.parent
                 / "clanker_discord" / "clanker" / "data")


def clanker_filename(catalog_filename: str) -> str:
    """Map a built catalog filename to the clanker bot's name: the bot loads
    `rc_<name>.json`, so `weapons_catalog.json` → `rc_weapons.json`,
    `equipment_catalog.json` → `rc_equipment.json`."""
    return "rc_" + catalog_filename.replace("_catalog", "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rc", type=Path,
                    default=Path(__file__).resolve().parent.parent / "docs" / "rules-cyclopedia")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent.parent / "data" / "rc")
    ap.add_argument("--clanker-data", type=Path, default=_CLANKER_DATA,
                    help="clanker bot data dir to ship catalogs into (rc_*.json)")
    ap.add_argument("--no-ship", action="store_true",
                    help="build only; do not copy catalogs into the clanker data dir")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    weapons, armor = parse_equipment_tables(args.rc)
    spells = parse_spells(args.rc)
    magic = parse_magic_items(args.rc)
    equipment = parse_general_equipment(args.rc)

    outputs = {
        "weapons_catalog.json": weapons,
        "armor_catalog.json": armor,
        "spells_catalog.json": spells,
        "magic_items_catalog.json": magic,
        "equipment_catalog.json": equipment,
    }
    for fname, data in outputs.items():
        (args.out / fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")

    print(f"weapons: {len(weapons)}  armor: {len(armor)}  spells: {len(spells)}  "
          f"magic items: {len(magic)}  equipment: {len(equipment)}")
    gaps = coverage_gaps(magic, subtable_names(args.rc))
    if gaps:
        print(f"⚠ COVERAGE GAPS — {len(gaps)} subtable item(s) lack a description "
              f"(author/fix in the RC markdown, step 4A.0):")
        for g in gaps:
            print(f"    - {g}")
    else:
        print("coverage: every determination-subtable item has a description ✓")
    print(f"wrote → {args.out}")

    if not args.no_ship:
        if args.clanker_data.is_dir():
            for fname in outputs:
                dst = args.clanker_data / clanker_filename(fname)
                shutil.copyfile(args.out / fname, dst)
            print(f"shipped {len(outputs)} catalogs → {args.clanker_data} "
                  f"({', '.join(clanker_filename(f) for f in outputs)})")
        else:
            print(f"⚠ skip ship: clanker data dir not found ({args.clanker_data}); "
                  f"pass --clanker-data or --no-ship")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
