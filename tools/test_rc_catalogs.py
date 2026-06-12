"""Guard the RC catalog extractor: assert known BECMI weapon/armor/spell/magic-item
values survive parsing, and that every determination-subtable magic item has a
description (the 4A.0 coverage gate). Run from the repo root: python -m pytest tools/
"""
from pathlib import Path

import rc_catalogs

RC = Path(__file__).resolve().parent.parent / "docs" / "rules-cyclopedia"


def test_weapons_catalog():
    w, _armor = rc_catalogs.parse_equipment_tables(RC)
    assert w["dagger, normal"]["damage"] == "1d4"
    assert w["dagger, normal"]["range"] == "10/20/30"
    assert w["sword, normal"]["damage"] == "1d8" and w["sword, normal"]["enc"] == 60
    assert w["bow, long"]["range"] == "70/140/210"
    # group-header rows ("**Axes**") must not leak in
    assert "axes" not in w and "" not in w


def test_armor_catalog():
    _w, a = rc_catalogs.parse_equipment_tables(RC)
    assert a["plate mail"]["ac"] == 3 and a["plate mail"]["enc"] == 500
    assert a["leather armor"]["ac"] == 7
    assert a["chain mail"]["ac"] == 5
    assert a["shield"]["ac"] == -1                     # AC (−1)


def test_spells_catalog():
    s = rc_catalogs.parse_spells(RC)
    assert s["fireball"]["level"] == 3 and s["fireball"]["class"] == "mu"
    assert s["fireball"]["range"] == "240'"
    assert s["cure light wounds"]["class"] == "cleric" and s["cure light wounds"]["level"] == 1
    assert s["charm person"]["level"] == 1
    assert s["charm person"]["effect"]                 # non-empty effect/desc
    assert s["charm person"]["desc"]


def test_magic_items_catalog():
    m = rc_catalogs.parse_magic_items(RC)
    bag = m["bag of holding"]
    assert bag["category"] == "misc" and "10,000 cn" in bag["desc"]
    # rings carry their full description
    assert any(k.startswith("protection") for k in m)
    assert m["fire resistance"]["category"] in ("ring", "potion")
    assert m["fire resistance"]["desc"]


def test_coverage_no_gaps():
    """Every determination-subtable item has a description (Gemini RC conversion)."""
    m = rc_catalogs.parse_magic_items(RC)
    gaps = rc_catalogs.coverage_gaps(m, rc_catalogs.subtable_names(RC))
    assert gaps == [], f"subtable items lacking a description: {gaps}"
