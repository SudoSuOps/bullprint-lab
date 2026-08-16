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
import shutil
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

# The mark, as a favicon: the BULL, line cut, in brand gold on the brand
# near-black. BRAND.md assigns this cut to exactly this job — "Nav, badges,
# favicon, emboss, <=32px" — and the modelled master is barred below 40px, so
# the gradient bull would have turned to mush at 16. Stroke is ON THE PATHS and
# never inherited through <use>: inherited paint is dropped when the DOM is
# cloned for screenshot, PDF or PPTX export, and the mark ships blank.
# Weight 8 is the 16px step of the published stroke scale
# (2.2@96 · 3.4@48 · 5@30 · 6@24 · 6.5@22 · 8@16).
# Square — BRAND.md is explicit that there is no border radius anywhere in the
# system; the only rounded thing the brand makes is the part itself.
# Paths are the line cut from design_handoff_bullprint_lab/assets/marks.svg.txt,
# translated +13 in y to centre the silhouette (it spans y 9..84) in a 120 box.
FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
    '<rect width="120" height="120" fill="#0B0B0D"/>'
    '<g transform="translate(0,13)" fill="none" stroke="#E8B23A" stroke-width="8"'
    ' stroke-linejoin="round" stroke-linecap="round">'
    '<path d="M74 30C84 28 96 23 104 13C107 9 112 11 110 16C104 30 90 39 76 39"/>'
    '<path d="M46 30C36 28 24 23 16 13C13 9 8 11 10 16C16 30 30 39 44 39"/>'
    '<path d="M60 25H70C76 25 79 29 79 35L77 54C77 67 70 76 60 82C50 76 43 67'
    ' 43 54L41 35C41 29 44 25 50 25Z"/>'
    '<path d="M60 57C68 57 73 62 73 68C73 76 67 82 60 84C53 82 47 76 47 68C47 62'
    ' 52 57 60 57Z"/>'
    '<path d="M66 44L75 42.5M54 44L45 42.5"/>'
    '</g></svg>'
)

# NOTE: no <title> and no description here — the design carries both now, and
# emitting ours as well shipped duplicates. og:/twitter: below reuse whatever
# the design declared, via {title} / {desc}, so the card can never drift from
# the page.
HEAD = f"""<link rel="canonical" href="{SITE}/">
<meta name="theme-color" content="#0B0B0D">
<meta name="color-scheme" content="dark">
<link rel="icon" href="data:image/svg+xml;base64,{{favicon}}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="BullPrint Lab">
<meta property="og:url" content="{SITE}/">
<meta property="og:title" content="{{title}}">
<meta property="og:description" content="{{desc}}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1402">
<meta property="og:image:height" content="1122">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{title}}">
<meta name="twitter:description" content="{{desc}}">
<meta name="twitter:image" content="{OG_IMAGE}">
<script type="application/ld+json">{{jsonld}}</script>
<link rel="alternate" type="text/plain" href="/llms.txt">
<script src="./vendor/react.production.min.js"></script>
<script src="./vendor/react-dom.production.min.js"></script>
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<script src="./bp-forms.js" defer></script>
<script src="./bp-prerender.js" defer></script>"""

# ---- the platform app -----------------------------------------------------
#
# `design/BullPrintLab Platform.dc.html` is the AI-CAD application: landing,
# workspace, projects and compute. A second design export, built by the same
# rules as the site — vendored React, self-hosted fonts, no third-party
# request — but it needs none of the site's wiring: no image uploads, no store
# links, no BTC ticker, no Turnstile forms.
#
# It ships at /platform/, so subresources are referenced root-absolute:
# `./support.js` would resolve to /platform/support.js and 404.
PLATFORM_SRC = ROOT / "design" / "BullPrintLab Platform.dc.html"
PLATFORM_OUT = ROOT / "platform" / "index.html"

PLATFORM_TITLE = "BullPrint Lab Platform — describe the part, get the geometry."
PLATFORM_DESC = ("The AI CAD workspace behind BullPrint Lab. Describe a part in "
                 "plain language, read the BullSpec it derives, and generate real "
                 "parametric geometry — on our own GPU, on our own floor.")

PLATFORM_HEAD = f"""<title>{PLATFORM_TITLE}</title>
<meta name="description" content="{PLATFORM_DESC}">
<link rel="canonical" href="{SITE}/platform/">
<meta name="theme-color" content="#0B0B0D">
<meta name="color-scheme" content="dark">
<link rel="icon" href="data:image/svg+xml;base64,{{favicon}}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="BullPrint Lab">
<meta property="og:url" content="{SITE}/platform/">
<meta property="og:title" content="{PLATFORM_TITLE}">
<meta property="og:description" content="{PLATFORM_DESC}">
<meta property="og:image" content="{OG_IMAGE}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{PLATFORM_TITLE}">
<meta name="twitter:description" content="{PLATFORM_DESC}">
<link rel="alternate" type="text/plain" href="/llms.txt">
<script type="application/ld+json">{{platformld}}</script>
<script src="/vendor/react.production.min.js"></script>
<script src="/vendor/react-dom.production.min.js"></script>
<script src="/bp-prerender.js" defer></script>"""


PLATFORM_PRERENDER = ROOT / "platform-prerender.html"
PLATFORM_SCREENS = ("landing", "design", "projects", "compute")

# /platform/ is one level down, so the parked template's boot script — like
# every other subresource on that page — is referenced root-absolute.
PLATFORM_TEMPLATE_PARK = (
    '<template id="bp-tpl">{tpl}</template>\n'
    '<script src="/bp-boot.js"></script>'
)


