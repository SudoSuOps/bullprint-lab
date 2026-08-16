#!/usr/bin/env python3
"""
BullPrint Lab — print files, generated from vector.

    python3 art/gen_art.py

WHY THIS EXISTS
---------------
Printful fetches print files from a public URL and wants 300 DPI. It refuses
below 150. Every raster master handed to this project is between 18 and 62 DPI
at print size — the bull head "master" is 180x180, which is 22 DPI across an
8 inch chest print. Those files are fine as web thumbnails and they are not
artwork.

The marks are vector, and so is every tee design in the merch sheet: T-01 to
T-05 are SVG paths and text inside `design/BullPrint Merch Tees.dc.html`. So
the print files are RE-DERIVED here rather than exported by hand, at whatever
size the placement calls for, from the same geometry the sheet draws.

    art/svg/*.svg   the six marks, lifted verbatim from the handoff bundle
    art/print/*.png what Printful fetches — 300 DPI, transparent, RGBA

WHAT A PRINT FILE IS
--------------------
The artwork alone. No garment, no mockup, no background. Printful composites it
onto the blank; anything else in the file prints as a rectangle of ink.

COLOURWAY RULE (from the sheet)
-------------------------------
Dark blank -> gold or bone art. Light blank -> black art. The art is generated
per colourway rather than recoloured later, because a gold that was picked for
black cotton is not the gold you want on bone.

TEXT
----
rsvg-convert renders text through fontconfig, so Archivo, JetBrains Mono and
Saira Stencil One must be installed as real outlines in ~/.fonts — the woff2
files the site serves are not enough. `check_fonts()` refuses to generate
anything if they are missing, because a silent fallback to DejaVu Sans would
produce a print file that looks right at thumbnail size and wrong at 11 inches.
"""
from __future__ import annotations

import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
SVG = HERE / "svg"
PRINT = HERE / "print"

DPI = 300

# Brand, from brand/tokens.css. Gold is the signature; bone and black are the
# two inks that read on the blanks the sheet calls for.
GOLD = "#E8B23A"
BONE = "#F4F2ED"
INK = "#141414"

GENESIS = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"

FONTS = ("Archivo", "JetBrains Mono", "Saira Stencil One")


def check_fonts() -> None:
    """Refuse to render if fontconfig would silently substitute."""
    missing = []
    for f in FONTS:
        out = subprocess.run(["fc-match", f], capture_output=True, text=True).stdout
        if f.split()[0].lower() not in out.lower():
            missing.append(f"{f} -> {out.strip()}")
    if missing:
        sys.exit("fonts not installed; rsvg would substitute silently:\n  "
                 + "\n  ".join(missing)
                 + "\n\nInstall the TTFs into ~/.fonts and run `fc-cache -f`.")
    print(f"  fonts      {', '.join(FONTS)} resolved")



def ring_text(text: str, cx: float, cy: float, r: float, size: float,
              fill: str, opacity: float = 1.0, weight: int = 500,
              start_deg: float = -90.0, sweep: float = 360.0) -> str:
    """Set text around a circle, ONE GLYPH AT A TIME.

    librsvg 2.60 does not implement <textPath> — it drops the run silently, so
    the seal rendered as bare rings and nobody would have known until a
    hundred shirts came back with an empty ring. Verified with a minimal case:
    plain <text> renders, <textPath> produces zero ink. No attribute spelling
    fixes it; xlink:href behaves the same.

    So each character is placed at its own angle and rotated tangent to the
    circle. Deterministic, no font metrics needed, and it renders anywhere.
    """
    n = len(text)
    if not n:
        return ""
    step = sweep / n
    out = []
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        a = start_deg + i * step
        rad = math.radians(a)
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)
        out.append(
            f'<text x="{x:.3f}" y="{y:.3f}" transform="rotate({a + 90:.3f} {x:.3f} {y:.3f})" '
            f'text-anchor="middle" fill="{fill}" opacity="{opacity}" '
            f"style=\"font:{weight} {size}px 'JetBrains Mono',monospace\">"
            f'{ch}</text>')
    return "".join(out)


BULL_D = ("M74 30C84 28 96 23 104 13C107 9 112 11 110 16C104 30 90 39 76 39"
          "M46 30C36 28 24 23 16 13C13 9 8 11 10 16C16 30 30 39 44 39"
          "M60 25H70C76 25 79 29 79 35L77 54C77 67 70 76 60 82C50 76 43 67 43 54"
          "L41 35C41 29 44 25 50 25Z"
          "M60 57C68 57 73 62 73 68C73 76 67 82 60 84C53 82 47 76 47 68C47 62 52 57 60 57Z"
          "M66 44L75 42.5M54 44L45 42.5")


def bull(stroke: str, w: float = 6.0) -> str:
    """The line-cut bull as ONE path with M-subpaths, per the Print Masters kit.
    Identical geometry to the five-path version, one node instead of five."""
    return (f'<path d="{BULL_D}" fill="none" stroke="{stroke}" stroke-width="{w}" '
            'stroke-linejoin="round" stroke-linecap="round"/>')


