#!/usr/bin/env bash
# Snapshot third-party assets into the repo so the site builds AND serves with no
# CDN (requirement: hermetic build, serve everything from synapticon). Re-run to
# refresh the snapshot. The committed outputs ARE the snapshot:
#   assets/vendor/peerjs.min.js          (P2P fog-of-war signaling client)
#   assets/fonts/caveat.css + caveat-*.woff2   (patriarch map hand-drawn labels)
set -euo pipefail
cd "$(dirname "$0")"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

mkdir -p assets/vendor assets/fonts

echo "• peerjs@1.5.4 → assets/vendor/peerjs.min.js"
curl -fsSL "https://unpkg.com/peerjs@1.5.4/dist/peerjs.min.js" -o assets/vendor/peerjs.min.js
# Drop the sourceMappingURL comment so DevTools doesn't 404-fetch a map we don't ship.
sed -i '/sourceMappingURL=peerjs\.min\.js\.map/d' assets/vendor/peerjs.min.js

echo "• Caveat font → assets/fonts/"
curl -fsSL -A "$UA" \
  "https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&display=swap" \
  -o assets/fonts/caveat.css

# Download each referenced woff2 locally and rewrite the @font-face src URLs.
python3 - <<'PY'
import re, pathlib, urllib.request
css_path = pathlib.Path("assets/fonts/caveat.css")
css = css_path.read_text()
hdr = {"User-Agent": "Mozilla/5.0"}
blocks = re.findall(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*{[^}]*?url\((https://[^)]+\.woff2)\)", css, re.S)
local_for = {}
for subset, url in blocks:
    local_for.setdefault(url, f"caveat-{subset}.woff2")
for url, local in local_for.items():
    data = urllib.request.urlopen(urllib.request.Request(url, headers=hdr)).read()
    (css_path.parent / local).write_bytes(data)
    css = css.replace(url, f"/assets/fonts/{local}")
    print(f"  {local}  ({len(data)} bytes)")
css_path.write_text(css)
PY
echo "done."
