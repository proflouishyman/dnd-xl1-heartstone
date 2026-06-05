#!/usr/bin/env python3
"""gen_manifest.py — emit api/manifest.json from the canonical CHARACTERS data.

dnd-api needs each character's *base* (pre-rolled) values to render the homepage
roster and to resolve a renamed character back to its immutable id, merging the
player's overrides on top. We derive them from generate_sheets.CHARACTERS — the
single source of truth — so the manifest never drifts from the sheets. Importing
generate_sheets is side-effect-free thanks to its __main__ guard (no image work).

Run after editing CHARACTERS; commit the resulting api/manifest.json (it's baked
into the api image).
"""
import json
import os

from generate_sheets import CHARACTERS

OUT = os.path.join("api", "manifest.json")


def main():
    manifest = {}
    for c in CHARACTERS:
        slug = c["name"].lower()
        manifest[slug] = {
            "id": slug,
            "name": c["name"].title(),          # display name; slug/id stays name.lower()
            "epithet": c.get("epithet", ""),
            "class_level": c.get("class_level", ""),
            "race": c.get("race", ""),
            "alignment": c.get("alignment", ""),
            "save_as": c.get("save_as", ""),
            "languages": ", ".join(c.get("languages", [])),
        }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT} — {len(manifest)} characters")


if __name__ == "__main__":
    main()
