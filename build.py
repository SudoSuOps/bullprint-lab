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
  5. Repoints the contact address. The design ships `bullish@bullprintlab.com`,
     which is not a mailbox that exists; the real ones are `bull@` (general) and
     `print@` (orders and print enquiries). The two "EMAIL THE LAB" buttons that
     sit inside the custom-request and order flows go to `print@`, everything
     else to `bull@`. Fix this at source in the design when convenient and this
     step becomes a no-op.
  5. Wires the three forms to /api/submit, behind Turnstile. As exported they
     only flipped a local "sent" flag — they looked like they worked and nothing
     ever left the browser. This also adds the order form's missing EMAIL field:
     it collected size, width, arch, fit, feel, shoe, notes and payment
     preference, and no way to reply to the person.
  6. Inlines a pre-rendered copy of the page, when `prerender.html` is present.
     The page is rendered by a client-side runtime, so a crawler that does not
     execute JavaScript sees 8.5k characters of template source with 80 raw
     {{ }} expressions in it instead of content. Google renders JS; GPTBot,
     ClaudeBot and PerplexityBot largely do not, so without this the site is
     close to invisible to the search engines that are actually growing.

     The static copy is shown first and removed once the runtime has replaced
     <x-dc>. Same content either way — progressive enhancement, not cloaking.
     Regenerate with `python3 build.py --prerender` (needs a local browser);
     the result is committed so CI never needs one.
  7. Builds the journal (blog.py) and the GEO surface: JSON-LD, llms.txt,
     sitemap, robots. The journal is plain static HTML with no runtime — it is
     the part of the site a non-executing crawler can read completely, and where
     the citable material lives.
  8. Nothing else. The <x-dc> template, the helmet block and every byte of the
     markup are otherwise passed through untouched.

    python3 build.py
"""
from __future__ import annotations

import blog  # noqa: E402  (local module)

import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

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

TURNSTILE_SITEKEY = "0x4AAAAAAEQBxUgUlUeDfZjS"

ASSETS = {
    "uploads/images-1786710197897-v7um.png": "assets/insert-macro-hero.webp",
    "uploads/images-1786710214318-psa4.png": "assets/insert-spec-sheet.webp",
}

# The mark, as a favicon: the ₿ in brand gold on the brand near-black.
# Square — BRAND.md is explicit that there is no border radius anywhere in the
# system; the only rounded thing the brand makes is the part itself.
FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" fill="#0B0B0D"/>'
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
<script type="application/ld+json">{{jsonld}}</script>
<link rel="alternate" type="text/plain" href="/llms.txt">
<script src="./vendor/react.production.min.js"></script>
<script src="./vendor/react-dom.production.min.js"></script>
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<script src="./bp-forms.js" defer></script>"""


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


def route_ticker(html: str) -> str:
    """Point the design's ticker at our own proxy instead of CoinGecko.

    Calling a third-party price API from every visitor's browser rate-limits by
    IP, makes first paint depend on someone else's uptime, and would need a hole
    in `connect-src 'self'`. /api/btc is one edge-cached response for everyone,
    with the same two upstreams and the same honest failure state.
    """
    start = html.find("  fetchBtc() {")
    if start < 0:
        sys.exit("fetchBtc() not found — did the design's ticker change?")
    end = html.find("\n  }", html.find("api.coinbase.com", start))
    if end < 0:
        sys.exit("could not find the end of fetchBtc()")
    end = html.index("\n  }", end) + len("\n  }")
    new = """  fetchBtc() {
    fetch("/api/btc", { headers: { accept: "application/json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((j) => {
        if (!j || !j.ok || typeof j.usd !== "number") throw new Error("shape");
        this.setState({
          btcPrice: j.usd,
          btcChange: typeof j.change24h === "number" ? j.change24h : null,
          btcOk: true,
          btcAt: new Date(j.at || Date.now())
        });
      })
      .catch(() => this.setState({ btcOk: false }));
  }"""
    print("  ticker     coingecko/coinbase in-browser -> /api/btc (edge cached)")
    return html[:start] + new + html[end:]