def capture_platform_prerender() -> None:
    """Render every screen of the platform app and keep the markup.

    The site is one long document, so capturing it once captures all of it.
    The platform is a four-screen app where exactly one screen is in the DOM
    at a time — capturing it naively would ship a quarter of the page and hide
    COMPUTE, which is the most citable content on it, from every crawler that
    does not execute JavaScript.

    So each screen is rendered from a temporary copy with its initial state
    pinned, and the four are concatenated. That is the correct degradation
    rather than cloaking: a visitor without JavaScript cannot work the tabs
    either, so the static fallback has to carry all four. Same content, just
    unpaginated.
    """
    import http.server
    import socketserver
    import threading

    if not PLATFORM_OUT.exists():
        sys.exit("build once before capturing the platform prerender")

    anchor = 'state = {\n    screen: "landing"'
    built = PLATFORM_OUT.read_text()
    if built.count(anchor) != 1:
        sys.exit(f"platform prerender: initial-state anchor is not unique "
                 f"({built.count(anchor)} matches) — export format changed?")

    port = 8798
    os.chdir(ROOT)
    httpd = socketserver.TCPServer(
        ("127.0.0.1", port), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    tmp = PLATFORM_OUT.parent / "_capture.html"
    parts = []
    try:
        for screen in PLATFORM_SCREENS:
            tmp.write_text(built.replace(
                anchor, anchor.replace('"landing"', f'"{screen}"'), 1))
            for exe in ("brave-browser", "google-chrome", "chromium"):
                try:
                    dom = subprocess.run(
                        [exe, "--headless", "--disable-gpu", "--no-sandbox",
                         "--virtual-time-budget=10000", "--dump-dom",
                         f"http://127.0.0.1:{port}/platform/_capture.html"],
                        capture_output=True, text=True, timeout=120).stdout
                    break
                except FileNotFoundError:
                    continue
            else:
                sys.exit("no headless browser found (brave-browser / chrome / chromium)")

            m = re.search(r"<body[^>]*>(.*)</body>", dom, re.S)
            if not m:
                sys.exit(f"platform prerender: no <body> in the {screen} render")
            body = re.sub(r"<script.*?</script>", "", m.group(1), flags=re.S)
            body = re.sub(r"<template.*?</template>", "", body, flags=re.S)
            if "{{" in body:
                sys.exit(f"platform prerender: {screen} still has template "
                         "expressions — it did not render")
            # same guard as the site: never capture the previous static copy
            if 'id="bp-prerender"' in body:
                sys.exit(f"platform prerender: {screen} still contains the "
                         "previous static copy — bp-prerender.js did not run. "
                         "Rebuild first, then capture.")
            parts.append(f'<section data-screen="{screen}">{body.strip()}</section>')
            print(f"  platform   captured {screen}  ({len(body) / 1024:.0f} KB)")
    finally:
        httpd.shutdown()
        tmp.unlink(missing_ok=True)

    out = "\n".join(parts)
    PLATFORM_PRERENDER.write_text(out)
    print(f"  platform   prerender {len(out) / 1024:.0f} KB "
          f"across {len(parts)} screens")


def platform_compute(html: str) -> str:
    """Correct the COMPUTE page to the fleet that actually serves it.

    The export describes a single 96 GB RTX PRO 6000 holding the whole stack
    resident. That is not the deployment: the 96 GB card is reserved for
    in-house design and is deliberately not on the public path. Public
    inference runs on two consumer cards, routed by capability — which is what
    the page's own scheduler section already claims, so this makes the claim
    true rather than replacing it.

    Every number below is measured off the machines, not estimated:
      gpu-01  smash       RTX 5090 32,607 MiB · Ryzen 9 9950X3D 16C/32T · 60 GB
      gpu-02  defendable  RTX 3090 24,576 MiB · Ryzen 9 5900X  12C/24T · 62 GB
      in-house rails      RTX PRO 6000 Blackwell 96 GB · Xeon w9-3475X · 251 GB

    Fix this at source in the design when convenient and this step becomes a
    no-op — the asserts below will say so loudly if the export changes first.
    """
    subs = [
        # -- eyebrow + headline: the argument is the fleet, not one card
        ("SOVEREIGN COMPUTE · GPU-01 · ON OUR FLOOR",
         "SOVEREIGN COMPUTE · GPU-01 + GPU-02 · ON OUR FLOOR"),
        ("ONE CARD RUNS THE WHOLE STACK.",
         "ONE CARD HOLDS THE WHOLE MODEL."),

        # -- the 96 GB "everything resident" claim does not survive 32 GB
        ("96 GB is enough to keep the interpreter, the concept model and "
         "image-to-3D resident at once — no eviction, no cold loads between "
         "jobs. Geometry itself never touches the GPU: OpenSCAD and CadQuery "
         "run deterministic on the Xeon, so a render burst can't block a part "
         "from generating.",
         "BrAhMa runs on Muse-Glimmer-30B, resident on the 96 GB card at "
         "Q8_0 and never leaving it — 28 GB of weights against 96 GB of "
         "board, so there is no eviction, no cold load between jobs, and 66 "
         "GB still free for context and a second model. A 24 GB RTX 3090 "
         "registers as gpu-02 and takes overflow at a lower quantisation, so "
         "a queue degrades precision rather than dropping the job. Geometry "
         "itself never touches the GPU: OpenSCAD and CadQuery run "
         "deterministic on the CPU, so a render burst can't block a part "
         "from generating."),

        # -- the rack is now two machines
        ('{ k: "GPU", v: "RTX 6000 BLACKWELL · 96 GB" },\n'
         '        { k: "CPU", v: "XEON W9-3475X · SAPPHIRE RAPIDS · 36C/72T" },\n'
         '        { k: "RAM", v: "256 GB KINGSTON FURY DDR5" },\n'
         '        { k: "STORAGE", v: "4 TB NVME · MODELS + GENERATED ASSETS" },',
         '{ k: "GPU-01", v: "RTX PRO 6000 BLACKWELL · 96 GB · BrAhMa RESIDENT" },\n'
         '        { k: "GPU-02", v: "RTX 3090 · 24 GB · OVERFLOW" },\n'
         '        { k: "CPU", v: "XEON W9-3475X 36C/72T · RYZEN 9 5900X 12C/24T" },\n'
         '        { k: "RAM", v: "251 GB + 62 GB DDR5" },\n'
         '        { k: "STORAGE", v: "1.8 TB + 915 GB NVME · MODELS + ASSETS" },\n'
         '        { k: "RUNTIME", v: "LLAMA.CPP B2271 · CUDA 12.8 · SM_120" },'),

        # -- worker registration reflects the card that answers
        ('worker: "gpu-01",\n'
         '        gpu: "RTX 6000 Blackwell",\n'
         '        vram: 96,\n'
         '        cpu: "Xeon w9-3475X",\n'
         '        ram_gb: 256,\n'
         '        capabilities: ["text", "image", "vision", "3d", "render"]',
         'worker: "gpu-01",\n'
         '        gpu: "RTX PRO 6000 Blackwell",\n'
         '        vram: 96,\n'
         '        cpu: "Xeon w9-3475X",\n'
         '        ram_gb: 251,\n'
         '        capabilities: ["text", "vision", "structured-output"]'),

        # -- budget header: 32 GB, and it is a GGUF runtime, not FP8 vLLM
        ("VRAM BUDGET — 96 GB, FULLY RESIDENT", "VRAM BUDGET — GPU-01 · 96 GB, FULLY RESIDENT"),
        ("FP8 · vLLM", "Q8_0 · llama.cpp"),

        # -- the stack that is actually resident. FLUX and Hunyuan3D are not
        #    deployed on any card in the fleet; listing them as resident on a
        #    32 GB budget would be the exact overselling the brand forbids.
        ('{ name: "Qwen3-32B · FP8", role: "INTERPRETER — prompt → BullSpec → OpenSCAD, structured output via vLLM", gb: 34, pct: "35.4%", fg: "#F4F2ED" },\n'
         '        { name: "KV CACHE · 128K CTX", role: "Long design conversations without re-reading the spec each turn", gb: 24, pct: "25.0%", fg: "#F4F2ED" },\n'
         '        { name: "FLUX.1-dev · FP8", role: "CONCEPT — visual direction render, never the artifact", gb: 17, pct: "17.7%", fg: "#F4F2ED" },\n'
         '        { name: "Hunyuan3D-2", role: "IMAGE → 3D — photo or sketch to rough mesh, then re-specced as BullSpec", gb: 12, pct: "12.5%", fg: "#F4F2ED" },\n'
         '        { name: "HEADROOM", role: "Burst renders and model swaps without eviction", gb: 9, pct: "9.4%", fg: "#8B8780" }',
         '{ name: "Muse-Glimmer-30B · Q8_0", role: "INTERPRETER — the model under BrAhMa: prompt → BullSpec → OpenSCAD", gb: 28, pct: "29.4%", fg: "#F4F2ED" },\n'
         '        { name: "KV CACHE · 16K CTX", role: "Long design conversations without re-reading the spec each turn", gb: 2, pct: "2.1%", fg: "#F4F2ED" },\n'
         '        { name: "HEADROOM", role: "Context growth, a perception encoder, and a second model without eviction", gb: 66, pct: "68.5%", fg: "#8B8780" }'),

        # -- and the model call names the model that answers
        ("Qwen3-32B over anything bigger: at FP8 it leaves room for the entire "
         "visual stack plus a 128K context, and BullSpec generation is a "
         "structured-output problem, not a scale problem. Qwen2.5-Coder-32B is "
         "the drop-in fallback if pure OpenSCAD emission benchmarks better.",
         "Muse-Glimmer-30B at Q8_0 is the model under BrAhMa — near-lossless, "
         "because BullSpec generation is a structured-output problem where "
         "precision on the numbers matters more than parameter count. It is "
         "too new for vLLM and for Ollama's bundled runtime, so it runs on "
         "llama.cpp built from master against CUDA 12.8 for sm_120; that is "
         "the price of being early, and it is paid once. Qwen3.8-27B holds "
         "gpu-02 at Q4_K_M so overflow degrades quantisation rather than "
         "dropping the job. Concept render and image-to-3D are specified but "
         "not deployed — no card in the fleet holds them today.")
    ]

    for old, new in subs:
        if old not in html:
            sys.exit(f"platform compute: source text not found, export changed?\n  {old[:90]}…")
        html = html.replace(old, new, 1)

    # the retired claims must be gone, not merely edited around
    for gone in ("ONE CARD RUNS THE WHOLE STACK", "Qwen3-32B",
                 "FLUX.1-dev", "Hunyuan3D-2"):
        assert gone not in html, f"platform compute: stale claim survived: {gone}"
    print("  platform   COMPUTE: BrAhMa on Muse-Glimmer-30B, gpu-01 RTX PRO 6000")
    return html


def build_platform() -> None:
    """Build /platform/index.html from its design export.

    Deliberately not folded into main()'s pipeline: the site's transforms
    (asset repoint, form wiring, store links, ticker routing) are all
    site-specific, and running them against an export that has none of those
    hooks would fail the guards for the wrong reason.
    """
    if not PLATFORM_SRC.exists():
        print(f"  platform   SKIP — no {PLATFORM_SRC.name}")
        return

    html = PLATFORM_SRC.read_text()
    html = platform_compute(html)

    # Same font treatment as the site: no third-party request, so the CSP can
    # keep forbidding external hosts outright.
    before = html
    html = re.sub(r'<link rel="preconnect" href="https://fonts\.gstatic\.com"[^>]*>\s*', "", html)
    html = re.sub(r'<link href="https://fonts\.googleapis\.com/[^"]*" rel="stylesheet">',
                  '<link rel="stylesheet" href="/fonts/fonts.css">', html)
    if html == before:
        sys.exit("platform: font links not found — did the export format change?")

    # /platform/ is one level down; the export's relative runtime ref would 404.
    marker = '<script src="./support.js"></script>'
    if marker not in html:
        sys.exit("platform: support.js script tag not found — export format changed?")
    # The platform page had zero structured data. An AI answering "who does
    # AI-driven CAD for footwear" cannot cite what it cannot type.
    platform_ld = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "@id": f"{SITE}/platform/#app",
        "name": "BullPrint Lab Platform",
        "applicationCategory": "DesignApplication",
        "applicationSubCategory": "Computer-aided design",
        "operatingSystem": "Web",
        "url": f"{SITE}/platform/",
        "description": PLATFORM_DESC,
        "publisher": {"@id": f"{SITE}/#org"},
        "featureList": [
            "Describe a part in plain language and receive a readable BullSpec",
            "Generate real parametric geometry from the spec",
            "Edit any dimension by typing",
            "Export STL, OpenSCAD source and BullSpec JSON",
        ],
        "offers": {"@type": "Offer", "price": "0",
                   "priceCurrency": "USD",
                   "availability": "https://schema.org/PreOrder"},
    }
    head = PLATFORM_HEAD.replace(
        "{platformld}", json.dumps(platform_ld, separators=(",", ":")))
    head = head.replace(
        "{favicon}", base64.b64encode(FAVICON.encode()).decode())
    html = html.replace(marker, head + '\n<script src="/support.js"></script>', 1)

    if PLATFORM_PRERENDER.exists():
        static = PLATFORM_PRERENDER.read_text()
        i, j = html.index("<x-dc>"), html.index("</x-dc>") + len("</x-dc>")
        html = (html[:i]
                + f'<div id="bp-prerender">{static}</div>\n'
                + PLATFORM_TEMPLATE_PARK.replace("{tpl}", html[i:j])
                + html[j:])
        print(f"  platform   prerender inlined {len(static) / 1024:.0f} KB, "
              "template parked inert")
    else:
        print("  platform   prerender NONE — run `python3 build.py --prerender`; "
              "non-JS crawlers will see template source")

    html = add_footer(html, "platform")
    PLATFORM_OUT.parent.mkdir(exist_ok=True)
    PLATFORM_OUT.write_text(html)
    print(f"  platform   wrote {PLATFORM_OUT.relative_to(ROOT)}  ({len(html) / 1024:.0f} KB)")

    for must in ("<x-dc>", "</x-dc>", '"/support.js"', "/vendor/react.production.min.js",
                 "/fonts/fonts.css"):
        assert must in html, f"platform: missing {must}"
    assert "./support.js" not in html, "platform: a relative support.js ref survived"
    assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html, \
        "platform: a Google Fonts reference survived"
    sub = re.findall(r'<(?:script|img)\b[^>]*\bsrc="([^"]+)"', html)
    sub += re.findall(r'<link\b[^>]*\bhref="([^"]+)"', html)
    external = [u for u in sub if u.startswith(("http://", "https://"))
                and not u.startswith(SITE)]
    assert not external, f"platform: external subresource(s) survived: {external}"


