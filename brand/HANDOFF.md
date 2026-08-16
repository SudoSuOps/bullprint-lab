# Handoff: BULLPRINT LAB — full site

Repo: **github.com/SudoSuOps/bullprint-lab** · Deploy: **Cloudflare Pages** → bullprintlab.com
Contact: bullish@bullprintlabs.com · X: @bestinbull

---

## What this is

> **Read `BRAND.md` first** — it carries the identity system (hierarchy, marks, naming, voice, BULL ON/OFF, BullMaker/BullTaker, and the BrAhMa AI spec). This file covers the site build.

A complete, working design for the BullPrint Lab marketing + commerce site: 12 sections, three interactive instruments, two lead-capture forms and one order build sheet. Build it in the repo as a real app.

**The primary reference is `design/BullPrint Lab Site.dc.html`.** Open it in a browser — it runs. Everything below documents it.

`design/BullPrint Lab.dc.html` is the design-exploration board (brand kit sheet + mark development + the order-form study). Use it as the brand reference; it is not the site.

`design/support.js` is the runtime for those two reference files only. **Do not ship it.** Both references are authored in a streaming component format with inline styles; do not carry the inline styles across — lift the values into `tokens.css` (provided) and real components.

## Fidelity

**High-fidelity.** Colors, type, spacing, copy, interaction behaviour and derived-value maths are all final and specified. Recreate faithfully; the layout is fluid (clamp + auto-fit grids) rather than two fixed breakpoints, so it should be built responsive from one implementation, not as separate desktop/mobile pages.

## Stack recommendation

Nothing here requires a specific framework. Next.js (App Router) on Cloudflare Pages is the natural fit: static-render every section, and the only server work is three POST endpoints (order, custom request, contact) plus the Stripe/Coinbase webhooks. React state per section maps 1:1 to the reference's state object.

---

## Section inventory

Numbered as they appear on the page (the eyebrow number is part of the design):

| # | id | Section | Interactive? |
|---|---|---|---|
| — | `hero` | Hero — headline, dual CTA, spec strip, seal | — |
| — | — | **BTC spot ticker** (above nav) | live fetch, 60s poll |
| — | — | Microcopy ticker (marquee) | CSS animation |
| 01 | `bullprint` | What is a BullPrint? | — |
| 02 | `honeycomb` | Why honeycomb? — **live lattice instrument** | 2 sliders + 2-state toggle |
| 03 | `drop` | Featured: Drop 001 ₿ Edition + **Ten points on quality** | — |
| 04 | `exploded` | Cracked open — **exploded build-plate view** | slider + render/wireframe |
| 05 | `custom` | Custom Bull by Design — **special-order request form** | form + validation + confirm |
| 06 | `lab` | The Lab — pipeline + lab notes | hover states |
| 07 | `bull` | BEST IN BULL™ — genesis-hash seal | — |
| 08 | `drops` | Drops grid — 4 cards, 5 possible statuses | hover states |
| 09 | `journal` | THE BULLPRINT — featured essay + 3 drafts | hover states |
| 10 | `order` | Tell us about your shoes — **build sheet + checkout** | 6 fields + validation + confirm |
| 11 | `about` | About + stats | — |
| 12 | `contact` | Contact us — tiles + message form | form + validation + confirm |
| — | — | Footer | — |

Nav (sticky, scroll-spy): LAB · DROPS · CUSTOM · THE BULLPRINT · CONTACT, with a `LATEST DROP →` CTA to `#drop`. Under 900px the links collapse into a drawer toggled by the two-rule button; the drawer adds a `BUILD YOUR INSERT →` CTA to `#order`.

---

## The three interactive instruments

These are the parts most likely to be lost in a rebuild. They are not decoration — they carry the "geometry is the material" thesis.

### 02 · Live lattice (Why honeycomb?)

Two sliders — **cell size** 5–10 mm (step 0.5, default 7) and **wall thickness** 0.8–2.4 mm (step 0.1, default 1.2) — plus a **density map** radio (ZONED / UNIFORM).

The lattice panel is a CSS `background-image` holding an inline SVG data-URI of a seamless pointy-top hex tile. Both inputs change it live:
- `background-size` = `round(cell × 4.6)px` wide, and height = `round(width × 48 / 27.712)` (the tile ratio 1 : 1.732 must hold or the tiling seams).
- the tile's `stroke-width` = `wall × 0.9`, regenerated into the data-URI on each change.