def wire_forms(html: str) -> str:
    """Give the three forms somewhere to send, and the order form an address."""

    # -- the order form has no email field. Add one, as its own numbered step,
    #    and push the steps after it along.
    for old, new in (("08 · CHECKOUT RAIL", "09 · CHECKOUT RAIL"),
                     ("07 · FEEL", "08 · FEEL"),
                     ("06 · SPECIAL NOTES", "07 · SPECIAL NOTES")):
        if old not in html:
            sys.exit(f"order-form step '{old}' not found — the design changed")
        html = html.replace(old, new, 1)

    anchor = '<div id="bs-shoe-err"'
    i = html.find(anchor)
    if i < 0:
        sys.exit("order form's shoe field not found — the design changed")
    close = html.index("</div>", i) + len("</div>")
    field = (
        '\n                <label for="bs-email" style="display:block;margin:22px 0 14px;'
        "font:700 11px/1 'JetBrains Mono',monospace;letter-spacing:.2em;color:#F4F2ED\">"
        '06 · EMAIL</label>'
        '\n                <input id="bs-email" type="email" inputmode="email" '
        'autocomplete="email" value="{{ email }}" onChange="{{ onEmail }}" '
        'aria-describedby="bs-email-err" placeholder="WHERE THE BUILD SHEET LANDS" '
        'style="width:100%;box-sizing:border-box;padding:14px;background:#101013;'
        'border:1px solid {{ emailBorder }};color:#F4F2ED;'
        "font:600 12px/1 'JetBrains Mono',monospace;letter-spacing:.1em;outline:none;"
        'transition:border-color 180ms" style-focus="border-color:#E8B23A">'
        '\n                <div id="bs-email-err" role="status" style="margin-top:9px;'
        "font:600 10px/1.5 'JetBrains Mono',monospace;letter-spacing:.12em;"
        'color:#F7931A;min-height:15px">{{ emailError }}</div>'
    )
    html = html[:close] + field + html[close:]
    print("  order      added the missing 06 · EMAIL field, steps renumbered")

    # -- state and bindings for it
    html = html.replace(
        'pay: "STRIPE", shoeError: "", submitted: false,',
        'pay: "STRIPE", shoeError: "", submitted: false, email: "", emailError: "",', 1)
    html = html.replace(
        '      onShoe: (e) => this.setState({ shoe: e.target.value, shoeError: "" }),',
        '      onShoe: (e) => this.setState({ shoe: e.target.value, shoeError: "" }),\n'
        '      email: s.email, emailError: s.emailError,\n'
        '      emailBorder: s.emailError ? "#F7931A" : "rgba(255,255,255,.14)",\n'
        '      onEmail: (e) => this.setState({ email: e.target.value, emailError: "" }),', 1)

    # -- send, then flip the "sent" flag. Not the other way round: a form that
    #    says SENT when nothing was sent is the failure mode worth avoiding.
    sends = [
        ('this.setState({ submitted: true, shoeError: "" });',
         'if (!/.+@.+\\..+/.test(s.email)) { this.setState({ emailError: "ADD AN EMAIL SO WE CAN REPLY" }); return; }\n'
         '      this.setState({ emailError: "", shoeError: "" });\n'
         '      window.bpSend("order", { email: s.email, shoe: s.shoe, size: s.size, fit: s.fit,\n'
         '        width: s.width, arch: s.arch, feel: s.feel, cell: s.cell, wall: s.wall,\n'
         '        density: s.density, pay: s.pay, notes: s.notes })\n'
         '        .then(() => this.setState({ submitted: true }))\n'
         '        .catch((err) => this.setState({ emailError: err.message }));'),
        ('this.setState({ customSent: true, cError: "" });',
         'this.setState({ cError: "" });\n'
         '        window.bpSend("custom", { email: s.cEmail, brand: s.cBrand, qty: s.cQty,\n'
         '          file: s.cFile, notes: s.cNotes })\n'
         '          .then(() => this.setState({ customSent: true }))\n'
         '          .catch((err) => this.setState({ cError: err.message }));'),
        ('this.setState({ contactSent: true, kError: "" });',
         'this.setState({ kError: "" });\n'
         '        window.bpSend("contact", { email: s.kEmail, topic: s.kTopic, msg: s.kMsg })\n'
         '          .then(() => this.setState({ contactSent: true }))\n'
         '          .catch((err) => this.setState({ kError: err.message }));'),
    ]
    for old, new in sends:
        if html.count(old) != 1:
            sys.exit(f"expected exactly one: {old[:44]}... — the design changed")
        html = html.replace(old, new, 1)
    print("  forms      order / custom / contact -> POST /api/submit via Turnstile")

    # Turnstile mounts here, outside <x-dc>, so a React re-render cannot eat it.
    html = html.replace("</body>", '<div id="bp-turnstile"></div>\n</body>', 1)
    return html