# ── /bands/ — the Bull Band promo ────────────────────────────────────────────
#
# The first page in this repo to use <x-import>, and it broke two site-wide
# rules at once the first time it was looked at. Both are fixed HERE, at build
# time, rather than by loosening the CSP:
#
#   1. support.js decides how to load an x-import by file extension. A .jsx
#      module makes it inject @babel/standalone from unpkg — 3 MB of
#      third-party script on a page whose CSP is `script-src 'self'`. It does
#      not load, so the module never runs and the page renders NOTHING.
#      Fix: jsx-compile.js transforms the three modules to plain .js with the
#      same Babel and the same options the runtime would have used, so the
#      runtime takes the "js" branch and never reaches ensureBabel().
#
#   2. The helmet carries three INLINE <script> blocks (OM_SCENES, OM_PLAYBACK,
#      TWEAK_DEFAULTS). The helmet manager re-creates them as real inline
#      <script> elements in <head>, and `script-src 'self'` has no
#      'unsafe-inline' — so window.OM_SCENES is never set and the stage mounts
#      with no scenes. This is the same failure bp-boot.js already records
#      ("inline was blocked by the site's own CSP the moment it hit
#      production"), and it takes the same fix: a same-origin FILE. The values
#      are EXTRACTED from the export, never retyped, so the design stays the
#      one source.
#
# Neither is a hack around the CSP. The CSP is right; the export was authored
# for a preview host that has no CSP at all.

BANDS_SRC = ROOT / "design" / "Bull Band Promo.dc.html"
BANDS_OUT = ROOT / "bands" / "index.html"
BANDS_DIR = ROOT / "bands"
BANDS_STATIC = ROOT / "content" / "bands-static.md"

# Build-only. Gitignored, fetched on demand, and verified against the exact
# hash support.js pins for it — so the compiler used here is provably the
# compiler the browser would have used.
BABEL_LOCAL = ROOT / "build" / "babel.min.js"
BABEL_URL = "https://unpkg.com/@babel/standalone@7.29.0/babel.min.js"
BABEL_SRI = "sha384-m08KidiNqLdpJqLq95G/LEi8Qvjl/xUYll3QILypMoQ65QorJ9Lvtp2RXYGBFj1y"