Derived readouts, all from the same two values:
```
stiff     = (wall / 2.4) * 0.62 + ((10 - cell) / 5) * 0.38
flexIndex = clamp(round(100 - stiff * 88), 8, 97)        // shown as "NN / 100" + a gold progress bar
cellCount = round(21000 / cell² / 10) * 10               // "N,NNN CELLS"
mass      = round(58 + wall * 16 - cell * 2.2)           // "NN G"
height    = (4.2 + (cell - 5) * 0.36).toFixed(1)         // "N.N MM"
readsAs   = flex > 74 "SOFT · TRAINER" | > 46 "BALANCED · DAILY" | > 26 "SUPPORTIVE · COURT" | else "RIGID · PLATE-LIKE"
```

### 04 · Exploded view (Cracked open)

Three copies of the hero render stacked in a `3/2` box, all `mix-blend-mode: screen` (the PNG has a black background — screen is what makes it composite cleanly on the grid). A **separation** slider 0–100 (default 34) drives `translateY` of ±`explode × 0.62`px on the outer two layers and prints `explode × 0.18` as a millimetre readout. Outer layers fade in at `explode > 4`.

A **RENDER / WIREFRAME** toggle switches the filter. Wireframe is `grayscale(1) brightness(2.4) contrast(3.4) opacity(.5)` with the layer opacity dropped to 0.34 and the hex overlay raised to 0.8. **Do not use `invert()`** — on a black-background PNG under `screen` it floods the stage white. That was a real bug.

Zone list (fixed copy): 01 CONTACT SURFACE 1.2 MM · 02 ZONED LATTICE CORE 4.6 MM · 03 BASE MEMBRANE 0.9 MM, total stack 6.7 MM. The caption must stay: the part prints as one continuous piece; the separation is explanatory only.

### 10 · Order build sheet

Fields, in order: **01 SIZE (US)** 6–14 · **02 WIDTH** narrow/medium/wide · **03 ARCH** low/medium/high · **04 FIT PROFILE** men's/women's/unisex · **05 SNEAKER** free text (**required**) · **06 SPECIAL NOTES** textarea, 240 max · **07 FEEL** 90A softer / 95A firmer · **08 CHECKOUT RAIL** Stripe / Coinbase Commerce.

A sticky spec panel derives, live:
```
profileId = "BP-" + size + width[0] + arch[0] + "-001"     // e.g. BP-10MM-001
arch map  = LOW {tile 32px, 8.0 MM, "FLAT"} | MEDIUM {28px, 7.0 MM, "STANDARD"} | HIGH {22px, 5.5 MM, "RAISED"}
            → drives BOTH the panel's lattice background-size AND the "MID CELL" label. One record, two labels;
              they drifted once and it read as sloppy on a brand selling manufacturing rigor.
last      = NARROW "STOCK LAST −4 MM" | MEDIUM "STOCK LAST" | WIDE "STOCK LAST +6 MM"
material  = "TPU / PEBA · " + (90A|95A)
printTime = 180 + size*7 minutes → "EST NH NNM"
price     = $99 USD / PAIR
```
Validation: sneaker required — on empty submit, border goes `#F7931A` and `TELL US THE SHOE — WE CUT THE OUTLINE TO IT` appears in a `role="status"` region. On success the form is replaced by a confirmation panel naming the chosen rail ("Stripe Checkout opens for the card payment." / "Coinbase Commerce opens with a Lightning invoice and an on-chain address."), showing profile ID, lattice pitch and print time, with EDIT PROFILE and EMAIL THE LAB.

---

## Commerce integration (not built — this is the wiring spec)

The reference stops at the confirmation state. In the repo:

1. **Stripe** — server-side Checkout Session. One price object for Drop 001 ($99/pair). Put the whole profile in `metadata`: `profile_id, size, width, arch, fit, feel, shoe, notes`. `success_url` returns to `/order/confirmed?session_id=…` and renders the same confirmation panel; `cancel_url` returns to `#order` with state intact.
2. **Coinbase Commerce** — create a charge with the same metadata, `pricing_type: fixed_price`, USD 99. Show the hosted charge page or embed. Handle the `charge:confirmed` webhook.
3. **Both rails write one order record.** The print queue needs the profile, not the payment — keep the profile row separate from the payment row and join on `profile_id`.
4. **Custom requests (05)** and **contact (12)** POST to the same handler with a `type` discriminator. The custom form carries a file (SVG/AI/PDF/PNG) — accept up to ~10 MB to object storage (R2 on Cloudflare) and put the URL in the email to bullish@bullprintlabs.com.
5. **No fake scarcity.** Drop status is an enum on content: `IN THE LAB · COMING SOON · LIVE · SOLD OUT · ARCHIVED`. Never a countdown, never a fake stock number. "001 / 100" is a real edition size — only show a serial once one is assigned.
6. Prices, edition sizes and statuses come from content, not hardcoded JSX.

