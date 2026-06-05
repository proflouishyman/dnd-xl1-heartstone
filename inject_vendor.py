#!/usr/bin/env python3
"""inject_vendor.py — make the served pages CDN-free (hermetic build).

Rewrites the only external asset references on the site to the local copies that
vendor_assets.sh snapshots into assets/, and points the maps' PeerJS client at
the self-hosted broker peer.haldo.org instead of the public 0.peerjs.com:

  - maps/*.html        unpkg peerjs <script>      → /assets/vendor/peerjs.min.js
                       Peer host '0.peerjs.com'   → 'peer.haldo.org'
  - patriarch-map.html Google Fonts <link>        → /assets/fonts/caveat.css

Plain-string replace, idempotent (a no-op once rewritten), like the sibling
inject scripts. Re-run after generate_* / the other inject_* steps.
"""
import glob

REPLACEMENTS = {
    "maps": [
        ('<script src="https://unpkg.com/peerjs@1.5.4/dist/peerjs.min.js"></script>',
         '<script src="/assets/vendor/peerjs.min.js"></script>'),
        ("host: '0.peerjs.com'", "host: 'peer.haldo.org'"),
    ],
    "patriarch": [
        ('<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&display=swap" rel="stylesheet">',
         '<link href="/assets/fonts/caveat.css" rel="stylesheet">'),
    ],
}


def rewrite(path, repls):
    h = open(path, encoding="utf-8").read()
    n = 0
    for old, new in repls:
        n += h.count(old)
        h = h.replace(old, new)
    if n:
        with open(path, "w", encoding="utf-8") as f:
            f.write(h)
    return n


def main():
    total = 0
    for p in sorted(glob.glob("maps/*.html")):
        n = rewrite(p, REPLACEMENTS["maps"])
        total += n
        print(f"  {p}: {n} rewrite(s)")
    n = rewrite("patriarch-map.html", REPLACEMENTS["patriarch"])
    total += n
    print(f"  patriarch-map.html: {n} rewrite(s)")
    print(f"\nDone — {total} rewrites.")


if __name__ == "__main__":
    main()