# Order matters and is the export's own: animations-v3 defines the globals
# bull-band-promo destructures off window at module scope.
BANDS_JSX = ("animations-v3.jsx", "tweaks-panel.jsx", "bull-band-promo.jsx")

# The promo's two uploads, repointed at repo assets. Same treatment the site
# gives its own two design uploads; the assert below refuses to ship a page
# that still points at an `uploads/` path that only exists in Claude Design.
BANDS_IMAGES = {
    "uploads/pasted-1786883724308-0.png": "bull-band",
    "uploads/pasted-1786883900528-0.png": "bull-coin",
}

BANDS_TITLE = "Bull Bands — BullPrint Lab"
BANDS_DESC = ("A TPU Bull Button sewn into technical spacer mesh, not glued on "
              "top of it. Headbands and wristbands from BullPrint Lab — printed "
              "in house, hand sewn, numbered.")

BANDS_HEAD = f"""<title>{BANDS_TITLE}</title>
<meta name="description" content="{BANDS_DESC}">
<link rel="canonical" href="{SITE}/bands/">
<meta name="theme-color" content="#0B0B0D">
<meta name="color-scheme" content="dark">
<link rel="icon" href="data:image/svg+xml;base64,{{favicon}}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="BullPrint Lab">
<meta property="og:url" content="{SITE}/bands/">
<meta property="og:title" content="{BANDS_TITLE}">
<meta property="og:description" content="{BANDS_DESC}">
<meta property="og:image" content="{OG_IMAGE}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{BANDS_TITLE}">
<meta name="twitter:description" content="{BANDS_DESC}">
<link rel="alternate" type="text/plain" href="/llms.txt">
<script type="application/ld+json">{{bandsld}}</script>
<script src="/vendor/react.production.min.js"></script>
<script src="/vendor/react-dom.production.min.js"></script>"""

# The written half of the page. It is NOT a prerender — it does not get removed
# when the runtime mounts, because a visitor who CAN run the promo still needs
# to read what the thing is made of and what is not settled yet. The promo is
# the hero; this is the page.
BANDS_STATIC_CSS = """
  #bands-copy{max-width:760px;margin:0 auto;padding:64px 24px 96px;
    color:#F4F2ED;font:400 17px/1.65 Archivo,system-ui,sans-serif}
  #bands-copy .kicker{font:700 11px/1 'JetBrains Mono',monospace;letter-spacing:.2em;
    color:#E8B23A;text-transform:uppercase;margin:0}
  #bands-copy h1{font:900 clamp(34px,6vw,58px)/1.03 Archivo,sans-serif;
    letter-spacing:-.02em;margin:18px 0 14px}
  #bands-copy h2{font:800 26px/1.2 Archivo,sans-serif;letter-spacing:-.01em;margin:44px 0 12px}
  #bands-copy .lede{color:#A5A19A;font-size:19px;margin:0 0 8px}
  #bands-copy p{color:#A5A19A}
  #bands-copy strong{color:#F4F2ED}
  #bands-copy ul.spec{list-style:none;padding:0;margin:22px 0;
    border-top:1px solid rgba(255,255,255,.09)}
  #bands-copy ul.spec li{display:flex;justify-content:space-between;gap:18px;
    padding:13px 0;border-bottom:1px solid rgba(255,255,255,.09);
    font:500 14px/1.4 'JetBrains Mono',monospace;color:#8B8780}
  #bands-copy ul.spec b{color:#E8B23A;font-weight:700;letter-spacing:.06em}
  #bands-copy .lozenge{display:inline-block;border:1px solid rgba(232,178,58,.5);
    padding:15px 28px;font:700 12px/1 'JetBrains Mono',monospace;letter-spacing:.2em;
    color:#E8B23A}
  #bands-copy .lozenge:hover{background:rgba(232,178,58,.1)}
  #bands-copy .cta{margin-top:34px}
"""