---

## Accessibility — already designed in, keep it

- Skip link to `#hero`, visible on focus.
- `:focus-visible` ring: `2px solid #E8B23A`, offset 3px.
- Every chip group is a `role="radiogroup"` of `role="radio"` items with `aria-checked`, `tabindex="0"` and Enter/Space handlers. **If you rebuild these as real `<input type="radio">` + `<label>`, do — it's strictly better.** What must not happen is bare clickable `<div>`s.
- All hit targets ≥44px (chips have `min-height:44px`).
- Forms use `form / fieldset / legend / label`; errors are `role="status"` and referenced by `aria-describedby`.
- Decorative SVG is `aria-hidden`; meaningful marks carry `role="img"` + label. Card thumbnails are `role="img"` with `aria-label` (they are CSS backgrounds — see Performance).
- `prefers-reduced-motion`: freezes the microcopy marquee, kills smooth scroll, collapses transition durations. Apply it to scroll reveals too when you add them.
- Gold `#E8B23A` on `#0B0B0D` is ~9.8:1. Do not drop accent text below `#8A6A1E` on black for anything that must be read (that pairing is for decorative meta only).

## Performance

- The three PNG renders are the page weight. Serve AVIF/WebP with PNG fallback, explicit intrinsic sizes, `fetchpriority="high"` on the hero, `loading="lazy"` below the fold.
- Card thumbnails are CSS `background-image` deliberately: as `<img>` inside a templated list they fired requests for unresolved URLs. In a real framework `<img>` is fine — just make sure the src is resolved before render.
- Every pattern (lattice, layer lines, CAD grid) is a data-URI or gradient — no image requests.
- Scroll work is one `IntersectionObserver` (nav scroll-spy), one passive scroll listener (header background state) and one 60s interval (BTC rate) — all cleaned up on unmount. Do not add parallax or a rAF loop; the audience lands from X on a phone.

---

## BTC spot ticker

A slim strip above the nav inside the sticky header: status dot · ₿ BTC · price · 24h change · fetch time, with Drop 001 priced in sats pushed right. There is also an **IN SATS** row in the order spec panel.

**Data.** CoinGecko primary:
```
GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true
```
Coinbase spot as fallback (no 24h change — the change chip renders "24H —"):
```
GET https://api.coinbase.com/v2/prices/BTC-USD/spot
```
Poll every 60s; clear the interval on unmount.

**In production, do not call these from the browser.** Proxy through a Cloudflare Worker with a 30–60s edge cache: CoinGecko rate-limits by IP, and a first-paint dependency on a third-party API is a bad trade for a number this decorative. One cached Worker response serves every visitor.

**Degradation is a requirement, not a nicety.** If both endpoints fail, the price reads `RATE OFFLINE`, the dot goes `#5C5952`, and the sats figure reads `— SATS`. **A fabricated or stale-but-unlabelled price must never render** on a brand whose entire pitch is that claims come with verification.

**Sats maths:** `round(priceUsd / btcUsd * 1e8)`, thousands-separated. At $99 and $63,000/BTC that is ~157,000 sats. This is **display only** — checkout charges USD 99 on both rails. If you want to charge in sats, that is a pricing decision (spot at checkout, with a quote expiry) and it needs to be stated at the payment step.

**Accessibility:** the strip carries `aria-label="Bitcoin spot price"` and **`aria-live="off"`**. Do not give it `role="status"` — an ambient market ticker that mutates every 60s would interrupt screen-reader users continuously for the whole session. Live regions are for the result of a user action (the three form confirmations, which correctly use `role="status"`).

**Responsive:** the SPOT timestamp and the "DROP 001" label carry `data-tickmeta` and are hidden under 600px, leaving dot · ₿ BTC · price · change · sats on one line at 390px. All numerics use `font-variant-numeric: tabular-nums` so the sticky header does not reflow as digits change.

---

## Scroll reveals — deliberately absent from the reference

The reference file has **no scroll-reveal animation**, and that is intentional, not an omission.

Reveals were built and then removed: the design preview scrolls the iframe rather than the document, so no scroll event or IntersectionObserver entry ever reaches the page, and any content gated on "has this been seen" stayed permanently at `opacity: 0` — invisible in every screenshot, PDF and PPTX export, and stranded on any anchor jump or deep link.

In a normal browser this is not a problem, so add them in the real build — with these rules, which are what the failure modes taught:

