# BRAND.md — BullPrint Lab identity system

The visual reference is `design/BullPrint Brand Kit.dc.html` (18 sheets — open it in a browser). This file is the machine-readable version: everything an implementer needs without reading a picture. Where the two disagree, the kit is correct and this file is stale — say so rather than guessing.

Companion: `README.md` (the site build spec) · `tokens.css` · `patterns.css` · `assets/marks.svg.txt`.

---

## 1. Hierarchy

Seven named things. Each has one job; none of them are interchangeable.

| | Name | Role |
|---|---|---|
| 01 | **BULLPRINT LAB** | Builds the things. The company. |
| 02 | **BrAhMa** | Intelligence inside the Lab. The AI. |
| 03 | **BULL ON / BULL OFF** | BrAhMa's verdict system. |
| 04 | **BEST IN BULL™** | Finished quality mark, applied per unit after inspection. |
| 05 | **THE BULLPRINT** | Publishes the story. Editorial masthead. |
| 06 | **BULLMAKER** | Commissioned / custom creator. |
| 07 | **BULLTAKER** | Owner of the numbered physical object. |

**The rule that holds it together:** everything can carry the lab; only inspected units carry the bull.

---

## 2. Names and spelling

- **BULLPRINT LAB** — uppercase in display, "BullPrint Lab" in prose. Never hyphenated to a product name.
- **BEST IN BULL™** — always uppercase, always with the ™.
- **BrAhMa** — B-r-**A**-h-**M**-a. Capitals on positions 3 and 5, and the reason is that A·I is embedded in the breed name. **This is the only name in the system exempt from uppercase display styling** — `text-transform: uppercase` on BrAhMa is a bug. `BRAHMA`, `Brahma` and `brahma` are all wrong in copy. The URL slug is lowercase: `brahma.bullprintlab.com`.
- **BULLMAKER / BULLTAKER** — one word, uppercase in badges, "BullMaker" in prose.

### Naming architecture

```
LEVEL 01  HOUSE    BullPrint Lab
LEVEL 02  FAMILY   (unnamed until drop 003 — cattle breeds are the pool; BrAhMa is taken)
LEVEL 03  DROP     Drop 001 ₿ Edition          three digits, never reset, never skipped
LEVEL 04  UNIT     037 / 100 · BP-10MM-001     serial = object, profile = foot
```

Rules: families are real cattle breeds (Angus, Hereford, Charolais, Simmental). Editions name **what changed** — a material, a mark, a collaborator — never "Pro" or "Elite". One "bull" per name maximum. Drop numbers never skip, including for runs that die: a missing 004 is a question worth answering. If a name needs explaining in the sentence it appears in, it isn't the name.

**URLs:** content on paths (`bullprintlab.com/drops/001`), tools on subdomains (`brahma.bullprintlab.com`). Marketing authority compounds on one domain; an application with its own deploy and nothing to rank for is the exception.

---

## 3. Marks

Full copy-paste SVG in `assets/marks.svg.txt`. Three cuts, one silhouette:

| Mark | Use | Minimum |
|---|---|---|
| Golden bull, modelled (gradient fill) | Hero, seals, footer, ≥40px contexts | **40 px / 12 mm** |
| Golden bull, line cut (single weight) | Nav, badges, favicon, emboss, ≤32px | **16 px / 4 mm** |
| BEST IN BULL™ seal with genesis ring | Quality-mark moments, posters, certificates | **280 px / 40 mm** |
| Seal without hash ring | Hero lockup, footer, inline stamp | **28 px / 8 mm** |

The seal's inner bull is exempt from the 40px floor — the ring carries the mark at that size.

**Line-cut stroke weights** scale with size: 2.2@96px · 3.4@48 · 5@30 · 6@24 · 6.5@22 · 8@16. Put the stroke **on the paths**, never inherited through `<use>` — inherited paint is dropped when the DOM is cloned for screenshot, PDF or PPTX export, and the mark ships blank.

**Clear space** = X on all sides, where X is the height of the bull's muzzle plate (¼ of mark height). Nothing enters it.

**Misuse:** no stretching, recolouring, rotating, glow/neon, drop shadows, outlining the modelled master, or crowding the lockup. The mark is a stamp; stamps are flat and confident.

### The seal