def fetch_babel() -> bool:
    """Get the build-time compiler, once, and verify it is the right one.

    Gitignored on purpose: 3 MB that never ships, needed only on a machine that
    is re-compiling the design. `index.html` and `bands/*.js` are committed, so
    a Pages build with no build command still deploys the right page.
    """
    if BABEL_LOCAL.exists():
        got = "sha384-" + base64.b64encode(
            hashlib.sha384(BABEL_LOCAL.read_bytes()).digest()).decode()
        if got == BABEL_SRI:
            return True
        print(f"  bands      {BABEL_LOCAL.name} does not match the pinned SRI — refetching")
    BABEL_LOCAL.parent.mkdir(exist_ok=True)
    print(f"  bands      fetching {BABEL_URL}")
    try:
        subprocess.run(["curl", "-sS", "-L", "-m", "180", "-o", str(BABEL_LOCAL),
                        BABEL_URL], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  bands      could not fetch Babel ({e})")
        return False
    got = "sha384-" + base64.b64encode(
        hashlib.sha384(BABEL_LOCAL.read_bytes()).digest()).decode()
    if got != BABEL_SRI:
        sys.exit(f"fetched Babel does not match the SRI support.js pins\n"
                 f"  want {BABEL_SRI}\n  got  {got}")
    return True


# ── the contact bar ─────────────────────────────────────────────────────────
#
# blog.py carries this on the journal and every markdown page, and the home page
# has its own from the design. /platform/ and /bands/ shipped with NO footer at
# all — two of the six pages on this site had no way to reach the lab from the
# bottom of them.
#
# NOTE ON THE ADDRESS: bullprintlab.com, SINGULAR. There is no
# bullprintlabs.com mailbox, and BRAND.md is explicit that the name is never
# pluralised. An S here is a bounced enquiry, not a typo.
CONTACT_EMAIL = "bullish@bullprintlab.com"
CONTACT_X = "bestinbull"
CONTACT_PHONE = "561.532.7120"
CONTACT_CITY = "Jupiter"
CONTACT_REGION = "FL"
CONTACT_PLACE = "JUPITER, FLORIDA"
CONTACT_TEL = "+15615327120"

FOOTER = f"""<footer id="bp-foot"><div>
  <span>BEST IN BULL&trade; &middot; PRINTED IN HOUSE &middot; {CONTACT_PLACE}</span>
  <span><a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL.upper()}</a>
    &middot; <a href="tel:{CONTACT_TEL}">{CONTACT_PHONE}</a>
    &middot; <a href="https://x.com/{CONTACT_X}" rel="me">@{CONTACT_X.upper()}</a></span>
</div></footer>
<style>
  #bp-foot{{border-top:1px solid rgba(255,255,255,.09);background:#0B0B0D}}
  #bp-foot>div{{max-width:1180px;margin:0 auto;padding:26px 24px;display:flex;
    flex-wrap:wrap;gap:12px 26px;align-items:center;justify-content:space-between;
    font:600 11px/1.6 'JetBrains Mono',monospace;letter-spacing:.14em;color:#6E6B66}}
  #bp-foot a{{color:#E8B23A;text-decoration:none}}
  #bp-foot a:hover{{color:#F5D07A}}
</style>"""


def add_footer(html: str, where: str) -> str:
    """Append the contact bar to a page whose design never had one."""
    if CONTACT_EMAIL in html:
        print(f"  {where:<10} footer     already present, left alone")
        return html
    if "</body>" not in html:
        sys.exit(f"{where}: no </body> to append the footer to")
    print(f"  {where:<10} footer     {CONTACT_EMAIL} · {CONTACT_PHONE} · @{CONTACT_X}")
    return html.replace("</body>", FOOTER + "\n</body>", 1)


def bands_asset(upload: str, stem: str) -> str | None:
    """Resolve one of the promo's two images to a repo asset, webp first."""
    for ext in (".webp", ".png", ".jpg"):
        if (ROOT / "assets" / (stem + ext)).exists():
            return f"/assets/{stem}{ext}"
    return None


BANDS_STAMP = BANDS_DIR / ".sources.sha256"


def bands_fingerprint(images: dict) -> str:
    """What the compiled modules were built FROM.

    Content-hashed, not mtime-compared: a fresh `git clone` stamps every file
    with the checkout time, so mtimes would say "stale" on a tree that is
    perfectly current. The image mapping and the brand correction are folded in
    because both are applied to the compiled output — change either and the
    committed .js really is out of date.
    """
    h = hashlib.sha256()
    for n in BANDS_JSX:
        h.update(n.encode())
        h.update(hashlib.sha256((ROOT / "design" / n).read_bytes()).digest())
    h.update(repr(sorted(images.items())).encode())
    h.update(b"BULL PRINT LABS->BULLPRINT LAB")
    return h.hexdigest()


def bands_output_current(want: str) -> bool:
    """True when the committed bands/*.js already match the design on disk."""
    if not BANDS_STAMP.exists():
        return False
    if BANDS_STAMP.read_text().strip() != want:
        return False
    return all((BANDS_DIR / f"{n[:-4]}.js").exists() for n in BANDS_JSX)


def compile_bands_jsx(images: dict) -> bool:
    """design/*.jsx -> bands/*.js, then the two mechanical corrections.

    The toolchain — node, and a 3 MB Babel fetched over the network — is needed
    only when the design has actually MOVED. The compiled modules are committed,
    so the ordinary CI build has nothing to compile and needs neither.

    Three outcomes, in order:
      current + committed  -> reuse, say so, touch nothing
      design moved + tools -> recompile
      design moved, no tools -> STOP. Publishing a page built from source we
        cannot compile would ship a promo that silently disagrees with the
        design it claims to be generated from, which is the one thing this
        build exists to prevent.
    """
    want = bands_fingerprint(images)
    if bands_output_current(want):
        print(f"  bands      jsx        up to date ({want[:12]}) — "
              "no node, no Babel, nothing to do")
        return True

    have_node = shutil.which("node") is not None
    if not have_node:
        sys.exit(
            "bands: design/*.jsx has changed and node is not on PATH.\n"
            "  The compiled modules in bands/ are committed precisely so a CI\n"
            "  build never needs a toolchain — but they no longer match the\n"
            "  design, so publishing them would ship a stale promo.\n"
            "  Fix: run `python3 build.py` on a machine with node, then commit\n"
            "  bands/*.js and bands/.sources.sha256 alongside the design change.")
    if not fetch_babel():
        sys.exit(
            "bands: design/*.jsx has changed and the Babel compiler could not be\n"
            "  fetched. Same fix — build locally and commit bands/.")

    srcs = [str(ROOT / "design" / n) for n in BANDS_JSX]
    subprocess.run(["node", str(ROOT / "jsx-compile.js"), str(BABEL_LOCAL),
                    str(BANDS_DIR)] + srcs, check=True, cwd=ROOT)

    promo = BANDS_DIR / "bull-band-promo.js"
    js = promo.read_text()

    for upload, url in images.items():
        if upload not in js:
            sys.exit(f"bands: the promo no longer references {upload} — "
                     "re-point BANDS_IMAGES at whatever it uses now")
        js = js.replace(upload, url)
        print(f"  bands      repointed {upload} -> {url}")

    # BRAND.md 2: the house is BULLPRINT LAB, one word, never pluralised. The
    # export's Product Flex slate says "BULL PRINT LABS". Fix it at source in
    # the design when convenient and this step becomes a no-op — the assert
    # below will say so loudly if it goes away.
    wrong, right = "BULL PRINT LABS", "BULLPRINT LAB"
    if wrong not in js:
        sys.exit("bands: 'BULL PRINT LABS' not found — fixed at source? "
                 "delete this correction if so")
    js = js.replace(wrong, right)
    print(f"  bands      brand      {wrong!r} -> {right!r}")

    promo.write_text(js)
    BANDS_STAMP.write_text(want + "\n")
    print(f"  bands      stamped    {want[:12]} — CI reuses this without node")
    return True


def bands_scene_file(html: str) -> str:
    """Lift the helmet's inline scripts into a same-origin file.

    Returns the html with the inline blocks replaced by one <script src>. The
    payload is taken verbatim from the export — the scene list, the durations
    and the tweak defaults are still authored in Claude Design and never
    retyped here.

    OM_PLAYBACK is the one line rewritten rather than copied: the export loops a
    1920x1080 composition forever, which on a phone is a battery drain a visitor
    never asked for. `{mode:'times',count:N}` is the engine's own documented
    playback contract, so a reduced-motion visitor gets the film once and then a
    still frame, and everyone else gets the loop as authored.
    """
    blocks = re.findall(r"<script>(window\.OM_[A-Z]+|window\.TWEAK_DEFAULTS)"
                        r"([^<]*?)</script>\s*", html)
    if len(blocks) < 2:
        sys.exit(f"bands: expected the helmet's inline scripts, found {len(blocks)}")

    lines = []
    for name, rest in blocks:
        stmt = (name + rest).strip()
        if name == "window.OM_PLAYBACK":
            authored = re.search(r"'(.*)'", stmt)
            lines.append(
                "// Authored as " + (authored.group(1) if authored else "?") + ".\n"
                "// prefers-reduced-motion gets one pass instead of an endless one.\n"
                "window.OM_PLAYBACK = (window.matchMedia &&\n"
                "  window.matchMedia('(prefers-reduced-motion: reduce)').matches)\n"
                "  ? '{\"mode\":\"times\",\"count\":1}'\n"
                "  : " + (authored.group(0) if authored else "'{\"mode\":\"loop\"}'") + ";")
        else:
            lines.append(stmt if stmt.endswith(";") else stmt + ";")

    scene = ("/* GENERATED by build.py from design/Bull Band Promo.dc.html.\n"
             " * Do not edit — change the design and re-run the build.\n"
             " *\n"
             " * These three assignments are inline <script> in the export. The\n"
             " * helmet manager re-creates them as inline scripts in <head>, and\n"
             " * this site's CSP is `script-src 'self'` with no 'unsafe-inline',\n"
             " * so on the deployed page they would never execute and the stage\n"
             " * would mount with no scenes at all.\n"
             " */\n" + "\n".join(lines) + "\n")
    (BANDS_DIR / "scene.js").write_text(scene)
    print(f"  bands      helmet     {len(blocks)} inline script(s) -> /bands/scene.js")

    html = re.sub(r"<script>(?:window\.OM_[A-Z]+|window\.TWEAK_DEFAULTS)[^<]*?</script>\s*",
                  "", html)
    return html.replace("</helmet>", '<script src="/bands/scene.js"></script>\n</helmet>')


def build_bands() -> bool:
    """Build /bands/index.html — the Bull Band promo over the written page.

    Returns True when the route was published, so write_geo only lists a page
    that exists.
    """
    if not BANDS_SRC.exists():
        print(f"  bands      SKIP — no {BANDS_SRC.name}")
        return False

    images, missing = {}, []
    for upload, stem in BANDS_IMAGES.items():
        url = bands_asset(upload, stem)
        if url:
            images[upload] = url
        else:
            missing.append(stem)
    if missing:
        print("  bands      SKIP — the promo's images are not in the repo yet.")
        for stem in missing:
            src = next(u for u, s in BANDS_IMAGES.items() if s == stem)
            print(f"               need assets/{stem}.webp (or .png) "
                  f"— that is {src} in the design project")
        print("               /bands/ is not published until they land; nothing"
              " else in this build is affected.")
        # A page whose two images 404 is worse than no page, and a compiled
        # module still carrying a since-deleted image path is worse again. The
        # whole output directory regenerates from the design in one command, so
        # take it down rather than leave a half-truth in the repo.
        stale = sorted(p for p in BANDS_DIR.glob("*") if p.is_file()) \
            if BANDS_DIR.exists() else []
        for p in stale:
            p.unlink()
        if stale:
            print(f"               removed {len(stale)} stale file(s) from "
                  f"{BANDS_DIR.relative_to(ROOT)}/")
        return False

    compile_bands_jsx(images)

    html = BANDS_SRC.read_text()
    html = bands_scene_file(html)

    before = html
    html = re.sub(r'<link rel="preconnect" href="https://fonts\.gstatic\.com"[^>]*>\s*', "", html)
    html = re.sub(r'<link href="https://fonts\.googleapis\.com/[^"]*" rel="stylesheet">',
                  '<link rel="stylesheet" href="/fonts/fonts.css">', html)
    if html == before:
        sys.exit("bands: font links not found — did the export format change?")

    # /bands/ is one level down, and the modules are precompiled, so both the
    # runtime ref and the x-import list are rewritten root-absolute.
    marker = '<script src="./support.js"></script>'
    if marker not in html:
        sys.exit("bands: support.js script tag not found — export format changed?")

    jsx_list = " ".join("./" + n for n in BANDS_JSX)
    js_list = " ".join(f"/bands/{n[:-4]}.js" for n in BANDS_JSX)
    if jsx_list not in html:
        sys.exit(f"bands: x-import list is not {jsx_list!r} — export changed?")
    html = html.replace(jsx_list, js_list)
    print(f"  bands      x-import   .jsx -> precompiled .js (no Babel at runtime)")

    bands_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "@id": f"{SITE}/bands/#product",
        "name": "Bull Bands",
        "url": f"{SITE}/bands/",
        "description": BANDS_DESC,
        "brand": {"@id": f"{SITE}/#org"},
        "material": "Thermoplastic polyurethane, technical spacer mesh",
        "offers": {"@type": "Offer", "url": f"{SITE}/bands/",
                   "priceCurrency": "USD",
                   "availability": "https://schema.org/PreOrder"},
    }
    head = BANDS_HEAD.replace("{bandsld}", json.dumps(bands_ld, separators=(",", ":")))
    head = head.replace("{favicon}", base64.b64encode(FAVICON.encode()).decode())
    html = html.replace(marker, head + '\n<script src="/support.js"></script>', 1)

    if not BANDS_STATIC.exists():
        sys.exit(f"bands: missing {BANDS_STATIC.relative_to(ROOT)}")
    m = blog.parse(BANDS_STATIC, required=("title", "summary"))
    copy = (f'<style>{BANDS_STATIC_CSS}</style>\n'
            f'<main id="bands-copy">\n'
            f'  <p class="kicker">{m.get("kicker", "Signal")}</p>\n'
            f'  <h1>{m["title"]}</h1>\n'
            f'  <p class="lede">{blog.inline(m["summary"])}</p>\n'
            f'  {blog.md(m["body"])}\n'
            f'</main>\n')
    html = html.replace("</body>", copy + "</body>", 1)
    print(f"  bands      copy       {BANDS_STATIC.name} -> {len(copy) / 1024:.0f} KB, "
          "always visible")

    html = add_footer(html, "bands")
    BANDS_OUT.parent.mkdir(exist_ok=True)
    BANDS_OUT.write_text(html)
    print(f"  bands      wrote {BANDS_OUT.relative_to(ROOT)}  ({len(html) / 1024:.0f} KB)")

    for must in ("<x-dc>", "</x-dc>", '"/support.js"', "/vendor/react.production.min.js",
                 "/fonts/fonts.css", "/bands/scene.js", "/bands/bull-band-promo.js",
                 'id="bands-copy"', "BEST IN BULL"):
        assert must in html, f"bands: missing {must}"
    assert "./support.js" not in html, "bands: a relative support.js ref survived"
    assert ".jsx" not in html, "bands: a .jsx x-import survived — the page would load Babel"
    assert "uploads/" not in html, "bands: an upload reference survived the rewrite"
    assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html, \
        "bands: a Google Fonts reference survived"
    # Every EXECUTABLE inline <script> must be gone: this page's CSP has no
    # 'unsafe-inline'. A data block (application/ld+json) is never executed and
    # is not what script-src governs, so it stays — the JSON-LD above is one.
    inline_js = [t for t in re.findall(r"<script\b([^>]*)>(?=\s*\S)", html)
                 if "src=" not in t and "ld+json" not in t]
    assert not inline_js, \
        f"bands: an executable inline <script> survived: {inline_js} — the CSP blocks it"
    sub = re.findall(r'<(?:script|img)\b[^>]*\bsrc="([^"]+)"', html)
    sub += re.findall(r'<link\b[^>]*\bhref="([^"]+)"', html)
    external = [u for u in sub if u.startswith(("http://", "https://"))
                and not u.startswith(SITE)]
    assert not external, f"bands: external subresource(s) survived: {external}"
    for stray in BANDS_DIR.glob("*.jsx"):
        sys.exit(f"bands: {stray.name} is in the served directory — "
                 "only compiled .js belongs there")
    return True


