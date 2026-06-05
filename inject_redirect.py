#!/usr/bin/env python3
"""inject_redirect.py — bounce GitHub Pages visitors to the canonical host.

The same HTML is served from two origins: the self-hosted https://dnd.haldo.org
(nginx, with the live dnd-api backend) and the GitHub Pages mirror at
https://proflouishyman.github.io/dnd-xl1-heartstone/ (static only — no backend,
no realtime sync). We want the Pages copy to forward to dnd.haldo.org without
needing any admin change to the repo's Pages settings.

So we bake a tiny *conditional* redirect into the top of every page's <head>:
it fires only when the hostname ends in ``github.io`` and is a no-op when the
exact same file is served from dnd.haldo.org. Because it runs synchronously
before the body parses, there's no flash of the static page.

Run as a final pipeline step over all served *.html. Plain-string/regex and
idempotent (guarded by a marker comment), like the sibling inject scripts.
"""
import glob

MARKER = "<!-- haldo-redirect -->"

SNIPPET = (
    MARKER + "\n"
    "<script>(function(){"
    "if(location.hostname.endsWith('github.io')){"
    "var p=location.pathname.replace(/^\\/dnd-xl1-heartstone/,'');"
    "location.replace('https://dnd.haldo.org'+p+location.search+location.hash);"
    "}})();</script>\n"
)

# Every page the site actually serves (the figma plugin + api/ are not served).
FILES = (
    glob.glob("*.html")
    + glob.glob("characters/*.html")
    + glob.glob("maps/*.html")
)


def main():
    for path in sorted(FILES):
        with open(path, encoding="utf-8") as f:
            h = f.read()
        if MARKER in h:
            continue
        # Insert immediately after the opening <head> so it runs as early as
        # possible — before any content, styles, or scripts.
        new = h.replace("<head>", "<head>\n" + SNIPPET, 1)
        if new == h:
            print(f"skip (no <head>): {path}")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"redirect injected: {path}")


if __name__ == "__main__":
    main()