Three rings: outer = the Bitcoin genesis block hash (`000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f`, 03 Jan 2009) at 7.2px with **letter-spacing .62em** — that value is what closes 64 characters into a full ring on r=90; changing the font size means re-tuning it (target computed length ≈562 of 565 units). Middle = BEST IN BULL™ · BULLPRINT LAB at 11px / .5em on r=64. Centre = modelled bull at scale .78.

Physical die: ≥40 mm for the hash to deboss legibly, 0.4 mm depth. Below 120px on screen, drop the hash ring entirely — never fake it with placeholder characters.

---

## 4. Colour, type, pattern

Full values in `tokens.css` and `patterns.css`. Summary:

**Ratio ≈ 85% black/graphite · 10% gold · 5% everything else.** Gold is a metal, not a highlighter: one gold thing per view — the mark, the CTA, or the number that matters.

Core: `--void #0B0B0D` · `--graphite #0E0E11` · `--panel #141418` · `--bone #F4F2ED` · `--gold #E8B23A` · `--gold-deep #8A6A1E` · `--btc #F7931A` (5% max, only where Bitcoin is literally the subject).

Never: purple/blue gradients, neon, gold on gold, trading green/red, or a flat CMYK gold build (reads as mustard — use foil or a spot metallic).

**Type:** Archivo (display + body, 400–900) and JetBrains Mono (every numeric, ID, status, eyebrow, nav item, CTA). Headlines uppercase at −3 to −4% tracking; body sentence case, 15–17px / 1.75, measure under 68 characters. **No border radius anywhere in the brand system** — the only rounded thing we make is the part.

**Patterns:** lattice field (seamless pointy-top hex, 27.712 × 48 tile, ratio 1 : 1.732 — hold it or the tiling seams), layer lines, CAD grid, dimension callouts. All data-URIs; no raster files in the identity.

---

## 5. Voice

Four principles: **show the number** (every claim carries a figure, material or tolerance) · **one joke, then work** (~one funny line per section; stack two and it reads as a meme account with a Shopify) · **publish the failures** (archived prototypes get the same typographic treatment as shipped ones) · **never oversell** (no medical claims, no fake scarcity, no countdowns, no invented stock numbers).

The humour gets attention; the quality earns the customer — in that order. And the joke always points at us, never at the audience.

### Taglines

**Locked, do not rewrite:** WE PRINT WHAT WE'RE BULLISH ON. (master) · VibePrints with real utility. (descriptor, always follows the master) · ONLY THE BEST EARN THE STAMP. (quality, pairs with the seal).

**Rotating** — one per surface, never two:
- *Product:* EXPRESSION, ENGINEERED. · GEOMETRY IS THE MATERIAL. · EVERY CELL EARNS ITS PLACE. · LATTICE OVER LOGOS. · TOLERANCES ARE A LOVE LANGUAGE.
- *Quality:* NOT EVERYTHING EARNS THE BULL. · IF IT WEARS THE BULL, WE STAND BEHIND THE PRINT. · THE JOKE IS THE HOOK. THE PRINT IS THE POINT. · NUMBERED, NOT MASS. · SOFT ON THE FOOT. HARD ON THE SPEC.
- *Culture:* STAY BULLISH. · BUILT DIFFERENT. PRINTED DIFFERENT. · PRINT WHAT YOU BELIEVE. · FROM THE LAB. · MADE IN THE LAB. WORN IN THE WILD. · FOLLOW THE BULLPRINT.
- *BrAhMa:* THE AI ON THE BULL. · Built to ride the iteration.

---

## 6. BULL ON / BULL OFF