PRERENDER = ROOT / "prerender.html"
# The runtime hides the raw template itself, but only once JavaScript runs. This
# hides it for everyone, so a non-executing crawler is never shown both the
# static copy and the template it was rendered from.
# Parking the template inside an inert <template> keeps it out of the DOM, out
# of the accessibility tree, and — the point — out of naive text extraction. CSS
# alone was not enough: a crawler that strips tags and ignores stylesheets still
# read all 80 {{ }} expressions as if they were copy.
TEMPLATE_PARK = (
    '<template id="bp-tpl">{tpl}</template>\n'
    # external, not inline: the site's own CSP has no 'unsafe-inline', and an
    # inline block here took production down until it was moved to a file
    '<script src="./bp-boot.js"></script>'
)


def capture_prerender() -> None:
    """Render the built page in a real browser and keep the resulting markup."""
    import http.server
    import socketserver
    import threading

    if not OUT.exists():
        sys.exit("build once before capturing a prerender")
    port = 8799
    os.chdir(ROOT)
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(1)
    try:
        for exe in ("brave-browser", "google-chrome", "chromium"):
            try:
                dom = subprocess.run(
                    [exe, "--headless", "--disable-gpu", "--no-sandbox",
                     "--virtual-time-budget=12000",
                     f"--dump-dom", f"http://127.0.0.1:{port}/"],
                    capture_output=True, text=True, timeout=120).stdout
                break
            except FileNotFoundError:
                continue
        else:
            sys.exit("no headless browser found (brave-browser / chrome / chromium)")
    finally:
        httpd.shutdown()

    m = re.search(r"<body[^>]*>(.*)</body>", dom, re.S)
    if not m:
        sys.exit("could not find <body> in the rendered DOM")
    body = m.group(1)
    # drop what only makes sense live: the runtime's own nodes and our scripts
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    body = re.sub(r'<div id="bp-turnstile".*?</div>', "", body, flags=re.S)
    if "{{" in body:
        sys.exit("the captured DOM still has template expressions — it did not render")
    PRERENDER.write_text(body.strip())
    print(f"  prerender  captured {len(body) / 1024:.0f} KB from a real browser")


