#!/usr/bin/env python3
"""
Generate interactive fog-of-war HTML map pages.
DM clicks tiles to reveal; state saved to localStorage per map.
"""

import os
os.makedirs("maps", exist_ok=True)

MAPS = [
    {
        "slug":  "northern-marsh",
        "title": "Map 1 — Mists of the Northern Marsh",
        "sub":   "Wilderness · Cave Openings 2a–2f",
        "desc":  "Marsh trail, quicksand, four stone bridges. Random encounters every 4 hours. Watch for hobgoblin scouts fleeing toward the mountains.",
        "img":   "northern-marsh.jpg",
        "cols":  18, "rows": 24,
    },
    {
        "slug":  "icewater-falls",
        "title": "Map 2 — Perils of the Icewater Falls",
        "sub":   "Wilderness · Cliff Face",
        "desc":  "The cliff riddled with cave openings. Scale: 1 inch = 20 feet. Hobgoblins flee through here — time the approach carefully.",
        "img":   "icewater-falls.jpg",
        "cols":  16, "rows": 22,
    },
    {
        "slug":  "tunnels-of-death",
        "title": "Map 3 — The Tunnels of Death",
        "sub":   "Dungeon Level I",
        "desc":  "Natural caverns carved into passages. Scale: 1 square = 10 feet. Ghouls, troglodytes, and worse await in the dark.",
        "img":   "tunnels-of-death.jpg",
        "cols":  26, "rows": 32,
    },
    {
        "slug":  "frost-giants-lair",
        "title": "Map 4 — Frost Giants' Lair",
        "sub":   "Dungeon Level II",
        "desc":  "The frost giants hold this level. Connects to Level I via Area 11, and down to Level III via trapdoor.",
        "img":   "frost-giants-lair.jpg",
        "cols":  20, "rows": 26,
    },
    {
        "slug":  "wizards-home",
        "title": "Map 5 — The Wizard's Home",
        "sub":   "Dungeon Level III",
        "desc":  "Dahnakriss's tower. Area 15 leads back up to Level II. The lower passages drop to Level IV.",
        "img":   "wizards-home.jpg",
        "cols":  22, "rows": 30,
    },
    {
        "slug":  "home-of-heartstone",
        "title": "Map 6 — Home of the Heartstone",
        "sub":   "Dungeon Level IV",
        "desc":  "The deepest sanctum. The Heartstone is here — and so is Dahnakriss. Enter from Area 54 on Level III.",
        "img":   "home-of-heartstone.jpg",
        "cols":  20, "rows": 26,
    },
]

TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — XL-1</title>
<style>
  :root {{
    --gold:  #c9a84c;
    --dark:  #0e0d0b;
    --panel: #1a1710;
    --border:#3a3020;
    --text:  #e8dfc8;
    --muted: #8a7d60;
    --fog:   rgba(12,11,9,0.92);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--dark); color: var(--text); font-family: Georgia, serif; min-height: 100vh; }}

  header {{
    background: #111008;
    border-bottom: 1px solid var(--border);
    padding: 10px 16px;
    display: flex; align-items: center; gap: 16px;
    position: sticky; top: 0; z-index: 200;
  }}
  .back {{ color: var(--gold); text-decoration: none; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; white-space: nowrap; }}
  .back:hover {{ text-decoration: underline; }}
  .header-text h1  {{ font-size: 16px; color: #fff; }}
  .header-text p   {{ font-size: 11px; color: var(--muted); }}

  .toolbar {{
    display: flex; align-items: center; gap: 8px;
    padding: 8px 16px;
    background: #181410;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }}
  .toolbar span {{ font-size: 11px; color: var(--muted); margin-right: 4px; }}
  button {{
    padding: 5px 12px; font-size: 11px; border: 1px solid var(--border);
    border-radius: 4px; cursor: pointer; background: var(--panel); color: var(--text);
    transition: border-color 0.15s, background 0.15s;
  }}
  button:hover {{ border-color: var(--gold); background: #252010; color: var(--gold); }}
  button.active {{ background: #c0392b; border-color: #c0392b; color: #fff; }}
  #reveal-count {{ font-size: 11px; color: var(--muted); margin-left: auto; }}

  /* map wrapper */
  .map-wrapper {{
    position: relative;
    display: inline-block;
    margin: 12px;
  }}
  #map-img {{
    display: block;
    max-width: calc(100vw - 24px);
    height: auto;
    user-select: none;
  }}

  /* fog grid — absolutely positioned over the image */
  #fog-grid {{
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-columns: repeat({cols}, 1fr);
    grid-template-rows:    repeat({rows}, 1fr);
    pointer-events: none; /* tiles get their own events */
  }}
  .fog-tile {{
    background: var(--fog);
    border: 1px solid rgba(255,255,255,0.03);
    cursor: pointer;
    pointer-events: all;
    transition: background 0.12s;
  }}
  .fog-tile.revealed {{ background: transparent; border-color: transparent; pointer-events: all; }}
  .fog-tile:hover:not(.revealed) {{ background: rgba(40,30,10,0.75); }}
  .fog-tile.revealed:hover {{ background: rgba(200,160,76,0.15); }}

  /* DM mode: revealed tiles show a faint re-hide hint */
  body.dm-mode .fog-tile.revealed {{ border: 1px dashed rgba(200,160,76,0.2); }}
</style>
</head>
<body class="dm-mode">

<header>
  <a class="back" href="../index.html">← Hub</a>
  <div class="header-text">
    <h1>{title}</h1>
    <p>{sub}</p>
  </div>
</header>

<div class="toolbar">
  <span>DM Controls:</span>
  <button id="btn-reveal-all" onclick="revealAll()">Reveal All</button>
  <button id="btn-reset"      onclick="resetFog()">Reset Fog</button>
  <button id="btn-dm-toggle"  onclick="toggleDM()" class="active">DM Mode ON</button>
  <span id="reveal-count"></span>
</div>

<div class="map-wrapper" id="map-wrapper">
  <img id="map-img" src="{img}" alt="{title}" draggable="false">
  <div id="fog-grid"></div>
</div>

<script>
  const SLUG    = '{slug}';
  const COLS    = {cols};
  const ROWS    = {rows};
  const TOTAL   = COLS * ROWS;
  const STORE_KEY = 'fog_' + SLUG;

  let dmMode   = true;
  let isDragging = false;
  let dragReveal = true; // reveal or hide during drag
  let revealed = new Set();

  // ── Load saved state ──────────────────────────────────────────────────────
  function loadState() {{
    try {{
      const saved = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
      if (Array.isArray(saved)) revealed = new Set(saved);
    }} catch(e) {{}}
  }}
  function saveState() {{
    localStorage.setItem(STORE_KEY, JSON.stringify([...revealed]));
  }}

  // ── Build grid ────────────────────────────────────────────────────────────
  function buildGrid() {{
    const grid = document.getElementById('fog-grid');
    grid.innerHTML = '';
    for (let i = 0; i < TOTAL; i++) {{
      const tile = document.createElement('div');
      tile.className = 'fog-tile' + (revealed.has(i) ? ' revealed' : '');
      tile.dataset.i = i;
      grid.appendChild(tile);
    }}
    updateCount();
  }}

  // ── Tile interaction ──────────────────────────────────────────────────────
  function toggleTile(tile) {{
    const i = +tile.dataset.i;
    if (revealed.has(i)) {{
      revealed.delete(i);
      tile.classList.remove('revealed');
    }} else {{
      revealed.add(i);
      tile.classList.add('revealed');
    }}
    updateCount();
    saveState();
  }}

  function setTile(tile, reveal) {{
    const i = +tile.dataset.i;
    if (reveal && !revealed.has(i)) {{
      revealed.add(i);
      tile.classList.add('revealed');
      updateCount();
    }} else if (!reveal && revealed.has(i)) {{
      revealed.delete(i);
      tile.classList.remove('revealed');
      updateCount();
    }}
  }}

  // ── Grid events (click + drag) ────────────────────────────────────────────
  const grid = document.getElementById('fog-grid');

  grid.addEventListener('mousedown', (e) => {{
    const tile = e.target.closest('.fog-tile');
    if (!tile) return;
    isDragging = true;
    dragReveal = !revealed.has(+tile.dataset.i); // first tile determines mode
    toggleTile(tile);
    e.preventDefault();
  }});

  grid.addEventListener('mousemove', (e) => {{
    if (!isDragging) return;
    const tile = e.target.closest('.fog-tile');
    if (tile) setTile(tile, dragReveal);
  }});

  window.addEventListener('mouseup', () => {{ isDragging = false; saveState(); }});

  // Touch support
  grid.addEventListener('touchstart', (e) => {{
    const touch = e.touches[0];
    const tile = document.elementFromPoint(touch.clientX, touch.clientY)?.closest('.fog-tile');
    if (tile) {{ toggleTile(tile); e.preventDefault(); }}
  }}, {{ passive: false }});

  grid.addEventListener('touchmove', (e) => {{
    const touch = e.touches[0];
    const tile = document.elementFromPoint(touch.clientX, touch.clientY)?.closest('.fog-tile');
    if (tile) {{ setTile(tile, dragReveal); e.preventDefault(); }}
  }}, {{ passive: false }});

  // ── Toolbar buttons ───────────────────────────────────────────────────────
  function revealAll() {{
    document.querySelectorAll('.fog-tile').forEach(t => {{
      revealed.add(+t.dataset.i);
      t.classList.add('revealed');
    }});
    updateCount(); saveState();
  }}

  function resetFog() {{
    if (!confirm('Reset all fog? This cannot be undone.')) return;
    revealed.clear();
    document.querySelectorAll('.fog-tile').forEach(t => t.classList.remove('revealed'));
    updateCount(); saveState();
  }}

  function toggleDM() {{
    dmMode = !dmMode;
    document.body.classList.toggle('dm-mode', dmMode);
    const btn = document.getElementById('btn-dm-toggle');
    btn.textContent = dmMode ? 'DM Mode ON' : 'DM Mode OFF';
    btn.classList.toggle('active', dmMode);
    // In player mode, revealed tiles are fully invisible (no hover hints)
    document.querySelectorAll('.fog-tile.revealed').forEach(t => {{
      t.style.pointerEvents = dmMode ? 'all' : 'none';
    }});
  }}

  function updateCount() {{
    document.getElementById('reveal-count').textContent =
      revealed.size + ' / ' + TOTAL + ' tiles revealed';
  }}

  // ── Init ──────────────────────────────────────────────────────────────────
  loadState();
  buildGrid();
</script>
</body>
</html>
"""

for m in MAPS:
    html = TEMPLATE.format(**m)
    path = os.path.join("maps", f"{m['slug']}.html")
    with open(path, "w") as f:
        f.write(html)
    print(f"  {path}  ({m['cols']}×{m['rows']} = {m['cols']*m['rows']} tiles)")

print("Done")
