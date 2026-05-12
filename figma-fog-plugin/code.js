// D&D Fog of War plugin
// Covers a selected map image with a grid of removable fog tiles.
// DM deletes individual tiles to reveal rooms as players explore.

figma.showUI(__html__, { width: 260, height: 270 });

const FOG_GROUP_NAME = '🌫️ Fog of War';
const FOG_TILE_NAME = 'fog-tile';

figma.ui.onmessage = async (msg) => {
  if (msg.type === 'add-fog') {
    await addFog(msg.cols, msg.rows, msg.opacity);
  } else if (msg.type === 'reveal-all') {
    revealAll();
  } else if (msg.type === 'remove-fog') {
    removeFog();
  }
};

async function addFog(cols, rows, opacity) {
  const sel = figma.currentPage.selection;
  if (sel.length === 0) {
    figma.notify('Select the map image first, then click Add Fog.', { error: true });
    return;
  }

  const target = sel[0];
  const { x, y, width, height } = target;

  // Remove any existing fog group on this page first
  removeFogFromPage();

  await figma.loadFontAsync({ family: 'Inter', style: 'Regular' });

  const group = figma.createFrame();
  group.name = FOG_GROUP_NAME;
  group.x = x;
  group.y = y;
  group.resize(width, height);
  group.fills = [];
  group.clipsContent = false;
  // Place the fog frame directly above the map in z-order
  figma.currentPage.appendChild(group);

  const tileW = width / cols;
  const tileH = height / rows;

  // Dark fog color — matches classic dungeon darkness
  const fogColor = { r: 0.08, g: 0.08, b: 0.12 };

  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const tile = figma.createRectangle();
      tile.name = FOG_TILE_NAME;
      tile.x = col * tileW;
      tile.y = row * tileH;
      tile.resize(tileW + 0.5, tileH + 0.5); // slight overlap to avoid gaps
      tile.fills = [{ type: 'SOLID', color: fogColor, opacity }];
      tile.strokeWeight = 0;
      group.appendChild(tile);
    }
  }

  figma.currentPage.selection = [group];
  figma.viewport.scrollAndZoomIntoView([target, group]);
  figma.notify(`Fog added: ${cols * rows} tiles. Select tiles and delete to reveal.`);
}

function revealAll() {
  const group = findFogGroup();
  if (!group) {
    figma.notify('No fog layer found on this page.', { error: true });
    return;
  }
  // Make all tiles transparent so everything is visible
  for (const tile of group.children) {
    if (tile.name === FOG_TILE_NAME && 'fills' in tile) {
      tile.fills = tile.fills.map(f => ({ ...f, opacity: 0 }));
    }
  }
  figma.notify('All fog revealed.');
}

function removeFog() {
  const removed = removeFogFromPage();
  if (removed) {
    figma.notify('Fog layer removed.');
  } else {
    figma.notify('No fog layer found.', { error: true });
  }
}

function findFogGroup() {
  return figma.currentPage.children.find(n => n.name === FOG_GROUP_NAME) ?? null;
}

function removeFogFromPage() {
  const group = findFogGroup();
  if (group) {
    group.remove();
    return true;
  }
  return false;
}