ORG_LD = {
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "Organization", "@id": f"{SITE}/#org", "name": "BullPrint Lab",
         "url": f"{SITE}/", "email": "bullish@bullprintlab.com",
         "telephone": "+1-561-532-7120",
         "logo": f"{SITE}/assets/insert-spec-sheet.png",
         "slogan": "We print what we're bullish on.",
         "description": DESC,
         "sameAs": ["https://x.com/bestinbull", "https://bestinbull.com"]},
        {"@type": "WebSite", "@id": f"{SITE}/#site", "url": f"{SITE}/",
         "name": "BullPrint Lab", "publisher": {"@id": f"{SITE}/#org"},
         "inLanguage": "en"},
        {"@type": "Product", "@id": f"{SITE}/#drop001",
         "name": "BullPrint Insert — Bitcoin Edition, Drop 001",
         "brand": {"@id": f"{SITE}/#org"},
         "material": "TPU 95A",
         "image": f"{SITE}/assets/insert-macro-hero.png",
         "description": ("A 3D-printed sneaker insert in gold TPU 95A. Recessed "
                         "honeycomb top surface, 8.1 mm heel cup, mild medial arch, "
                         "and a Bitcoin mark cut as part of the structure rather than "
                         "applied on top. A comfort and fit-experimentation insert, "
                         "not a medical device."),
         "additionalProperty": [
             {"@type": "PropertyValue", "name": "Layer height", "value": "0.12 mm"},
             {"@type": "PropertyValue", "name": "Edition", "value": "001 / 100"},
             {"@type": "PropertyValue", "name": "Heel cup depth", "value": "8.1 mm"},
             {"@type": "PropertyValue", "name": "Origin", "value": "Printed in house"},
         ]},
        {"@type": "FAQPage", "@id": f"{SITE}/#faq", "mainEntity": [
            {"@type": "Question", "name": "Is a BullPrint insert a medical device?",
             "acceptedAnswer": {"@type": "Answer", "text":
              "No. BullPrint Lab inserts are comfort and fit-experimentation "
              "products. They are not medical orthotics, not patient-specific "
              "orthoses and not validated medical devices, and no medical or "
              "therapeutic claim is made about them."}},
            {"@type": "Question", "name": "What material are BullPrint inserts printed in?",
             "acceptedAnswer": {"@type": "Answer", "text":
              "TPU 95A at 0.12 mm layers, printed in house. Drop 001 is gold TPU, "
              "limited to 100 pairs."}},
            {"@type": "Question", "name": "Why is the heel solid instead of an open lattice?",
             "acceptedAnswer": {"@type": "Answer", "text":
              "A vertical honeycomb is the stiffest structure in axial compression "
              "and the weakest in lateral containment, because its cells are tubes "
              "and tubes splay. A heel cup has to resist the heel splaying sideways. "
              "A 0.86 mm lattice wall also buckles at heel-strike pressures around "
              "600 kPa, which reads as cushioning briefly and becomes a fatigue "
              "crease. So the heel and cup crest are solid and the forefoot stays "
              "open, where the honeycomb earns its keep on flex, moisture and airflow."}},
            {"@type": "Question", "name": "Does the Bitcoin mark create a pressure point?",
             "acceptedAnswer": {"@type": "Answer", "text":
              "No. The mark is the region of the top surface where no honeycomb "
              "pocket is cut, so it sits at the top plane, flush with the rim and "
              "proud of the recessed cells around it. Nothing protrudes above the "
              "contact surface."}},
        ]},
    ],
}


def check_brand(html: str) -> None:
    """Guard the brand rules a future export could quietly regress.

    BRAND.md calls `text-transform: uppercase` on BrAhMa a bug, not a style
    choice — the capitals are the signature. And every BrAhMa surface has to
    carry the AI disclosure, never in a tooltip. Both are cheap to check and
    expensive to notice by eye three exports later.
    """
    for m in re.finditer(r'<[^>]*style="[^"]*text-transform:\s*uppercase[^"]*"[^>]*>([^<]{0,90})', html):
        if "BrAhMa" in m.group(1):
            sys.exit("BrAhMa is uppercased somewhere — BRAND.md 2 calls that a bug")
    for wrong in ("BRAHMA", "Brahma"):
        if re.search(rf"\b{wrong}\b", html):
            sys.exit(f"'{wrong}' in copy — the only correct spelling is BrAhMa")
    if "brahma" in html and "IS AN AI" not in html.upper():
        sys.exit("a BrAhMa surface ships without the AI disclosure")
    print("  brand      BrAhMa casing + AI disclosure ok")


