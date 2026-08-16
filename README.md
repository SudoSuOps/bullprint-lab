# bullprintlab.com

The BullPrint Lab site. Static, single-origin, deployed on Cloudflare Pages.

## How this is built

The design lives in Claude Design and is the source of truth:

> https://claude.ai/design/p/9dd423de-c1da-4abe-b2e6-2931610f721f?file=BullPrint+Lab+Site.dc.html

`design/BullPrint Lab Site.dc.html` is that export, byte for byte. **Do not edit
it by hand** — change the design, re-export, drop it in, re-run the build. Any
hand-patch here is a change that gets silently reverted the next time the design
moves.

```bash
python3 build.py      # design/*.dc.html  ->  index.html
```

The build makes four mechanical changes and nothing else. The `<x-dc>` template,
the helmet block and the markup are passed through untouched:

| # | change | why |
|---|---|---|
| 1 | Loads vendored React 18.3.1 before `support.js` | `support.js` otherwise pulls React off unpkg at runtime. The vendored copies are SRI-checked at build time against the exact hashes `support.js` itself pins — the build fails if they drift. |
| 2 | Repoints the two design uploads at `assets/*.webp` | 4.2 MB of PNG became 447 KB of WebP. The PNG originals are kept in `assets/`. |
| 3 | Adds the document head | Title, description, canonical, Open Graph, Twitter card, favicon, theme colour — none of which a `.dc.html` export can carry. |
| 4 | Self-hosts Archivo and JetBrains Mono | Google Fonts was the last third-party request on the page. Same typefaces, same weights, same origin. |

The build asserts on the way out that no external subresource survived, so
"single-origin" is checked rather than claimed.

## Why the runtime is still here

`BullPrint Lab Site.dc.html` is not a static page. It has 232 template
expressions, 21 loops, 8 conditionals and real state — the custom-insert
configurator, the exploded view, the order and contact forms. Pre-rendering it
to flat HTML would throw all of that away, so the dc runtime ships and React
mounts on load.

That has one consequence worth knowing: the runtime compiles templates with
`new Function`, so the CSP in `_headers` has to allow `'unsafe-eval'`. Every
other directive is locked down — `default-src 'self'`, no external hosts at all,
`frame-ancestors 'none'`, `object-src 'none'`.

## Layout

```
index.html          generated — do not edit, edit the design
build.py            the generator
blog.py             the journal + standalone pages
jsx-compile.js      build-time JSX -> JS, for /bands/ (see below)
design/             the Claude Design export (source of truth)
support.js          Claude Design runtime, as exported
vendor/             React 18.3.1 UMD, SRI-verified
bands/              generated — compiled promo modules + /bands/index.html
build/              gitignored, build-time only: @babel/standalone
fonts/              Archivo + JetBrains Mono, self-hosted
assets/             renders: WebP for the page, PNG originals kept
content/            markdown: journal posts, pages, the Bull Bands copy
_headers            Cloudflare Pages security + cache headers
robots.txt sitemap.xml
```

## /bands/ — the Bull Band promo

`design/Bull Band Promo.dc.html` is the first page here to use `<x-import>`, and
it broke two site rules the first time it was looked at. Both are fixed in the
build rather than by loosening the CSP, because the CSP is right — the export was
authored for a preview host that has none.

**1. A `.jsx` x-import pulls Babel off unpkg.** `support.js` picks its loader by
file extension, and for `jsx` it injects `@babel/standalone` (3 MB) from a
third-party host. `script-src 'self'` blocks it, the module never runs, and the
page renders *nothing*. So `jsx-compile.js` transforms the three modules ahead of
time using the same Babel and the same options the runtime would have used —
verified against the exact SRI hash `support.js` pins for it — and the build
repoints the import at the compiled `.js`. The runtime then takes its `js` branch
and never reaches `ensureBabel()`. Confirmed in a real browser: three
`x-import: loading … (js)` lines, zero requests to unpkg.

**2. The helmet's three inline `<script>` blocks are blocked too.** `OM_SCENES`,
`OM_PLAYBACK` and `TWEAK_DEFAULTS` are inline, the helmet manager re-creates them
as inline scripts in `<head>`, and this CSP has no `'unsafe-inline'` — so the
stage would mount with no scenes. Same failure `bp-boot.js` already records, same
fix: the build *extracts* them, verbatim, into `bands/scene.js`. The design stays
the one source; nothing is retyped.

`OM_PLAYBACK` is the one line rewritten rather than copied. The export loops a
1920×1080 composition forever; `bands/scene.js` gives a `prefers-reduced-motion`
visitor `{"mode":"times","count":1}` — the engine's own documented playback
contract — so they get one pass and a still frame instead of an endless one.

The promo is the hero and the written page sits under it, always visible, built
from `content/bands-static.md`. It is deliberately **not** a prerender that gets
removed: a visitor who can run the animation still needs to read what the thing
is made of and what is not settled yet.

**The two promo images are not in the repo.** They live in the design project as
`uploads/pasted-1786883724308-0.png` (the band) and
`uploads/pasted-1786883900528-0.png` (the coin), and the design file read caps at
256 KiB, which neither fits under. Export them and drop them in as
`assets/bull-band.webp` and `assets/bull-coin.webp` (`.png`/`.jpg` also work).
Until then `build.py` prints exactly what is missing, does not publish `/bands/`,
leaves it out of the sitemap, and clears any stale output — a page whose images
404 is worse than no page.

## Deploying

Cloudflare Pages, connected to this repo:

- **Build command:** `python3 build.py`
- **Build output directory:** `/` (the repo root)
- **Root directory:** `/`

`index.html` is committed, so a Pages project with **no build command at all**
also works — point it at the repo root and it serves as-is. Running the build
in CI is better: it re-derives the page from the design export and fails loudly
if the vendored React ever stops matching what `support.js` expects.

Custom domain `bullprintlab.com` is attached in the Pages dashboard
(Workers & Pages → the project → Custom domains). DNS is already in Cloudflare,
so it provisions the certificate itself; no `CNAME` file is needed.

## Checking it before you push

```bash
python3 build.py && python3 -m http.server 8788 --bind 127.0.0.1
```

Then open http://127.0.0.1:8788/. The page is verified by loading it in a real
browser and confirming three things: React mounts (no `<x-dc>` left in the DOM),
no template expression renders literally, and every network request is
same-origin.

## Not yet wired

The order and contact forms are **front-end only** — they validate and show
their success state, but nothing is submitted anywhere. They need an endpoint
(a Pages Function, or a form service) before the site can take a real order.