def kit(name: str) -> str:
    """A master from the Vector Kit, verbatim.

    Two of these are genuinely new geometry the marks file never had: the
    MODELLED bull (gradient horns, muzzle shadow, eyes, ear notches) and the
    SMALL seal (ring plus bull, no type at all — which is the right answer for
    a 3 inch cap panel, where 7px ring text becomes lint).

    seal-genesis.svg is NOT loaded here. It sets its rings with <textPath>, and
    librsvg 2.60 drops textPath silently — measured on this exact file: 0.00%
    ink in the hash band. The kit's own note says xlink:href fixes that; it does
    not, and both attributes are present on that file. The seal is generated by
    seal() instead, glyph by glyph, which rasterises anywhere.
    """
    src = (SVG / "kit" / f"{name}.svg").read_text()
    # standalone extraction needs the namespace HTML supplies implicitly
    if 'xmlns="http://www.w3.org/2000/svg"' not in src:
        src = src.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return src


def seal(fg: str) -> str:
    """T-01 — the genesis seal. Hash ring, name ring, bull, INSPECTED."""
    hashring = ring_text(GENESIS, 100, 100, 90, 7.2, fg, 0.55, 500)
    namering = ring_text("BEST IN BULL™ · BULLPRINT LAB · ", 100, 100, 64, 11, fg, 1.0, 700)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
<circle cx="100" cy="100" r="98" fill="none" stroke="{fg}" stroke-width="1" opacity=".45"/>
{hashring}
<circle cx="100" cy="100" r="81" fill="none" stroke="{fg}" stroke-width="3"/>
<circle cx="100" cy="100" r="52" fill="none" stroke="{fg}" stroke-width="1" opacity=".5"/>
{namering}
<g transform="translate(100,92) scale(0.8) translate(-60,-50)">{bull(fg)}</g>
<text x="100" y="134" text-anchor="middle" fill="{fg}" opacity=".6" style="font:500 7.5px \'JetBrains Mono\',monospace;letter-spacing:.2em">INSPECTED</text>
</svg>'''


def bullish(fg: str) -> str:
    """T-02 — the BULLISH lockup, bar pairs through the B, off the slide."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 66">
<g fill="{fg}">
  <rect x="8.8" y="3.3" width="2.5" height="12"/><rect x="14.7" y="3.3" width="2.5" height="12"/>
  <rect x="8.8" y="20.6" width="2.5" height="17.6"/><rect x="14.7" y="20.6" width="2.5" height="17.6"/>
  <text x="2" y="32" style="font:400 32px 'Saira Stencil One',sans-serif">B</text>
  <text x="25.9" y="32" style="font:400 32px 'Saira Stencil One',sans-serif;letter-spacing:.05em">ULLISH</text>
  <text x="86" y="58" text-anchor="middle" opacity=".55" style="font:500 7.5px 'JetBrains Mono',monospace;letter-spacing:.3em">BULLPRINT LAB · JUPITER FL</text>
</g>
</svg>'''


def we_print(fg: str) -> str:
    """T-03 front — left chest: the bull over two words."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 128">
<g transform="translate(0,0)">{bull(fg)}</g>
<text x="60" y="118" text-anchor="middle" fill="{fg}" style="font:700 10px 'JetBrains Mono',monospace;letter-spacing:.18em">WE PRINT.</text>
</svg>'''


def bull_back(fg: str) -> str:
    """T-03 back — the big line-cut bull over the domain."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 132">
{bull(fg)}
<text x="60" y="122" text-anchor="middle" fill="{fg}" style="font:700 9px 'JetBrains Mono',monospace;letter-spacing:.24em">BULLPRINTLAB.COM</text>
</svg>'''


def bull_on(fg: str) -> str:
    """T-04 front."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 90">
<text x="200" y="66" text-anchor="middle" fill="{fg}" font-family="Archivo, sans-serif" font-weight="900" font-size="60" letter-spacing="-1.8">BULL ON.</text>
</svg>'''


def bull_off(fg: str) -> str:
    """T-04 back — the nape answer."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100">
<g fill="{fg}" font-family="JetBrains Mono, monospace">
<text x="150" y="44" text-anchor="middle" font-weight="700" font-size="22" letter-spacing="4">BULL OFF.</text>
<text x="150" y="74" text-anchor="middle" font-weight="500" font-size="11" letter-spacing="2.6">DOES NOT EXIST</text>
</g></svg>'''


def genesis_stripe(fg: str) -> str:
    """T-05 — all 64 characters down the side seam. No truncation, ever:
    a genesis hash missing a character is just a wrong number.

    Kit proportions: 32 x 320 at 6.5px. The earlier 26 x 420 crammed the same
    64 glyphs into a taller, narrower box and the type came out thinner than
    the sheet drew it."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 320">
