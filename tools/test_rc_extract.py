"""Guard the RC extractor against conversion drift: assert a handful of known
BECMI values survive parsing. Run from the repo root:  python -m pytest tools/

These mirror constants clanker depends on (clanker/sheet.py, rules_compact.md):
torch/lantern burn turns, the encumbrance→movement bands, ammo mapping, and a
few stable A–L monster stat blocks. If a re-OCR or markdown edit breaks the
format, one of these fails instead of the bot silently reading garbage.
"""
from pathlib import Path

import rc_extract

RC = Path(__file__).resolve().parent.parent / "docs" / "rules-cyclopedia"


def test_encumbrance_bands_match_book_p88():
    bands = rc_extract.parse_encumbrance(RC)
    assert bands[0] == {"min_cn": 0, "max_cn": 400, "normal": 120,
                        "encounter": 40, "running": 120}
    assert bands[1]["normal"] == 90 and bands[1]["max_cn"] == 800
    assert bands[-1]["min_cn"] == 2401 and bands[-1]["normal"] == 0   # 2,401+ → 0


def test_light_and_ammo():
    light, ammo, weights = rc_extract.parse_equipment(RC)
    assert light["torch"]["turns"] == 6           # 1 hour
    assert light["lantern"]["turns"] == 24         # 4 hours / flask of oil
    assert ammo["bow"]["ammo"] == "arrow"
    assert ammo["crossbow"]["ammo"] == "quarrel"
    assert ammo["sling"]["ammo"].startswith("stone")
    assert weights["torch"] == 20                  # cn
    assert weights["oil (one flask)"] == 10


def test_armor_weights_keyed_by_name_not_ac():
    """The Armor/Barding tables put the AC number in col 0 and the name in
    "Armor Type"; weights must key by the name, not the AC number."""
    _light, _ammo, weights = rc_extract.parse_equipment(RC)
    assert weights["leather armor"] == 200         # AC 7
    assert weights["chain mail"] == 400            # AC 5
    assert weights["plate mail"] == 500            # AC 3
    assert weights["shield"] == 100                # AC (−1)
    # No bare AC-number keys leaked in from col 0.
    assert not any(k.strip("()-−ï ").isdigit() for k in weights)


def test_monster_statlines_parse_across_wrapped_lines():
    mons = rc_extract.parse_monsters(RC)
    a = mons["actaeon"]                            # multi-line stat block
    assert (a["ac"], a["hd_dice"], a["hd_special"], a["size"]) == (3, 11, 2, "L")
    assert a["save"] == "C11" and a["xp"] == 2700 and a["hp_dice"] == "11d8"
    cc = mons["carrion-crawler"]                   # "3+1" HD modifier
    assert cc["hd_dice"] == 3 and cc["hd_mod"] == 1 and cc["hp_dice"] == "3d8+1"
    # A–L chapters are final; M+ flagged provisional.
    assert a["provisional"] is False
    assert any(m["provisional"] for m in mons.values())
    # Coverage sanity: the A–L set should be well over half the parsed monsters.
    final = [m for m in mons.values() if not m["provisional"]]
    assert len(final) >= 70