The verdict on a **print** (maker/taker name a **person** — don't conflate them).

| | BULL ON | BULL OFF |
|---|---|---|
| Means | Inspected, numbered, stamped, shipping | Archived — failed or not good enough |
| Colour | Gold `#E8B23A` on black, seal present | `#5C5952` on black, dashed rules, no seal |
| Post form | "PROTO 003. BULL ON." + the spec | "PROTO 004. BULL OFF." + what broke |

A BullMaker's run can still come back bull off — they hear it first and nothing ships. **A brand that publishes its own bull-offs gets believed about its bull-ons**, so the bull-offs post as often as the bull-ons and the reason is never softened.

---

## 7. BullMaker & BullTaker

| | BULLMAKER | BULLTAKER |
|---|---|---|
| Who | Brings the mark — custom-bull client | Takes the number — drop owner |
| Earned at | Sample approved, run started | Unit inspected and shipped |
| Carries | BullMaker no. + their mark in the lattice | Serial NNN / 100 + profile ID |
| Badge | Outline lozenge, gold rule on black | Solid gold lozenge, knockout bull |
| Appears on | Custom cert card, request confirmation | Cert card, order confirmation, reprints |

**Guardrail:** these are earned titles, not loyalty tiers. No points, no ranks, no leaderboard, no token, nothing purchasable. The moment either can be bought, it becomes the thing this brand exists to avoid. The site reflects this — the order confirmation reads "BULLTAKER PENDING" because the serial is issued at inspection, not at checkout.

---

## 8. BrAhMa — the AI

The intelligence operating inside BullPrint Lab. **Authority over a workflow, not another chat window.** It reads the inspection, calls the verdict, prescribes the change in millimetres, and generates the next version.

### Verdict card — BULL OFF
```
PROTO 004 / TPU95A / V7                                    [BULL OFF]
Forefoot transition failed inspection.
Failure localized at lattice-density boundary.

BrAhMa RECOMMENDS
· Increase transition length 12 mm
· Move wall thickness 0.8 → 1.2 mm
· Preserve ₿ geometry
· Generate V8
                                                        [ RIDE AGAIN → ]
BrAhMa IS AN AI · A HUMAN SIGNS THE STAMP
```
Styling: dashed `rgba(255,255,255,.2)` verdict chip, `#5C5952` type, recommendations in mono at `#F4F2ED`, gold gradient on RIDE AGAIN.

### Verdict card — BULL ON
```
PROTO 005 / TPU95A / V8                                     [BULL ON 🐂]
GEOMETRY PASSED   PRINT PASSED   INSPECTION PASSED

→ ASSIGN SERIAL    → GENERATE CERT    → SEND TO BEST IN BULL
```
Styling: solid gold gradient chip with the line-cut bull knocked out in `#0B0B0D`, card border `rgba(232,178,58,.36)`, three outlined gold action buttons.

### Behaviour contract

**Does:** read inspections and call bull on/off with the reason · prescribe geometry changes in millimetres and generate the next version · fill a customer's build sheet from a plain description of their foot · say "I don't know" and hand to a human.

**Never:** diagnose anything or answer a medical question · **assign the stamp itself — BrAhMa recommends, a human signs** · quote a price, date or stock level it can't verify from the system · pretend to be a person or hide that it's a model.

**Voice:** brand voice, shorter. Verdict first, then the millimetres, then the action. Two sentences beats six. No preamble, no "great question". Funny only when the situation already is. Three exchanges without resolution → bullish@bullprintlabs.com.

**Disclosure:** every BrAhMa surface carries "BrAhMa IS AN AI" (or the fuller "· A HUMAN SIGNS THE STAMP" on verdict cards) at **9.5px minimum, never in a tooltip, never hidden**.

**Implementation note:** BEST IN BULL™ must be a human-gated state transition in the data model — the AI can propose it, but awarding it needs a human actor recorded on the record. If a model can award the stamp, the guarantee is worthless.

---

## 9. Applications

Specced visually in the kit — sheets 11 (A2 posters), 12 (packaging: box lid, certificate card, care card, sticker sheet, business card), 16 (the BTC ticker component), 18 (X header, avatar, bull on/off post templates, asset index).

Print: black stock, one gold foil hit, mono type. The unboxing should feel like receiving a machined part, not a sneaker collab.

Launch cadence (sheet 15): three posts a week, one always a verdict. Week 1 exist, week 2 teach, week 3 earn it, week 4 sell — the drop lands in week four, not week one. Never open with the product, never run a countdown, never post a render as if it were a photograph.

---

## 10. Non-negotiables

1. No medical or therapeutic claims, anywhere, by anyone — including BrAhMa.
2. No fake scarcity: no countdowns, no invented stock numbers. Drop status is an enum (`IN THE LAB · COMING SOON · LIVE · SOLD OUT · ARCHIVED`).
3. BEST IN BULL™ is per-unit and post-inspection. Never on a render, a prototype, a concept or merch.
4. Antimicrobial is **in testing and not claimed**. Do not upgrade that sentence without a filament spec and test data.
5. Bitcoin is culture and payment rail, not the brand. Orange stays under 5%; no charts, no price commentary, no forecast language.
6. BrAhMa is never uppercased and never unlabelled as AI.
