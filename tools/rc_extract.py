#!/usr/bin/env python3
"""Parse the converted Rules Cyclopedia markdown into deterministic JSON the
clanker bot looks up at runtime — monster stat blocks, the encumbrance→movement
bands, light-source burn times, and ammunition mappings. No LLM anywhere: this is
a build step, and lookups are exact dict access (the old "ask the game" RAG was
removed for being too slow — this replaces it with structured data).

    python tools/rc_extract.py [--rc docs/rules-cyclopedia] [--out data/rc]

Emits, under --out:
  monsters.json          {slug: {name, ac, hd_dice, hd_mod, hd_special, size, hp_dice,
                          mv, mv_run, attacks, dmg, na, save, ml, tt, int, al, xp,
                          page, source, provisional}}
  encumbrance.json       [{min_cn, max_cn|null, normal, encounter, running}]
  light.json             {torch:{turns,enc}, lantern:{turns,enc,flask_enc}}
  ammo.json              {bow:{ammo,load}, crossbow:{...}, sling:{...}}
  equipment_weights.json {item_name_lower: enc_cn}

Monster chapters A–L (files 01..08) are final; M+ (09..) are VLM-pre-drafted and
flagged provisional:true so consumers can warn. Re-run as those chapters finalize.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# ── monster stat line ─────────────────────────────────────────────────────────
# Headings look like:  "## Actaeon (Elk Centaur) — Monster (Rare), p.156"
#                       "## Gargoyle\* — Construct, Enchanted (Rare), p.178"
#                       "## Ape, Snow — Normal Animal (Rare), pp.157–158"
_HEADING = re.compile(r"^##\s+(?P<name>.+?)\s*$")
# Stat line:  "**AC** 3 · **HD** 11\*\* (L) · **MV** 150' (50') · … · **XP** 2,700"
_STAT_HINT = re.compile(r"^\*\*AC\*\*")
_FIELD = re.compile(r"\*\*(?P<key>AC|HD|MV|#AT|Dmg|NA|Save|ML|TT|Int|AL|XP)\*\*\s*(?P<val>.*?)\s*(?=·\s*\*\*|$)")
_PAGE = re.compile(r"pp?\.\s*(\d+)")

# HD: leading "11" / "3+1" / "1/2" / "1−1" / "2", optional ±mod, asterisks count the
# special abilities (they bump XP). Unicode minus (−) and en-dash appear in source.
_HD = re.compile(
    r"^\s*(?P<dice>\d+(?:/\d+)?)\s*(?P<mod>[+\-−]\s*\d+)?\s*(?P<stars>\*+)?")
_SIZE = re.compile(r"\(([SML])(?:[–-][SML])?\)")
_INT = re.compile(r"-?\d[\d,]*")


def _norm_minus(s: str) -> str:
    return s.replace("−", "-").replace("–", "-")  # unicode minus / en-dash → ascii


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or name.lower()


def _clean_name(raw: str) -> str:
    """Heading text → bare monster name: drop the trailing '— category, p.NN',
    the parenthetical alt-name, and the '\\*' needs-magic-weapon marker."""
    name = raw.split("—")[0].strip()
    name = re.sub(r"\\?\*+$", "", name).strip()        # trailing asterisk marker
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()  # "(Elk Centaur)"
    return name


def _first_int(s: str):
    m = _INT.search(s or "")
    return int(m.group(0).replace(",", "")) if m else None


def _parse_hd(val: str) -> dict:
    """'11\\*\\* (L)' → {hd_dice:11, hd_mod:0, hd_special:2, size:'L',
    hp_dice:'11d8', hd_variable:False}. Fractional '1/2' → hd_dice None, hp '1d4'.
    Range/variable HD ('8, 12, or 16', '4** to 15****', '1 or more', 'see below')
    → hd_variable:True (XP is not a single value for these)."""
    s = val.replace("\\", "")
    size_m = _SIZE.search(s)
    size = size_m.group(1) if size_m else None
    core = re.sub(r"\([^)]*\)", " ", s)                # drop (L) / (1–4 hp) / (M–L)
    nums = re.findall(r"\d+(?:/\d+)?", core)
    is_fraction = bool(re.match(r"\s*1/[0-9]", core))  # ½ / ¼ HD, not a range
    # A dash between two numbers whose 2nd is larger is a RANGE (variable HD:
    # '1–4', '5–12', '3**–7**'); an equal/smaller 2nd is a minus modifier ('1−1').
    rng = re.search(r"(\d+)\s*\**\s*[–\-−]\s*\**\s*(\d+)", core)
    is_range = bool(rng) and int(rng.group(2)) > int(rng.group(1))
    variable = (is_range
                or ("/" in core and not is_fraction)   # '7**/8**/9**' variants
                or ("," in core and len(nums) > 1)      # '8, 12, or 16'
                or bool(re.search(r"\bto\b|\bor\b|see|per|special|table", core, re.I)))
    stars = s.count("*")                               # asterisks anywhere in the HD
    m = _HD.match(core.replace("−", "-").strip())      # minus (U+2212) → ascii for the mod
    if not m:
        return {"hd_dice": None, "hd_mod": 0, "hd_special": stars,
                "size": size, "hp_dice": None, "hd_variable": True}
    dice_s = m.group("dice")
    mod = int(re.sub(r"\s+", "", m.group("mod"))) if m.group("mod") else 0
    if "/" in dice_s:                                  # fractional HD (½) → 1d4 hp
        hd_dice, hp_dice = None, "1d4"
    else:
        hd_dice = int(dice_s)
        hp_dice = f"{hd_dice}d8" + (f"+{mod}" if mod > 0 else f"{mod}" if mod else "")
    return {"hd_dice": hd_dice, "hd_mod": mod, "hd_special": stars,
            "size": size, "hp_dice": hp_dice, "hd_variable": variable}


def _parse_stat_line(line: str) -> dict:
    fields = {m.group("key"): m.group("val").strip()
              for m in _FIELD.finditer(line)}
    if "AC" not in fields:
        return {}
    out: dict = {
        "ac": _first_int(fields.get("AC", "")),
        "mv": _first_int(fields.get("MV", "")),
        "mv_run": None,
        "attacks": fields.get("#AT"),
        "dmg": fields.get("Dmg"),
        "na": fields.get("NA"),
        "save": fields.get("Save"),
        "ml": _first_int(fields.get("ML", "")),
        "tt": fields.get("TT"),
        "int": _first_int(fields.get("Int", "")),
        "al": fields.get("AL"),
        "xp": _first_int(fields.get("XP", "")),
    }
    mv_paren = re.search(r"\((\d+)'?\)", fields.get("MV", ""))
    if mv_paren:
        out["mv_run"] = int(mv_paren.group(1))
    out.update(_parse_hd(fields.get("HD", "")))
    return out


def parse_monsters(rc: Path) -> dict:
    mons: dict = {}
    files = sorted((rc / "14-monsters").glob("[0-9][0-9]-monsters-*.md"))
    for fp in files:
        provisional = fp.name >= "09-monsters-m.md"     # A–L final; M+ pre-drafted
        lines = fp.read_text(encoding="utf-8").splitlines()
        pending = None
        i = 0
        while i < len(lines):
            ln = lines[i]
            h = _HEADING.match(ln)
            if h:
                pending = h.group("name")
                i += 1
                continue
            if pending and _STAT_HINT.match(ln):
                # The stat block wraps across several physical lines (until a blank
                # line): "**AC** 3 · **HD** … · **#AT** 2 spears/1 antler or\nbreath
                # (special) · **Dmg** … · **Save** C11 ·\n**ML** 10 · … · **XP** 2,700".
                block = [ln]
                j = i + 1
                while j < len(lines) and lines[j].strip():
                    block.append(lines[j])
                    j += 1
                stat = _parse_stat_line(" ".join(block))
                if stat:
                    name = _clean_name(pending)
                    slug = _slug(name)
                    pm = _PAGE.search(pending)
                    if slug not in mons:                # first stat line wins
                        mons[slug] = {"name": name,
                                      "page": int(pm.group(1)) if pm else None,
                                      "source": fp.name, "provisional": provisional,
                                      **stat}
                pending = None
                i = j
                continue
            i += 1
    return mons


# ── encumbrance → movement bands (06-movement.md) ─────────────────────────────
def parse_encumbrance(rc: Path) -> list:
    text = (rc / "06-movement" / "06-movement.md").read_text(encoding="utf-8")
    bands = []
    # rows like "| 0–400 | 120 | 40 | 120 |" and "| 2,401+ | 0 | 0 | 0 |"
    row = re.compile(
        r"^\|\s*([\d,]+)\s*(?:[–-]\s*([\d,]+)|\+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        re.M)
    for m in row.finditer(_norm_minus(text)):
        lo = int(m.group(1).replace(",", ""))
        hi = int(m.group(2).replace(",", "")) if m.group(2) else None
        bands.append({"min_cn": lo, "max_cn": hi, "normal": int(m.group(3)),
                      "encounter": int(m.group(4)), "running": int(m.group(5))})
    return bands


# ── light + ammo + gear weights (04-equipment.md) ─────────────────────────────
def parse_equipment(rc: Path) -> tuple[dict, dict, dict]:
    text = (rc / "04-equipment" / "04-equipment.md").read_text(encoding="utf-8")
    light = {
        "torch": {"turns": 6, "enc": 20, "radius_ft": 30},     # 1 hour (book p.68)
        "lantern": {"turns": 24, "enc": 30, "flask_enc": 10, "radius_ft": 30},
    }
    # cross-check torch/lantern turn counts against the prose so a source edit is caught
    if not re.search(r"torch[^.]*\b6\s+turns\b", text, re.I):
        light["torch"]["_unconfirmed"] = True
    if not re.search(r"lantern[^.]*\b24\s*\n?\s*turns\b|4 hours \(24", text, re.I):
        light["lantern"]["_unconfirmed"] = True

    ammo = {}
    # "| Bow | Arrow | 20 | 5 | 2 |"  (Weapon | Ammunition | Standard Load | …)
    ammo_row = re.compile(
        r"^\|\s*(Bow|Crossbow|Sling)\s*\|\s*([A-Za-z][\w \-]*?)\s*\|\s*(\d+)\s*\|", re.M)
    for m in ammo_row.finditer(text):
        weapon = m.group(1).lower()
        if weapon in ammo:                              # first (standard) ammo wins
            continue
        ammo[weapon] = {"ammo": m.group(2).strip().lower(), "load": int(m.group(3))}

    weights: dict = {}
    # Walk every markdown table; in any table whose header has an "Enc (cn)" column,
    # read each data row's name (col 0) and that column's integer cn.
    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    rows = text.splitlines()
    k = 0
    while k < len(rows):
        line = rows[k]
        if line.lstrip().startswith("|") and "enc" in line.lower():
            hdr = [c.lower() for c in cells(line)]
            enc_col = next((idx for idx, c in enumerate(hdr) if "enc" in c), None)
            # The name is in col 0 for most tables (Weapons, Gear), but the Armor and
            # Barding tables put the AC *number* in col 0 and the name in an
            # "Armor Type" column. Key by the name column, not col 0, or armor weights
            # come out keyed by their AC number ("7","3",…) and are useless.
            name_col = next((idx for idx, c in enumerate(hdr)
                             if any(key in c for key in
                                    ("item", "name", "armor type", "weapon", "animal"))), 0)
            k += 1
            if k < len(rows) and set(rows[k].strip()) <= set("|-: "):  # separator row
                k += 1
            while k < len(rows) and rows[k].lstrip().startswith("|") and enc_col is not None:
                cs = cells(rows[k])
                if len(cs) > max(name_col, enc_col):
                    name = re.sub(r"\\?\*+", "", cs[name_col]).strip().lower()
                    cn = _first_int(re.sub(r"\\?\*+", "", cs[enc_col]))
                    # Bold group-header rows ("| **Axes** | | | | |") have an empty enc
                    # cell → cn is None → skipped here.
                    if cn is not None and name:
                        weights.setdefault(name, cn)
                k += 1
            continue
        k += 1
    return light, ammo, weights


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rc", type=Path,
                    default=Path(__file__).resolve().parent.parent / "docs" / "rules-cyclopedia")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent.parent / "data" / "rc")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    monsters = parse_monsters(args.rc)
    encumbrance = parse_encumbrance(args.rc)
    light, ammo, weights = parse_equipment(args.rc)

    outputs = {
        "monsters.json": monsters,
        "encumbrance.json": encumbrance,
        "light.json": light,
        "ammo.json": ammo,
        "equipment_weights.json": weights,
    }
    for fname, data in outputs.items():
        (args.out / fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")

    prov = sum(1 for m in monsters.values() if m["provisional"])
    print(f"monsters: {len(monsters)} ({len(monsters)-prov} final, {prov} provisional)")
    print(f"encumbrance bands: {len(encumbrance)}  ammo: {list(ammo)}  "
          f"gear weights: {len(weights)}")
    print(f"light: {light}")
    print(f"wrote → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