<text transform="rotate(90 16 8)" x="16" y="8" fill="{fg}" font-family="JetBrains Mono, monospace" font-weight="500" font-size="6.5" letter-spacing="0.78">{GENESIS}</text>
</svg>'''


def chest_hit(fg: str) -> str:
    """T-05 companion — small right-chest mark."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 16">
<text x="75" y="12" text-anchor="middle" fill="{fg}" style="font:700 8.5px 'JetBrains Mono',monospace;letter-spacing:.22em">BEST IN BULL™</text>
</svg>'''


def collar(fg: str) -> str:
    """Inside back collar — every tee gets it, per the sheet's order notes."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 134">
{bull(fg, 6)}
<text x="60" y="124" text-anchor="middle" fill="{fg}" font-family="JetBrains Mono, monospace" font-weight="700" font-size="9.5" letter-spacing="1">BEST IN BULL™</text>
</svg>'''


def cap_front(fg: str) -> str:
    """HATS. Embroidery wants a bold, closed, low-detail mark — the hash ring
    and 7px type on the seal would turn to lint at 3 inches on a cap panel.
    So the cap gets the bull alone, heavier stroke, nothing else."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 100">
{bull(fg, 8)}
</svg>'''


# Every piece in all three colourways — the store needs a variant per blank, and
# a gold picked for black cotton is not the gold you want on bone. Kit sizes.
PIECES = [
    ("t01-seal",        seal,           9.0),
    ("t02-bullish",     bullish,       10.5),
    ("t03f-we-print",   we_print,       3.5),
    ("t03b-bull",       bull_back,     11.0),
    ("t04f-bull-on",    bull_on,        9.0),
    ("t04b-bull-off",   bull_off,       3.0),
    ("t05-stripe",      genesis_stripe, 1.6),
    ("t05-chest",       chest_hit,      3.0),
    ("cap-bull",        cap_front,      3.0),
    ("collar",          collar,         2.4),
]
WAYS = (("gold", GOLD), ("bone", BONE), ("ink", INK))

JOBS = [(f"{n}-{w}", fn, inch, c) for n, fn, inch in PIECES for w, c in WAYS]
# The kit masters carry their own colour and are used as authored.
JOBS += [
    ("t06-bull-mascot",        lambda _c: kit("bull-modelled"),       8.0, GOLD),
    ("t03b-bull-modelled",     lambda _c: kit("bull-modelled"),      11.0, GOLD),
    ("cap-seal-small",         lambda _c: kit("seal-small"),          3.0, GOLD),
]

def render(name: str, svg: str, inches: float) -> pathlib.Path:
    px = round(inches * DPI)
    src = SVG / f"_{name}.svg"
    src.write_text(svg)
    out = PRINT / f"{name}.png"
    subprocess.run(["rsvg-convert", "-w", str(px), "-f", "png", "-o", str(out), str(src)],
                   check=True)
    src.unlink()
    return out


def main() -> None:
    if not shutil.which("rsvg-convert"):
        sys.exit("rsvg-convert not found — apt install librsvg2-bin")
    check_fonts()
    PRINT.mkdir(parents=True, exist_ok=True)

    from PIL import Image
    print(f"  target     {DPI} DPI, transparent RGBA, artwork only\n")
    for name, fn, inches, colour in JOBS:
        out = render(name, fn(colour), inches)
        im = Image.open(out)
        dpi = im.size[0] / inches
        flag = "" if dpi >= DPI - 1 else f"  <-- {dpi:.0f} DPI"
        print(f"  {name:<26} {inches:>5.1f} in   {im.size[0]:>5}x{im.size[1]:<5} "
              f"{im.mode}  {out.stat().st_size / 1024:>5.0f} KB{flag}")
        if im.mode != "RGBA":
            sys.exit(f"{name}: not RGBA — a print file needs a transparent ground")
        if dpi < 150:
            sys.exit(f"{name}: {dpi:.0f} DPI is under Printful's floor")
        # A dropped <textPath> renders a clean, plausible, WRONG file. The seal
        # without its rings still looks like a seal, which is how it nearly
        # shipped. Ink coverage is the cheapest way to notice.
        if name.startswith("t01"):
            import numpy as np
            a = np.array(im)[:, :, 3] > 8
            h, w = a.shape
            Y, X = np.mgrid[0:h, 0:w]
            rr = ((X - w / 2) ** 2 + (Y - h / 2) ** 2) ** 0.5 / (w / 2)
            band = a[(rr > 0.84) & (rr < 0.96)].mean()   # the hash ring only
            if band < 0.02:
                sys.exit(f"{name}: hash ring band is {band*100:.2f}% ink — the "
                         "ring text did not render. Total coverage is NOT a "
                         "valid check here; the circles alone pass it.")
            print(f"  {'':<26} hash ring {band*100:.1f}% ink · name ring set glyph-by-glyph")
    print(f"\n  {len(JOBS)} print file(s) -> art/print/")


if __name__ == "__main__":
    main()
