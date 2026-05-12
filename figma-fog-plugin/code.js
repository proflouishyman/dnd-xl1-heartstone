// D&D Fog of War — auto-creates all 6 XL-1 maps with fog tiles.
// In "setup" mode: fetches each map from GitHub Pages, creates a Figma page
// per map, places the image, and lays a fog grid on top.
// In "manual" mode: adds fog to whatever image is currently selected.

figma.showUI(__html__, { width: 320, height: 380 });

const BASE_URL  = 'https://proflouishyman.github.io/dnd-xl1-heartstone/maps/';
const FOG_COLOR = { r: 0.08, g: 0.08, b: 0.12 };
const FOG_NAME  = '🌫️ Fog of War';
const TILE_NAME = 'fog-tile';

const MAP_CONFIGS = [
  { slug: 'northern-marsh',    title: 'Map 1 — Northern Marsh',       cols: 18, rows: 24 },
  { slug: 'icewater-falls',    title: 'Map 2 — Icewater Falls',        cols: 16, rows: 22 },
  { slug: 'tunnels-of-death',  title: 'Map 3 — Tunnels of Death',      cols: 24, rows: 30 },
  { slug: 'frost-giants-lair', title: 'Map 4 — Frost Giants\' Lair',  cols: 20, rows: 26 },
  { slug: 'wizards-home',      title: 'Map 5 — Wizard\'s Home',        cols: 22, rows: 30 },
  { slug: 'home-of-heartstone','title': 'Map 6 — Home of Heartstone', cols: 20, rows: 26 },
];

figma.ui.onmessage = async (msg) => {
  if (msg.type === 'setup-all') {
    await setupAllMaps(msg.opacity);
  } else if (msg.type === 'add-fog') {
    await addFogToSelection(msg.cols, msg.rows, msg.opacity);
  } else if (msg.type === 'reveal-all') {
    revealAll();
  } else if (msg.type === 'remove-fog') {
    removeFog();
  } else if (msg.type === 'image-data') {
    // Received image bytes from UI fetch — build the map page
    await buildMapPage(msg.config, msg.bytes, msg.opacity);
    figma.ui.postMessage({ type: 'map-done', slug: msg.config.slug });
  } else if (msg.type === 'setup-error') {
    figma.notify(`Failed to load ${msg.slug}: ${msg.error}`, { error: true });
    figma.ui.postMessage({ type: 'map-done', slug: msg.slug });
  }
};

// ── Auto-setup: request UI to fetch each map image ───────────────────────────
async function setupAllMaps(opacity) {
  figma.notify('Fetching maps from GitHub Pages…');
  figma.ui.postMessage({ type: 'fetch-maps', maps: MAP_CONFIGS, opacity });
}

// ── Build one page from received image bytes ──────────────────────────────────
async function buildMapPage(config, bytes, opacity) {
  await figma.loadFontAsync({ family: 'Inter', style: 'Regular' });

  // Create or reuse a page named after this map
  let page = figma.root.children.find(p => p.name === config.title);
  if (!page) {
    page = figma.createPage();
    page.name = config.title;
  }

  // Remove any existing content on the page
  for (const child of [...page.children]) child.remove();

  figma.currentPage = page;

  // Create the map frame with the image as fill
  const imageHash = figma.createImage(new Uint8Array(bytes)).hash;
  const frame = figma.createFrame();
  frame.name = config.title;
  frame.x = 0; frame.y = 0;
  frame.resize(2400, 3000);
  frame.fills = [{ type: 'IMAGE', imageHash, scaleMode: 'FIT' }];
  page.appendChild(frame);

  // Add fog grid frame on top
  const fogFrame = figma.createFrame();
  fogFrame.name = FOG_NAME;
  fogFrame.x = 0; fogFrame.y = 0;
  fogFrame.resize(2400, 3000);
  fogFrame.fills = [];
  fogFrame.clipsContent = false;
  page.appendChild(fogFrame);

  const tileW = 2400 / config.cols;
  const tileH = 3000 / config.rows;

  for (let row = 0; row < config.rows; row++) {
    for (let col = 0; col < config.cols; col++) {
      const tile = figma.createRectangle();
      tile.name = TILE_NAME;
      tile.x = col * tileW;
      tile.y = row * tileH;
      tile.resize(tileW + 0.5, tileH + 0.5);
      tile.fills = [{ type: 'SOLID', color: FOG_COLOR, opacity }];
      tile.strokeWeight = 0;
      fogFrame.appendChild(tile);
    }
  }

  figma.viewport.scrollAndZoomIntoView([frame, fogFrame]);
}

// ── Manual: add fog to currently selected image ───────────────────────────────
async function addFogToSelection(cols, rows, opacity) {
  const sel = figma.currentPage.selection;
  if (!sel.length) {
    figma.notify('Select the map image first.', { error: true });
    return;
  }
  await figma.loadFontAsync({ family: 'Inter', style: 'Regular' });
  removeFogFromPage();

  const { x, y, width, height } = sel[0];
  const fog = figma.createFrame();
  fog.name = FOG_NAME;
  fog.x = x; fog.y = y;
  fog.resize(width, height);
  fog.fills = [];
  fog.clipsContent = false;
  figma.currentPage.appendChild(fog);

  const tileW = width / cols;
  const tileH = height / rows;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const tile = figma.createRectangle();
      tile.name = TILE_NAME;
      tile.x = c * tileW; tile.y = r * tileH;
      tile.resize(tileW + 0.5, tileH + 0.5);
      tile.fills = [{ type: 'SOLID', color: FOG_COLOR, opacity }];
      tile.strokeWeight = 0;
      fog.appendChild(tile);
    }
  }
  figma.currentPage.selection = [fog];
  figma.notify(`Fog added — ${cols * rows} tiles. Delete tiles to reveal.`);
}

function revealAll() {
  const g = findFog();
  if (!g) { figma.notify('No fog layer.', { error: true }); return; }
  for (const t of g.children) {
    if (t.name === TILE_NAME && 'fills' in t)
      t.fills = t.fills.map(f => ({ ...f, opacity: 0 }));
  }
  figma.notify('All fog revealed.');
}

function removeFog() {
  removeFogFromPage()
    ? figma.notify('Fog removed.')
    : figma.notify('No fog layer.', { error: true });
}

function findFog()         { return figma.currentPage.children.find(n => n.name === FOG_NAME) ?? null; }
function removeFogFromPage(){ const g = findFog(); if (g) { g.remove(); return true; } return false; }
