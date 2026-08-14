#!/usr/bin/env python3
"""
Build the deployable site from the Claude Design export.

The design is the source of truth. This script never edits it — it takes
`design/BullPrint Lab Site.dc.html` exactly as exported and applies four
mechanical changes, so re-exporting the design and re-running this reproduces
the site with no hand-patching to redo:

  1. Vendors React locally. `support.js` pulls React 18.3.1 UMD off unpkg unless
     `window.React` is already set. Loading our own copies first short-circuits
     that, so the site has no third-party runtime dependency at all — which is
     the correct posture for a page whose headline is about sovereignty.
     The vendored files are SRI-verified against the exact hashes support.js
     itself pins.
  2. Repoints the two design uploads at optimised local assets (4.2 MB of PNG
     became 447 KB of WebP; the PNG originals stay in the repo).
  3. Adds the document head the design has no way to carry: title, description,
     canonical, Open Graph, Twitter card, favicon, theme colour.
  4. Self-hosts the two webfonts. The design links Google Fonts, which is the
     last third-party request on the page and a privacy dependency the brand
     line does not sit well with. Same typefaces, same weights, served from the
     same origin — so the deployed CSP can forbid external hosts outright.
  5. Nothing else. The <x-dc> template, the helmet block and every byte of the
     markup are otherwise passed through untouched.

    python3 build.py
"""
from __future__ import annotations

import base64
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "design" / "BullPrint Lab Site.dc.html"
OUT = ROOT / "index.html"

SITE = "https://bullprintlab.com"
TITLE = "BullPrint Lab — We print what we're bullish on."
DESC = ("VibePrints with real utility. BullPrint Lab experiments at the "
        "intersection of design, additive manufacturing, culture and utility — "
        "every object starts as a question about geometry and ends as something "
        "you can wear out of the house.")
OG_IMAGE = f"{SITE}/assets/insert-spec-sheet.png"

# support.js pins these; vendoring only works if the bytes match.
VENDOR_SRI = {
    "vendor/react.production.min.js":
        "sha384-DGyLxAyjq0f9SPpVevD6IgztCFlnMF6oW/XQGmfe+IsZ8TqEiDrcHkMLKI6fiB/Z",
    "vendor/react-dom.production.min.js":
        "sha384-gTGxhz21lVGYNMcdJOyq01Edg0jhn/c22nsx0kyqP0TxaV5WVdsSH1fSDUf5YJj1",
}

ASSETS = {
    "uploads/images-1786710197897-v7um.png": "assets/insert-macro-hero.webp",
    "uploads/images-1786710214318-psa4.png": "assets/insert-spec-sheet.webp",
}

# The mark, as a favicon: the ₿ in brand gold on the brand near-black.
FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="12" fill="#0B0B0D"/>'
    '<text x="32" y="45" font-family="Archivo,Helvetica,Arial,sans-serif"'
    ' font-size="42" font-weight="800" fill="#E8B23A"'
    ' text-anchor="middle">₿</text></svg>'
)

HEAD = f"""<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<link rel="canonical" href="{SITE}/">
<meta name="theme-color" content="#0B0B0D">
<meta name="color-scheme" content="dark">
<link rel="icon" href="data:image/svg+xml;base64,{{favicon}}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="BullPrint Lab">
<meta property="og:url" content="{SITE}/">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESC}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1402">
<meta property="og:image:height" content="1122">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{TITLE}">
<meta name="twitter:description" content="{DESC}">
<meta name="twitter:image" content="{OG_IMAGE}">
<script src="./vendor/react.production.min.js"></script>
<script src="./vendor/react-dom.production.min.js"></script>"""


def check_vendor() -> None:
    for rel, want in VENDOR_SRI.items():
        p = ROOT / rel
        if not p.exists():
            sys.exit(f"missing {rel} — see README, it is fetched once and committed")
        got = "sha384-" + base64.b64encode(
            hashlib.sha384(p.read_bytes()).digest()).decode()
        if got != want:
            sys.exit(f"{rel} does not match the SRI support.js pins\n"
                     f"  want {want}\n  got  {got}")
        print(f"  vendor ok  {rel}")


def main() -> None:
    if not SRC.exists():
        sys.exit(f"missing {SRC}")
    check_vendor()
    html = SRC.read_text()

    for old, new in ASSETS.items():
        n = html.count(old)
        if not n:
            sys.exit(f"asset reference not found in the design: {old}")
        html = html.replace(old, new)
        print(f"  repointed  {old} -> {new}  ({n}x)")

    # self-hosted fonts: drop the Google links, add the local stylesheet
    before = html
    html = re.sub(r'<link rel="preconnect" href="https://fonts\.gstatic\.com"[^>]*>\s*', "", html)
    html = re.sub(r'<link href="https://fonts\.googleapis\.com/[^"]*" rel="stylesheet">',
                  '<link rel="stylesheet" href="./fonts/fonts.css">', html)
    if html == before:
        sys.exit("font links not found — did the export format change?")
    print("  fonts      google links -> ./fonts/fonts.css")

    head = HEAD.replace(
        "{favicon}", base64.b64encode(FAVICON.encode()).decode())

    # React must be defined before support.js runs, so go in ahead of it.
    marker = '<script src="./support.js"></script>'
    if marker not in html:
        sys.exit("support.js script tag not found — did the export format change?")
    html = html.replace(marker, head + "\n" + marker, 1)

    OUT.write_text(html)
    print(f"  wrote      {OUT.name}  ({len(html) / 1024:.0f} KB)")

    # cheap guards against shipping something obviously broken
    for must in ("<x-dc>", "</x-dc>", "support.js", "react.production.min.js"):
        assert must in html, must
    assert "uploads/" not in html, "an upload reference survived the rewrite"
    assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html, \
        "a Google Fonts reference survived the rewrite"
    # Only SUBRESOURCES must be same-origin. Outbound links in the footer
    # (x.com, bestinbull.com) are navigation, not loads, and stay as authored.
    sub = re.findall(r'<(?:script|img)\b[^>]*\bsrc="([^"]+)"', html)
    sub += re.findall(r'<link\b[^>]*\bhref="([^"]+)"', html)
    sub += re.findall(r'url\((["\']?)(https?://[^)"\']+)', html)
    external = [u for u in sub if isinstance(u, str)
                and u.startswith(("http://", "https://"))
                and not u.startswith("https://bullprintlab.com")]
    assert not external, f"external subresource(s) survived: {external}"
    print("  checks     passed")


if __name__ == "__main__":
    main()