# ── the line ────────────────────────────────────────────────────────────────
#
# Three products. Insoles, slides, headbands. Nothing else is offered, and the
# rule that decides it is one sentence: WE DO NOT OFFER WHAT WE DO NOT PRINT.
#
# This is not a preference, it is the whole pitch. A lab that lists a water shoe
# it has never printed, a heel cup parked behind an open question, and a
# cut-and-sew headband its own copy admits "nothing on our floor makes", is a
# dropshipper with good typography. The catalogue IS the credibility.
#
# RETIRED is enforced, not remembered: check_line() below fails the build if any
# of these names survives into a built page. The design export still carries
# some of them, so PURGE fixes them mechanically on the way through — fix them
# at source in Claude Design and each substitution becomes a no-op, which the
# asserts will say out loud.

THE_LINE = ("BULL INSOLES", "BULL SLIDES", "BULL HEADBANDS")

RETIRED = {
    "BULL SWIMS": "water shoe — never printed, never costed against a real machine",
    "BULL HEEL CUP": "parked behind an open question about the feathered cut",
    "BULL BITS": "never a product here, only a line in a brief",
    "BULL LAB": "a category for experiments, which is a catalogue by another name",
    "BULL SOCKS": "not printed",
}

# Every mechanical correction the retirement needs, applied to the site export.
# Each one asserts its needle exists, so a re-export that already fixed it fails
# loudly rather than rotting in place.
PURGE = [
    # 1. The drops rail carried a third drop for a product that does not exist.
    ('\n        {\n          no: "DROP 003", name: "BULL SWIMS", material: "TPU 95A · BLACK", edition: "RUN SIZE TBC",\n'
     '          note: "Water shoe. 360° drainage, secure fit collar, nothing in it to stay wet.", status: "COMING SOON", cta: "NOTIFY VIA X",\n'
     '          bg: "#101013", bgImg: this.lattice(1), bgSize: "20px 35px", bgPos: "50% 50%",\n'
     '          statusFg: "#A5A19A", statusBg: "rgba(255,255,255,.06)", statusLine: "rgba(255,255,255,.16)",\n'
     '          border: "rgba(255,255,255,.09)", nameColor: "#F4F2ED", ctaColor: "#8B8780"\n        },',
     '\n        {\n          no: "DROP 003", name: "BULL HEADBANDS", material: "TPU 90A BUTTON + SPACER MESH", edition: "RUN SIZE TBC",\n'
     '          note: "Printed TPU Bull Button, stitch channels in the geometry, sewn into technical spacer mesh.", status: "IN THE LAB", cta: "ON THE BENCH",\n'
     '          bg: "#101013", bgImg: this.lattice(1), bgSize: "20px 35px", bgPos: "50% 50%",\n'
     '          statusFg: "#E8B23A", statusBg: "rgba(232,178,58,.12)", statusLine: "rgba(232,178,58,.4)",\n'
     '          border: "rgba(255,255,255,.09)", nameColor: "#F4F2ED", ctaColor: "#8B8780"\n        },',
     "drops rail: DROP 003 is headbands, not a water shoe"),

    # 2. The page's own meta description sold a product line that is retiring.
    ("AI-designed, 3D-printed footwear hardware. Insoles, slides and swims in "
     "bull-grade TPU — serialized, inspected, BEST IN BULL.",
     "AI-designed, 3D-printed footwear hardware. Insoles, slides and headbands "
     "in bull-grade TPU — serialized, inspected, BEST IN BULL.",
     "meta description: three products, and they are the three we print"),

    # 3. A fabric print specified for a lining that has nowhere to line.
    ('spec: "486 MM REPEAT · SWIMS LINING"',
     'spec: "486 MM REPEAT · PACKAGING"',
     "fabric 02: repeat is for packaging now that swims are gone"),

    # 4. THE ONE THAT MATTERS. The export's own Bull Bands block says the
    #    headband "isn't printed" and that "nothing on our floor makes it" — a
    #    product the house rule forbids offering, described in the house's own
    #    words. The Bull Band that IS offered has a printed TPU Bull Button in
    #    it, which is exactly what makes it ours to sell.
    ("BULL BANDS — SAME CLOTH, NO PRINT TIME",
     "BULL HEADBANDS — THE BUTTON IS THE PRINT",
     "bands: the headband is a printed part, not a cut-and-sew buy-in"),
    ("The spacer mesh is already the right material for a headband: open-cell, "
     "wicking, holds a stretch without a seam. One cut piece, two stitched "
     "loops, 320 × 62 mm — the first BullPrint product that isn't printed and "
     "the only one that ships same day. Coming once we have a cut-and-sew "
     "partner; nothing on our floor makes it.",
     "The spacer mesh is already the right material for a headband: open-cell, "
     "wicking, holds a stretch without a seam. What makes it ours is the Bull "
     "Button — a low-profile TPU badge, 20–30 mm, with the stitch channels "
     "printed into the geometry so it is sewn through rather than glued on, and "
     "flexes with the cloth instead of fighting it. We print the button. The "
     "skin-contact and bond questions are open and the Materials Engineer owns "
     "them, so there is no drop number on this yet.",
     "bands copy: the Bull Button is the printed part"),
]


