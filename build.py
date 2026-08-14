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
  6. Wires the three forms to /api/submit, behind Turnstile. As exported they
     only flipped a local "sent" flag — they looked like they worked and nothing
     ever left the browser. This also adds the order form's missing EMAIL field:
     it collected size, width, arch, fit, feel, shoe, notes and payment
     preference, and no way to reply to the person.
  7. Nothing else. The <x-dc> template, the helmet block and every byte of the
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

# The design's placeholder address -> the mailboxes that actually exist.
DESIGN_EMAIL = "bullish@bullprintlab.com"
EMAIL_GENERAL = "bull@bullprintlab.com"
EMAIL_ORDERS = "print@bullprintlab.com"
# Sections whose "EMAIL THE LAB" button is an order/print enquiry, not general contact.
ORDER_SECTIONS = ("custom", "order")

TURNSTILE_SITEKEY = "0x4AAAAAAEQBxUgUlUeDfZjS"

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

    # contact address: order flows -> print@, everything else -> bull@
    n_before = html.count(DESIGN_EMAIL)
    # 6: two order-flow buttons, the about block, two contact links and the
    # "reply comes from ..." line in the contact form's success state.
    if n_before != 6:
        sys.exit(f"expected 6 references to {DESIGN_EMAIL}, found {n_before} — "
                 "the design changed, re-check which buttons sit in which flow")
    for sec in ORDER_SECTIONS:
        if f'id="{sec}"' not in html:
            sys.exit(f"section #{sec} not found in the design")
    out, cursor, n_ord = [], 0, 0
    for m in re.finditer(re.escape(DESIGN_EMAIL), html):
        # which section does this mailto fall in? the last section id before it
        sec_ids = re.findall(r'id="([a-z]+)"', html[:m.start()])
        target = EMAIL_ORDERS if sec_ids and sec_ids[-1] in ORDER_SECTIONS else EMAIL_GENERAL
        n_ord += target == EMAIL_ORDERS
        out.append(html[cursor:m.start()])
        out.append(target)
        cursor = m.end()
    out.append(html[cursor:])
    html = "".join(out)
    # the footer prints the address in caps as visible text
    html = html.replace(DESIGN_EMAIL.upper(), EMAIL_GENERAL.upper())
    print(f"  contact    {DESIGN_EMAIL} -> {EMAIL_ORDERS} ({n_ord}x), "
          f"{EMAIL_GENERAL} ({n_before - n_ord}x)")

    html = wire_forms(html)

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
    for must in ("<x-dc>", "</x-dc>", "support.js", "react.production.min.js",
                 "bp-forms.js", "bp-turnstile", "bpSend(", "bs-email"):
        assert must in html, must
    assert "uploads/" not in html, "an upload reference survived the rewrite"
    assert DESIGN_EMAIL not in html and DESIGN_EMAIL.upper() not in html, \
        "the design's placeholder address survived the rewrite"
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
    print("  checks     passed")


if __name__ == "__main__":
    main()