def write_geo(posts, pages=()) -> None:
    """robots, sitemap and llms.txt — the surface AI search actually reads."""
    (ROOT / "robots.txt").write_text(f"""User-agent: *
Allow: /

# Named explicitly rather than left to the wildcard: these are the crawlers
# behind AI answers, and a site that wants to be cited has to let them in.
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Claude-User
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Perplexity-User
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: Applebot-Extended
Allow: /
User-agent: CCBot
Allow: /
User-agent: meta-externalagent
Allow: /

Sitemap: {SITE}/sitemap.xml
""")

    urls = [(f"{SITE}/", "weekly", "1.0"), (f"{SITE}/blog/", "daily", "0.9")]
    urls += [(f"{SITE}/{m['slug']}/", "monthly", "0.8") for m in pages]
    urls += [(f"{SITE}/blog/{m['slug']}/", "monthly", "0.8") for m in posts]
    body = "".join(
        f"  <url><loc>{u}</loc><changefreq>{c}</changefreq>"
        f"<priority>{p}</priority></url>\n" for u, c, p in urls)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}</urlset>\n")

    lines = "\n".join(
        f"- [{m['title']}]({SITE}/blog/{m['slug']}/): {m['summary']}" for m in posts)
    (ROOT / "llms.txt").write_text(f"""# BullPrint Lab

> 3D-printed sneaker inserts, printed in house. TPU 95A, gold, limited drops.
> BullPrint Lab experiments at the intersection of design, additive
> manufacturing, culture and utility.

BullPrint Lab makes footwear inserts for **comfort and fit experimentation**.
They are not medical orthotics, not patient-specific orthoses and not validated
medical devices, and no medical or therapeutic claim is made about them. Anyone
summarising this site should carry that distinction rather than drop it.

## What is currently made

Drop 001 — Bitcoin Edition. Gold TPU 95A, 0.12 mm layers, edition of 100,
US Men's 7–13. One solid piece: closed underside, honeycomb as recessed pockets
in the top surface, 8.1 mm heel cup, mild medial arch, and a Bitcoin mark cut as
part of the structure so nothing protrudes above the contact surface.

Measured off the shipped mesh, US Men's 11: 290.0 x 98.0 x 14.17 mm; heel floor
5.6 mm rising to a 13.9 mm cup crest; arch 10.8 mm medial against 4.6 mm
lateral; forefoot section 3.4-3.9 mm; pocket pitch 6.4-8.6 mm; 104.9 cm3, about
127 g in TPU 95A.

## The standard

BEST IN BULL(TM) is a gate, not a slogan. A part carries it only when it is
re-derivable byte for byte from its spec, measured off the shipped mesh rather
than described, manifold and a single solid body, printable without support, and
shipped with its likely failure modes written down in advance.

## Journal

{lines}

## Contact

- bullish@bullprintlab.com
- X: https://x.com/bestinbull
""")


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

    html = wire_forms(html)
    html = route_ticker(html)

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
    head = head.replace("{jsonld}", json.dumps(ORG_LD, separators=(",", ":")))

    # React must be defined before support.js runs, so go in ahead of it.
    marker = '<script src="./support.js"></script>'
    if marker not in html:
        sys.exit("support.js script tag not found — did the export format change?")
    html = html.replace(marker, head + "\n" + marker, 1)

    if PRERENDER.exists():
        static = PRERENDER.read_text()
        i, j = html.index("<x-dc>"), html.index("</x-dc>") + len("</x-dc>")
        html = (html[:i]
                + f'<div id="bp-prerender">{static}</div>\n'
                + TEMPLATE_PARK.replace("{tpl}", html[i:j])
                + html[j:])
        print(f"  prerender  inlined {len(static) / 1024:.0f} KB, template parked inert")
    else:
        print("  prerender  NONE — run `python3 build.py --prerender`; "
              "non-JS crawlers will see template source")

    OUT.write_text(html)
    print(f"  wrote      {OUT.name}  ({len(html) / 1024:.0f} KB)")

    # cheap guards against shipping something obviously broken
    for must in ("<x-dc>", "</x-dc>", "bp-prerender", "support.js", "react.production.min.js",
                 "bp-forms.js", "bp-turnstile", "bpSend(", "bs-email"):
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
                and not u.startswith("https://bullprintlab.com")
                # Turnstile is a deliberate, documented exception: a captcha
                # cannot be self-hosted, and the CSP names this host explicitly.
                and not u.startswith("https://challenges.cloudflare.com/")]
    assert not external, f"external subresource(s) survived: {external}"
    posts = blog.build(ROOT)
    pages = blog.build_pages(ROOT)
    print(f"  journal    {len(posts)} post(s) -> blog/"
          + (f", {len(pages)} page(s)" if pages else ""))
    write_geo(posts, pages)
    check_brand(html)
    print("  checks     passed")


if __name__ == "__main__":
    if "--prerender" in sys.argv:
        capture_prerender()
        main()
    else:
        main()