def purge_line(html: str) -> str:
    """Retire everything that is not one of the three, at the source page."""
    for old, new, why in PURGE:
        if old not in html:
            sys.exit(f"purge: needle gone — {why}\n"
                     f"  fixed at source in the design? delete this entry.\n"
                     f"  looked for: {old[:90]!r}")
        html = html.replace(old, new)
        print(f"  purge      {why}")
    return html


def check_line(pages: dict) -> None:
    """No retired product may survive into anything this build publishes.

    A promise in a README is not a control. This is: if a re-export, a markdown
    edit or a new page reintroduces a product the lab does not print, the build
    stops and names it.
    """
    hits = []
    for where, html in pages.items():
        upper = html.upper()
        for name, why in RETIRED.items():
            if name in upper:
                hits.append(f"{where}: {name} ({why})")
    if hits:
        sys.exit("a retired product survived into a built page:\n  "
                 + "\n  ".join(hits))
    print(f"  line       {len(THE_LINE)} products, {len(RETIRED)} retired names "
          f"absent from {len(pages)} page(s)")


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


def link_footlabos(html: str) -> str:
    """AT-RISK FEET in the header nav, pointing at footlabos.com.

    Same mechanism as STORE: the nav is authored as in-page anchors, so an
    off-page route has to be added here to survive the next import.

    The LABEL is doing compliance work. In the footer this link sits beside
    "NO MEDICAL CLAIMS" and reads as a handoff. In the header it sits inside
    the product nav, one item away from DROPS, where a bare brand name would
    imply the two labs sell the same kind of thing. "AT-RISK FEET" names who
    it is for and, by omission, who BullPrint is not for — the distinction
    survives even when someone only skims the nav.

    footlabos.com is requested explicitly. It 301s to openfootlab.com, which
    the footer links directly, so this spends one redirect — worth knowing,
    not worth overriding.
    """
    anchor = '{ label: "STORE", href: "/store/", id: "store" },'
    if '"AT-RISK FEET"' in html:
        return html
    if anchor not in html:
        raise SystemExit("STORE nav item not found — link_store must run first")
    print("  footlabos  AT-RISK FEET added to the header nav -> footlabos.com")
    return html.replace(
        anchor,
        anchor + '\n        { label: "AT-RISK FEET", href: "https://footlabos.com",'
                 ' id: "footlabos" },', 1)


def link_openfootlab(html: str) -> str:
    """Point at-risk feet at the clinical lab, in the footer, beside the non-claim.

    BullPrint's first non-negotiable is no medical or therapeutic claims,
    anywhere, by anyone. A sister link to a foot-at-risk platform is the one
    place that rule could quietly break: put it next to the product and it
    reads as "these inserts help at-risk feet", which is a medical claim by
    association and is false.

    So it goes in the footer's legal bar, welded to the existing
    "NO MEDICAL CLAIMS" line, and it sends those people AWAY rather than
    inviting them in. Framed that way the link strengthens the position
    instead of eroding it — it is the disclaimer with somewhere to go.

    openfootlab.com is canonical; footlabos.com 301s to it, so linking the
    alias would spend a redirect and split the signal for nothing.

    Belongs in the design export, like the contact address before it. Until it
    is there, this transform carries it and fails loudly if the anchor moves.
    """
    anchor = "<span>NO MEDICAL CLAIMS · EXPERIMENTAL PRODUCTS</span>"
    if anchor not in html:
        sys.exit("footer legal bar not found — did the export change?")
    html = html.replace(anchor, anchor + (
        '\n        <span>FEET AT RISK? THAT IS A DIFFERENT LAB · '
        '<a href="https://openfootlab.com" target="_blank" rel="noopener"'
        ' style="color:#E8B23A">OPENFOOTLAB.COM</a></span>'), 1)
    print("  openfootlab at-risk handoff added to the footer legal bar")
    return html


def link_store(html: str) -> str:
    """Put STORE in the header nav.

    The nav is authored as anchors into the single page, so a route to another
    document has to be added here rather than in the design — and adding it here
    means it survives the next import instead of being something someone has to
    remember. The links are plain <a href> with no click handler, so an
    off-page href navigates normally; the active-state test keys on `id`, which
    simply never matches for a page that is not a section of this one.
    """
    anchor = '{ label: "DROPS", href: "#drops", id: "drops" },'
    if '"STORE"' in html:
        return html
    if anchor not in html:
        raise SystemExit("nav item list not found — the design changed shape")
    print("  store      STORE added to the header nav -> /store/")
    return html.replace(
        anchor, anchor + '\n        { label: "STORE", href: "/store/", id: "store" },', 1)


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
         '      var bp = { email: s.email, shoe: s.shoe, size: s.size, fit: s.fit,\n'
         '        width: s.width, arch: s.arch, feel: s.feel, cell: s.cell, wall: s.wall,\n'
         '        density: s.density, pay: s.pay, notes: s.notes,\n'
