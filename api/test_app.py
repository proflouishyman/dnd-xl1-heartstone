"""dnd-api tests. Run with the `dndapi` conda env from the repo root:
    conda run -n dndapi python -m pytest api/test_app.py -q

Covers the /characters/{id}/full XP fields added so clanker XP awards accumulate
from the real BECMI level floor instead of overwriting from 0.
"""
import os
import tempfile

os.environ.setdefault("DND_DATA_DIR", tempfile.mkdtemp(prefix="dndapi-test-"))

from fastapi.testclient import TestClient  # noqa: E402

import app  # noqa: E402

client = TestClient(app.app)


def test_full_exposes_base_xp():
    """An untouched sheet reports its BECMI level floor + next-level threshold."""
    data = client.get("/characters/mercion/full").json()   # cleric L7
    assert data["xp"] == 50_000
    assert data["xp_next"] == 100_000


def test_full_xp_override_wins():
    """A clanker-written xp override takes precedence over the base floor."""
    client.patch("/characters/mercion", json={"xp": 62_500})
    data = client.get("/characters/mercion/full").json()
    assert data["xp"] == 62_500
    # base floor still reflected for the next-level threshold
    assert data["xp_next"] == 100_000


def test_full_xp_next_none_at_max_level():
    """A character at the class table's max level has no next threshold."""
    data = client.get("/characters/ringlerun/full").json()  # mage L10 (table max)
    assert data["xp"] == 450_000
    assert data["xp_next"] is None


def test_learned_spell_listed_and_merged_into_spellbook():
    """A learned-spell override surfaces in `learned` AND joins `spells` at its level
    so the bot can cast it."""
    client.patch("/characters/kelek", json={"learn_spell_1": "Fireball", "learn_lvl_1": 3})
    data = client.get("/characters/kelek/full").json()
    assert {"slot": 1, "name": "Fireball", "level": 3} in data["learned"]
    assert "Fireball" in data["spells"].get("3", [])
    # a learned row with no level is listed but NOT merged (uncastable)
    client.patch("/characters/kelek", json={"learn_spell_2": "Mystery Cantrip"})
    data = client.get("/characters/kelek/full").json()
    assert any(l["name"] == "Mystery Cantrip" for l in data["learned"])
    flat = [s for lvl in data["spells"].values() for s in lvl]
    assert "Mystery Cantrip" not in flat


def test_magic_items_list():
    client.patch("/characters/bowmarc", json={
        "magic_item_1": "Bag of Holding",
        "magic_item_desc_1": "holds 10,000 cn", "magic_item_charges_1": 5})
    items = client.get("/characters/bowmarc/full").json()["magic_items"]
    assert items and items[0]["name"] == "Bag of Holding"
    assert items[0]["charges"] == 5 and "10,000" in items[0]["desc"]


def test_acquired_weapons_armor_appended_not_overwritten():
    base = client.get("/characters/bowmarc/full").json()
    base_weapons = list(base["weapons"])
    client.patch("/characters/bowmarc", json={"weapon_1": "War Hammer +1",
                                              "armor_1": "Cloak of Protection"})
    data = client.get("/characters/bowmarc/full").json()
    assert "War Hammer +1" in data["weapons"]
    assert all(w in data["weapons"] for w in base_weapons)   # base preserved
    assert "Cloak of Protection" in data["armor"]


def test_roster_url_avoids_static_id_collision():
    """A character renamed so its name-slug equals ANOTHER character's id must link
    to its OWN id page, not the colliding static sheet. This is the homepage-link
    bug where ringlerun renamed "Kelek" (slug "kelek") linked to /characters/kelek.html
    — the real `kelek` character (Dr. BRULE) — instead of /characters/ringlerun.html."""
    client.patch("/characters/ringlerun", json={"name": "Kelek"})   # slug "kelek" == kelek's id
    url = {c["id"]: c["url"] for c in client.get("/characters").json()["characters"]}
    assert url["ringlerun"] == "/characters/ringlerun.html"
    assert url["kelek"] != "/characters/ringlerun.html"             # the real kelek is unaffected


def test_roster_url_keeps_vanity_slug_when_no_collision():
    """A rename whose slug is NOT another character's id keeps its pretty vanity URL."""
    client.patch("/characters/bowmarc", json={"name": "Sir Bowmarc"})
    url = {c["id"]: c["url"] for c in client.get("/characters").json()["characters"]}
    assert url["bowmarc"] == "/characters/sir-bowmarc.html"
