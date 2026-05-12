# SOLUTIONS.md

## Bug Fixes and Notable Changes

---

[2026-05-12] - Rules link not visible to user
Problem
User added rules.html and a nav link in index.html but could not see the link in any browser, including a fresh browser with no cache.
Root Cause
The site is hosted on GitHub Pages (https://github.com/proflouishyman/dnd-xl1-heartstone). Changes to local files are not reflected until committed and pushed. All changes (rules.html, index.html, character sheets) were only local — GitHub Pages served the old committed version.
Solution
Committed and pushed all changes: rules.html (new), index.html (Rules nav link), and all 19 character sheet HTML files (Base/Equipped columns).
Notes
Always push after making visible changes. GitHub Pages serves from the main branch HEAD, not from the local filesystem.

---

[2026-05-12] - Character sheet saving throw values incorrect
Problem
The original character sheets had wrong saving throw values (e.g., strongheart L8 Fighter showed Thief-level saves).
Root Cause
The generate_sheets.py script used incorrect level brackets for save table lookups.
Solution
Created update_equipped_tables.py which replaces all save tables with correct Cyclopedia values (verified against docs/tsr01071 - The D&D Rules Cyclopedia 305pages.pdf), adding Base and Equipped columns.
Notes
Base values from Cyclopedia by class/level. Equipped adjusts for: STR bonus (THAC0 only), magic weapon bonus (THAC0 only), WIS 13-15 = -1 rod save, WIS 16-17 = -2 rod save, Ring of Protection = -N to all five saves.