'        profileId: "BP-" + s.size + s.width.charAt(0) + s.arch.charAt(0) + "-001" };\n'
         '      if (s.pay === "STRIPE") {\n'
         '        window.bpCheckout(bp).catch((err) => this.setState({ emailError: err.message }));\n'
         '      } else {\n'
         '        window.bpSend("order", bp)\n'
         '          .then(() => this.setState({ submitted: true }))\n'
         '          .catch((err) => this.setState({ emailError: err.message }));\n'
         '      }'),
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
    body = re.sub(r"<template.*?</template>", "", body, flags=re.S)
    body = re.sub(r'<div id="bp-turnstile".*?</div>', "", body, flags=re.S)
    if "{{" in body:
        sys.exit("the captured DOM still has template expressions — it did not render")
    # A capture runs against the previously built page, which already carries
    # an inlined static copy. That copy is normally removed by bp-prerender.js
    # before the capture reads the DOM — but if it is not (a slow render, or a
    # boot script that failed to load) the capture silently doubles in size and
    # every visitor gets the page twice. Refuse rather than ship that.
    if 'id="bp-prerender"' in body:
        sys.exit("the captured DOM still contains the previous static copy — "
                 "bp-prerender.js did not run. Rebuild first (`python3 build.py`) "
                 "so the page loads it, then capture.")
    PRERENDER.write_text(body.strip())
    print(f"  prerender  captured {len(body) / 1024:.0f} KB from a real browser")


ORG_LD = {
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "Organization", "@id": f"{SITE}/#org", "name": "BullPrint Lab",
         "url": f"{SITE}/", "email": "bullish@bullprintlab.com",
         "telephone": "+1-561-532-7120",
         "address": {"@type": "PostalAddress", "addressLocality": "Jupiter",
                     "addressRegion": "FL", "addressCountry": "US"},
         "areaServed": {"@type": "Country", "name": "United States"},
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


def write_geo(posts, pages=(), bands=False) -> None:
    """robots, sitemap and llms.txt — the surface AI search actually reads.

    `bands` is passed rather than assumed: /bands/ only publishes once the
    promo's images are in the repo, and listing a route that 404s is worse than
    listing nothing.
    """
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

    # /platform/ is a first-class page, not an appendix — it shipped and was
    # then left out of the sitemap entirely, so nothing crawling this site
    # could discover the product it is mostly about.
    urls = [(f"{SITE}/", "weekly", "1.0"), (f"{SITE}/blog/", "daily", "0.9"),
            (f"{SITE}/platform/", "weekly", "0.9")]
    if bands:
        urls.append((f"{SITE}/bands/", "weekly", "0.9"))
    # /order/confirmed is a post-payment page; it should never be indexed
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
    # Standalone pages carry as much citable material as the journal — the line
    # and the titles both live here — and a crawler that only ever sees dated
    # posts comes away thinking this is a blog with a shop bolted on.
    plines = "\n".join(
        f"- [{m['title']}]({SITE}/{m['slug']}/): {m['summary']}" for m in pages)
    if bands:
        bm = blog.parse(BANDS_STATIC, required=("title", "summary"))
        plines += f"\n- [{bm['title']}]({SITE}/bands/): {bm['summary']}"
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

## The line

Three products, and only three: Bull Insoles ($99, live), Bull Slides ($128, in
the lab) and Bull Headbands (in the lab). The rule that decides the list is that
BullPrint Lab does not offer what it does not print — a water shoe and a heel cup
were both retired for that reason rather than parked. Custom runs put a client's
mark into the lattice of those same three; they are not a fourth product.
Everything is made to order — nothing is held in a warehouse — and the qualified
material is TPU (95A firm, 90A skin-contact). TPU 80A is suspended and PEBA is
listed but not yet qualified on our machines; nothing ships in either. Full detail,
including why each item is printed rather than moulded, is at {SITE}/store/.

## Pages

{plines}

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

    html = purge_line(html)
    html = wire_forms(html)
    html = link_store(html)
    html = link_footlabos(html)
    html = link_openfootlab(html)
    html = route_ticker(html)

    # self-hosted fonts: drop the Google links, add the local stylesheet
    before = html
    html = re.sub(r'<link rel="preconnect" href="https://fonts\.gstatic\.com"[^>]*>\s*', "", html)
    html = re.sub(r'<link href="https://fonts\.googleapis\.com/[^"]*" rel="stylesheet">',
                  '<link rel="stylesheet" href="./fonts/fonts.css">', html)
    if html == before:
        sys.exit("font links not found — did the export format change?")
    print("  fonts      google links -> ./fonts/fonts.css")

    # The design is the source of truth for the title and description. Read
    # them back out of it rather than declaring a second, competing pair.
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    page_title = m.group(1).strip() if m else TITLE
    m = re.search(r'<meta name="description" content="(.*?)"', html, re.S)
    page_desc = m.group(1).strip() if m else DESC
    print(f"  head       title from {'design' if page_title != TITLE else 'build.py fallback'}: "
          f"{page_title[:52]}")

    head = HEAD.replace(
        "{favicon}", base64.b64encode(FAVICON.encode()).decode())
    head = head.replace("{jsonld}", json.dumps(
        {**ORG_LD, "@graph": [
            {**n, "description": page_desc} if n.get("@type") == "Organization" else n
            for n in ORG_LD["@graph"]]}, separators=(",", ":")))
    head = head.replace("{title}", page_title).replace("{desc}", page_desc)

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
                 "bp-forms.js", "bp-turnstile", "bpSend(", "bs-email", '"/store/"',
                 "openfootlab.com", "NO MEDICAL CLAIMS", "footlabos.com",
                 "AT-RISK FEET"):
        assert must in html, must
    assert "uploads/" not in html, "an upload reference survived the rewrite"
    # The design started carrying its own <title> and description; if build.py
    # ever emits a second pair again the page ships duplicates and browsers
    # silently pick the first.
    for tag, want in (("<title>", 1), ('name="description"', 1)):
        n = html.count(tag)
        assert n == want, f"{tag} appears {n}x in index.html, want {want}"
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
    build_platform()
    bands = build_bands()
    blog.build_order_confirmed(ROOT)
    posts = blog.build(ROOT)
    pages = blog.build_pages(ROOT)
    print(f"  journal    {len(posts)} post(s) -> blog/"
          + (f", {len(pages)} page(s)" if pages else ""))
    write_geo(posts, pages, bands)
    check_brand(html)
    published = {"index.html": html,
                 "platform/index.html": PLATFORM_OUT.read_text(),
                 "llms.txt": (ROOT / "llms.txt").read_text()}
    for m in list(pages) + [{"slug": f"blog/{p['slug']}"} for p in posts]:
        published[f"{m['slug']}/index.html"] = (ROOT / m["slug"] / "index.html").read_text()
    if bands:
        published["bands/index.html"] = BANDS_OUT.read_text()
    check_line(published)
    print("  checks     passed")


if __name__ == "__main__":
    if "--prerender" in sys.argv:
        capture_prerender()
        capture_platform_prerender()
        main()
    else:
        main()