1. **Never put the hidden state in an inline `style` attribute.** Use a class or data attribute + CSS. Inline styles mutated by JS get re-serialized from their mount-time value by DOM-clone consumers (screenshots, print, share thumbnails), which ships hidden content.
2. **Never let CSS hide content that only JS can reveal.** The hidden state must be applied by JS at mount, so a no-JS or clone render shows everything.
3. **Reveal on "reached", not "currently intersecting"** — `e.isIntersecting || e.boundingClientRect.top < 0` — or the anchor nav (every nav item on this site is an in-page jump) leaves skipped sections blank.
4. Motion spec: 12–16px rise + fade, 420ms, `cubic-bezier(.2,.8,.2,1)`, once per element, stagger ≤60ms, disabled under `prefers-reduced-motion`.

## Brand marks

`assets/marks.svg.txt` (v2) holds all three, copy-paste ready:
1. **Modelled golden bull** — gradient fill, viewBox 120×100. Use at **≥40px only**.
2. **Line cut** — same silhouette, single weight. Use at **≤32px**, favicon, emboss, single-colour print. Stroke scales with size: 2.2@96 · 3.4@48 · 5@30 · 6@24 · 6.5@22 · 8@16. Stroke goes **on the paths**, never inherited through `<use>` (it is dropped when the DOM is cloned for screenshot/PDF/PPTX export).
3. **BEST IN BULL™ seal, genesis ring** — outer track is the Bitcoin genesis block hash (`000000000019d66…0a8ce26f`, 03 Jan 2009) at 7.2px with **letter-spacing .62em**, which is what closes 64 characters into a full ring on r=90. Changing the font size means re-tuning the spacing (target computed text length ≈562 of the 565-unit path). Below ~120px, drop the hash ring entirely and use the plain ring + line-cut bull.

`assets/logo-footlab-master.png` is the client-supplied FOOTLAB lockup — final art, not to be redrawn.

Physical note: for a stamp die, the hash needs ≥40 mm to deboss legibly. The line cut holds down to 4 mm.

## Tokens, patterns, type

`tokens.css` and `patterns.css` are unchanged and authoritative — palette, type scale, spacing, the four background recipes, and the seamless hex tile geometry (27.712 × 48 viewBox, ratio 1 : 1.732).

Fonts: **Archivo** (display + body, 400–900) and **JetBrains Mono** (every numeric, ID, status, eyebrow, nav item and CTA). Self-host both for production. Square corners everywhere — the only radii in the design belong to the mockup frames, not the brand.

## Copy rules

- Headline, subheadline, section headings and all BEST IN BULL™ text are **verbatim from the client brief** — do not rewrite.
- **No medical or therapeutic claims anywhere.** The ten quality points are deliberately written as construction facts. The antimicrobial line states the additive is *in testing and not claimed* — do not upgrade that sentence without a filament spec and test data.
- Brand phrases (BUILT DIFFERENT. PRINTED DIFFERENT. · STAY BULLISH. · FROM THE LAB. · PRINT WHAT YOU BELIEVE.) appear roughly once per section, never stacked. Restraint is the joke's delivery mechanism.
- Material reads **TPU / PEBA**, with shore stated only as the 90A / 95A choice. No fixed shore in body copy.

## Files in this bundle

```
README.md                     ← this (site build spec)
BRAND.md                      identity system — read first
tokens.css                    design tokens
patterns.css                  4 background recipes incl. the seamless hex tile
assets/marks.svg.txt          bull (modelled + line) and the genesis seal, copy-paste SVG
assets/logo-footlab-master.png    client-supplied lockup
assets/insert-macro-hero.png      hero + exploded-view render
assets/insert-spec-sheet.png      annotated spec views
design/BullPrint Lab Site.dc.html ← THE SITE. open in a browser.
design/BullPrint Brand Kit.dc.html  18-sheet brand book — the visual source for BRAND.md
design/BullPrint Lab.dc.html      design board: early exploration, mark development, form study
design/support.js                 runtime for the two references. do not ship.
```

## Open items for the client

1. Price is $99 USD / pair — confirm before launch, and decide whether BTC pricing is spot-converted at checkout or fixed.
2. Edition size 100 for Drop 001 — confirm, and decide when serials are assigned (at order or at inspection).
3. Antimicrobial additive: claimable or not, pending test data.
4. Drop 002 and 003 copy is placeholder-grade; the statuses are real, the descriptions need the client's words.
5. THE BULLPRINT #001 needs its body copy — only the title and teaser exist.
6. Legal entity, returns policy and shipping regions are not written anywhere yet. Both checkout rails need them.
