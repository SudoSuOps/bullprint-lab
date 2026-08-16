# ARCHITECTURE.md — Bull-Grade, Bull-Link, and what it takes to run them

Written 2026-08-16 against the drop brief. This is a review of what exists and a
proposal for what comes next. It changes nothing on disk. Where I am reporting a
fact I read off the repo I say so; where I am making a judgement call I say that
too, and I name the decision that is yours rather than mine.

---

## 1. What exists today

### 1.1 bullprintlab.com — `~/Desktop/bullprint-lab`

A static site on Cloudflare Pages. Single origin, no third-party subresource,
no database, no server-side state.

```
design/*.dc.html        9 Claude Design exports — the source of truth
build.py     1059 ln    design export -> index.html + /platform/ + GEO surface
blog.py       378 ln    content/blog/*.md -> /blog/<slug>/ (plain static, no runtime)
support.js   1911 ln    Claude Design runtime, as exported
functions/api/          4 Cloudflare Pages Functions
vendor/                 React 18.3.1 UMD, SRI-pinned against support.js
brand/                  BRAND.md, tokens.css, patterns.css, marks
content/                4 journal posts, 2 standalone pages
```

Nine routes ship, all in `sitemap.xml`:
`/` · `/store/` · `/bullmaker-bulltaker/` · `/platform/` · `/blog/` + 4 posts,
plus `/order/confirmed/` (unlisted).

The four APIs:

| endpoint | does | state |
|---|---|---|
| `GET /api/btc` | CoinGecko→Coinbase spot, 45 s edge cache, `ok:false` on failure | none |
| `POST /api/submit` | 3 forms → Turnstile → Resend | none |
| `POST /api/checkout` | Stripe Checkout session, build profile in `metadata` | Stripe only |
| `POST /api/stripe-webhook` | verified sig → emails the build sheet to the print queue | none |

**The single most important fact in this repo:** `stripe-webhook.js` deliberately
does not assign a serial, because "BEST IN BULL™ is a human-gated transition and
the serial mints at inspection, not at checkout." The confirmation page says
`BULLTAKER PENDING`. That rule is already correct for everything the brief asks
for, and it should survive intact.

### 1.2 The brand system already in the repo

`brand/BRAND.md` defines seven named things with one job each:

| | Name | Role |
|---|---|---|
| 01 | BULLPRINT LAB | the company |
| 02 | BrAhMa | the AI |
| 03 | BULL ON / BULL OFF | BrAhMa's verdict system |
| 04 | BEST IN BULL™ | per-unit quality mark, applied after inspection |
| 05 | THE BULLPRINT | editorial masthead |
| 06 | BULLMAKER | commissioned creator |
| 07 | BULLTAKER | owner of a numbered unit |

Plus a naming architecture (HOUSE / FAMILY / DROP / UNIT), a serial grammar
(`037 / 100 · BP-10MM-001`), and a URL rule: content on paths, tools on
subdomains. This is a real system, it is in production, and the brief overlaps
it without referencing it. See §3.

### 1.3 The spine in openfootlab-os

`~/Desktop/openfootlab-os` is a pnpm monorepo with an event-sourced core. It is
a different business, but it already contains most of what Bull-Link needs:

| package | LOC | what it gives Bull-Link |
|---|---|---|
| `events` | 875 | typed event families incl. `manufacturing-job-events`, `material-events`, `machine-events` |
| `persistence` | 500 | append-only Postgres event store + in-memory twin for tests |
| `manufacturing` | 2050 | job service, machine registry, material library, house `standards.ts`, a print job that can **refuse** |
| `defendable` | 461 | `Claim` / `Receipt{method, source, sha256, reproduce, at}` / `Verdict = gold\|close\|not-yet` |
| `model-registry` | 1468 | model runs, inference, health probes — the BrAhMa call surface |
| `api` | 929 | router + server + role→actor mapping |

`packages/defendable/src/claim.ts` is, almost line for line, the Bull-Grade
evidence model the brief describes. It already refuses to let a claim exist
without a receipt naming the method, the source, the hash and the command that
re-derives it.

### 1.4 The CAD that feeds it

- `openfootlab-os/models/bullslides2/` — the 3-part captured-band slide,
  DWG BPL-SL-2L-013-B, generator + spec + measured REPORT.json.
- `openfootlab-os/bullprint-cad/` — CadQuery ₿ insert V1, STEP/STL/3MF exports.
- `openfootlab-os/models/bullprint/` — sections, mechanics, flight sheet.

Every one of these already emits a machine-readable report with measured
geometry. That is the manufacturing half of a Bull-Link, and it is free.

---

## 2. What can be reused as-is

Keep. Do not rewrite.

1. **The whole static delivery model.** Single-origin, SRI-pinned React,
   self-hosted fonts, a CSP with no external hosts. This is a genuine asset and
   the brief's "crypto-native without generic Web3 branding" line is *earned* by
   it, not claimed.
2. **`blog.py`.** 378 lines of markdown → static HTML with no runtime, built
   precisely so non-executing crawlers can read it. This is already the
   Bullish Print engine; it needs richer front matter, not a replacement.
3. **All four Pages Functions.** The Stripe rail (cards + USDC on one session,
   no second crypto integration) is the right call and is done.
4. **The serial-at-inspection rule.** Already implemented, already documented.
5. **`brand/tokens.css` + `patterns.css`.** The design language the brief asks
   for exists and is tokenised.
6. **openfootlab-os `defendable`, `events`, `persistence`, `manufacturing`.**
   Extract, don't reinvent. See §4.
7. **The CAD generators.** They already produce measured provenance data.

---

## 3. Conflicts and technical debt

Ordered by how much they cost if ignored.

### 3.1 RESOLVED (D-01, D-03) — the brief renames things that already have names

Three of the brief's terms collide with shipped marks, and one collides with a
different meaning in the other repo.

| brief term | already exists as | verdict |
|---|---|---|
| Bullish Print | **THE BULLPRINT** (masthead 05) | Same thing. Keep the masthead; an issue of it is a Bullish Print. No conflict once stated. |
| Bull-Grade *(verdict on a project)* | **BULL ON / BULL OFF** (03) | Same mechanism. Bull-Grade is the *standard*; BULL ON/BULL OFF is the *verdict*. Both survive. |
| Bull-Grade *(applied to a physical unit)* | **BEST IN BULL™** (04) | **Real collision.** Two different gates — one editorial about a project, one metrological about a unit. Merging them destroys the thing that makes BEST IN BULL credible. Keep both, never let a project's Bull-Grade imply a unit's stamp. |
| Bull-Link *(owner)* | **BULLTAKER** (07) | Complementary. BullTaker is the person; Bull-Link is the record. |
| "They Run. We Print." | "We print what we're bullish on." | Straight replacement. ~6 places: `build.py` `TITLE`/`DESC`, `llms.txt`, OG tags, the design export, `blog.py` `BRAND`. |

Fourth collision, outside this repo: in `openfootlab-os`, **"Bull-Grade" already
names a qualified *material* list** (BG-01, BG-02 …) with an open receipt gap
file against it. Three meanings of one phrase across two businesses is how a
standard stops meaning anything. One of them has to be renamed.

### 3.2 BLOCKER — there is nowhere to put a Bull-Link

There is no database. Not a small one — none. Units, editions, owners,
manufacturing events, assessments and provenance all need durable state, and the
only persistence in the system today is Stripe `metadata`, which is a payment
record that happens to carry a build profile.

Everything in Phase 1 items 7–8 of the brief is blocked on this one decision.

### 3.3 HIGH — "design export is the source of truth" cannot carry a live homepage

`build.py` takes `design/BullPrint Lab Site.dc.html` and applies ~15 **exact
string substitutions** to it (`wire_forms`, `link_store`, `link_footlabos`,
`link_openfootlab`, `route_ticker`, `platform_compute`, asset repoints, font
swaps). Each one `sys.exit`s if its needle is missing — good discipline, and the
reason the build is trustworthy today.

It is also the reason the brief's homepage cannot be built this way. "WHAT'S
BULL-GRADE RIGHT NOW?" is a data-driven feed. You cannot regex a feed into a
design export and keep either one honest.

This does not mean abandoning the design. It means inverting the relationship
for the dynamic surfaces: the design supplies the *component*, a JSON file
supplies the *content*, and the build renders one into the other. Static
sections stay exactly as they are.

### 3.4 HIGH — `unsafe-eval` becomes a liability the moment ownership is on the page

`_headers` allows `script-src 'unsafe-eval'` because the dc runtime compiles
templates with `new Function`. Fine for a marketing page. Not fine for
`/link/<unit>` if that page ever shows an owner, a wallet, or a claim action.

Rule: **every Bull-Link page is statically rendered, no runtime, like the
journal.** They are also the pages an AI crawler most needs to read.

### 3.5 MEDIUM — the medical firewall

`llms.txt` states plainly that BPL inserts "are not medical orthotics, not
patient-specific orthoses and not validated medical devices." OpenFootLab is the
clinical brand, with a `PHILOSOPHY.md` whose prime directive is to maximise
healthy days rather than hardware sales, and crew boundaries that forbid the
client-facing voice from interpreting clinical findings.

Sharing *code* between BPL and OFL is fine and correct. Sharing a **database**,
a **brand surface**, or a **claim vocabulary** is not. If BPL adopts the OFL
spine it takes its own deployment and its own data plane, and the word
"defendable" must not travel across the wall attached to a health claim.

### 3.6 LOW — doc drift in `build.py`

The module docstring numbers two different steps `5.`, and step 5 "repoints the
contact address" describes a patch that commit `e9c6dd1` removed (`bullish@` is
a real mailbox now and is used in `blog.py:210`, `build.py:765`, `store.md:39`).
One-line fix; noted so it does not get read as a live behaviour.

---

## 4. Proposed architecture

### 4.1 The shape

Three planes, one object model, one direction of dependency.

```
  PRESENTATION            bullprintlab.com — Cloudflare Pages
    static pages          design exports + blog.py + feed.json renderer
    edge functions        /api/* — thin, no business logic
                                  │
                                  │  reads a published JSON snapshot
                                  │  writes only through /api/mfg + /api/link
                                  ▼
  RECORD                  bull-link service — the only stateful thing
    event store           append-only; provenance is a PROJECTION, not a table
    projections           feed.json, project pages, unit records
    gates                 human approval before anything publishes
                                  ▲
                                  │  emits events
                                  │
  LAB                     BPL compute (BrAhMa) + the printers + CAD
    discover/research     proposes; never publishes
    generate              /platform BullSpec -> CadQuery/OpenSCAD
    manufacture           print jobs, machines, materials, QC
```

**The one rule that makes this work: the presentation layer never queries a
database at request time.** The record service publishes a signed JSON snapshot;
Pages serves it. That keeps the site single-origin, keeps the CSP closed, keeps
it fast, and means the record service can be down without the shop being down.

### 4.2 Build vs reuse

Build the record service **on the openfootlab-os packages**, in its own
deployment with its own Postgres. Concretely:

1. Promote `events`, `persistence`, `defendable` to a shared layer
   (`@bullhouse/*` or keep `@openfootlab/*` and depend on it — naming is a
   decision, the dependency direction is not).
2. `packages/manufacturing` is 80 % reusable as-is: `machine-registry`,
   `material-library`, `job-service`, and `standards.ts` all apply to slides,
   bands and bits without modification.
3. New package `bull-link`: the entities in §5 and their projections.
4. New package `bull-grade`: assessments, signals, the editorial gate.

What this buys: an append-only event log where provenance is *derived* rather
than stored, receipts on every claim, and a print job that can refuse — all
already written and tested.

What it costs: BPL takes on a Postgres and a deploy target it does not have
today. That is the real price of Phase 1 items 7 and 8, and it is unavoidable.

### 4.3 Provenance is a projection, not a record

Do not create a `bull_links` table with 18 columns. A Bull-Link is what you get
when you fold the event stream for one unit:

```
UnitMinted            edition, serial, profile_id
GeometryDerived       spec sha256, generator commit, measured report
JobQueued             machine, material lot, gcode sha256
JobCompleted          duration, mass, operator
Inspected             verdict, findings, BEST IN BULL yes/no
Shipped               to whom
Claimed               owner (email | wallet), at
Anchored              external attestation, if and when it exists
       ─────────────────────────────────────────────
       fold  ->  the Bull-Link shown at /link/<unit>
```

Every one of those carries a `Receipt`. The public page is the fold. Nothing is
mutable, so nothing can be quietly corrected, which is the entire point.

---

## 5. Core data model

Aggregates in **bold**; the rest are value objects or projections.

```
Project            slug, name, chains[], links[], first_seen
  EthosProfile     snapshot: score, vouches, at, source_url, sha256   [immutable]
  Signal           kind, value, receipt{method,source,sha256,reproduce,at}

BullGradeAssessment
  project_id, signals[], candidate_score  (BrAhMa — research tool, labelled)
  verdict: bull-on | bull-off | not-yet    (human — the gate)
  editor, decided_at, published_at
  rationale_md, disclosure: none | sponsored | collaboration

BullishPrint       issue_no, slug, title, project_id?, assessment_id?, body_md
                   (an issue of THE BULLPRINT — lives in content/blog/, extended front matter)

ProductFamily      slides | bands | bits | lab          [static, 4 rows, in code]
ProductEdition     family, project_id?, name, colorway, size_run, count, opens_at, closes_at
PhysicalUnit       edition_id, serial_n, serial_of, profile_id?, status
ManufacturingEvent unit_id, kind, machine_id, material_lot, artifact_sha256, operator, at
Inspection         unit_id, verdict, findings[], best_in_bull: bool, inspector, at

BullTaker          identity: email | wallet, units[]          (the person)
BullMaker          identity, mark_asset_id, editions[]        (the person)
BullLink           = projection over (PhysicalUnit + its events)   [derived, never written]

Drop               nnn, editions[], opens_at, story_id
Order              stripe_session_id, profile_id, unit_id?    (unit assigned at inspection)
DesignAsset        sha256, kind, generator_commit, spec_sha256
OracleAttestation  subject_sha256, network, tx, at            [Phase 3, nullable forever]
```

Identity grammar, following `brand/BRAND.md`:

```
edition   BULL-SLIDE-ETHOS-2026
unit      BULL-SLIDE-ETHOS-2026-0042      -> /link/bull-slide-ethos-2026-0042
serial    042 / 250
```

The brief's `BULL-SLIDE-ETHOS-0042` drops the year; `BRAND.md` says drop numbers
never reset and never skip. Adding the edition year keeps both true.

---

## 6. Frontend routes

Existing routes keep their URLs. `/store/` is the one that changes meaning.

| route | status | what it is |
|---|---|---|
| `/` | **rebuild** | WHAT'S BULL-GRADE RIGHT NOW — feed of current assessments over the existing hero |
| `/bull-grade/` | new | index of every assessment, bull-on and bull-off both |
| `/bull-grade/<project>/` | new | the living project page — score, why, the print, Ethos snapshot, drops, units |
| `/insoles/` | new | Drop 001, live — the only thing you can actually buy today |
| `/slides/` | new | Drop 002, in the lab |
| `/bands/` | new | Drop 003, in the lab — headbands |
| `/store/` | keep | the three-item line index |
| `/link/<unit>/` | new | **the Bull-Link record. Static. No runtime. QR/NFC target.** |
| `/drops/<nnn>/` | new | drop story + edition status |
| `/blog/` `/blog/<slug>/` | keep | THE BULLPRINT — extend front matter with `project`, `assessment` |
| `/bullmaker-bulltaker/` | keep | the titles page, unchanged |
| `/platform/` | keep | BrAhMa's CAD workspace |
| `/order/confirmed/` | keep | unchanged; still says BULLTAKER PENDING |

Four families, four verbs, and a catalogue that stays short by construction —
`ProductFamily` is four rows in code, not a table anyone can add to.

## 7. APIs

Existing four stay. New ones, all same-origin Pages Functions, all thin:

| method | path | auth | notes |
|---|---|---|---|
| GET | `/api/link/:unit` | public | the fold. cacheable, no PII, no owner identity |
| POST | `/api/link/:unit/claim` | owner proof | email magic link **or** wallet signature. Never mints. |
| GET | `/api/bull-grade` | public | the homepage feed. served from a published snapshot |
| GET | `/api/bull-grade/:project` | public | one assessment + its signals + receipts |
| POST | `/api/mfg/event` | lab token | the only write path from the floor. idempotent on `(unit, kind, at)` |
| GET | `/api/editions/:id` | public | availability, remaining count |
| POST | `/api/inspect/:unit` | crew | mints the serial and the BEST IN BULL™ verdict. **Human only.** |

`/api/inspect` is the one endpoint BrAhMa must never hold a credential for.

## 8. AI integration points

BrAhMa runs on the fleet described in `build.py:platform_compute` — RTX PRO 6000
(96 GB, in-house, Muse-Glimmer-30B resident) with a 5090 and a 3090 taking public
overflow. `packages/model-registry` is the call surface.

| stage | what BrAhMa does | what it may NOT do |
|---|---|---|
| Discover | watch communities, onchain activity, Ethos, dev activity → **candidate queue** | create a project page |
| Research | draft the brief, assemble the signal table with receipts | publish |
| Evaluate | compute the candidate score, label it a research tool | set the verdict |
| Create | BullSpec → CadQuery/OpenSCAD geometry, colorways, Bull Button variants | release a design |
| Manufacture | schedule, estimate, refuse out-of-standard jobs | pass inspection |
| Verify | assemble the Bull-Link fold | mint the serial |
| Publish | render the snapshot | approve it |

**One rule, stated once: BrAhMa proposes, a human publishes.** Wire it as a queue
with an approve step. Not a cron that posts. The moment an unreviewed model
output carries a Bull-Grade verdict, the standard is worth nothing, and that is
the only asset in the brief that cannot be rebuilt.

## 9. Ethos integration

- Read-only adapter, in the record service, never in the browser (the CSP
  forbids the origin and should keep forbidding it).
- Every read is stored as an **immutable snapshot** with `at`, `source_url` and
  `sha256`. A project page shows "Ethos 87, read 2026-08-14", never a live
  number that silently changes under a published assessment.
- Ethos is an **input to** Bull-Grade, weighted and disclosed. It is never the
  output. The brief is right that BPL owns the editorial judgment; the way to
  make that true in code is that `verdict` has a human `editor` field and no
  default.
- Failure is a state: adapter down → the page says the snapshot's age, it does
  not hide the field.

## 10. Chainlink / Bull-Link on-chain

Honest reading: **nothing in Phase 1 or Phase 2 needs a chain.**

A Bull-Link's job in Phase 1 is to let the owner of a physical object see its
real history. A hash-chained append-only log signed by BPL does that, and
`packages/defendable` already computes the hashes. Anchoring buys exactly one
thing: verification *without trusting BPL*. Until someone external needs that,
it is cost and dependency for a marketing sentence — which the brief itself says
not to do.

So, staged by what each step actually buys:

1. **Now** — sha256 every artifact (spec, mesh, gcode, report). Publish the unit
   record with its hashes. Anyone can re-derive; nothing is on a chain yet.
2. **When there is a reason** — periodically publish a Merkle root of all unit
   records. One transaction covers thousands of units. Cheap, and it makes
   "we did not backdate this" checkable.
3. **Escrow, when a collaboration needs it** — USDC in a contract, released on
   an *objective* milestone (units shipped, drop closed). The brief already says
   not to oracle-verify subjective work; the enforcement of that is that only
   milestones the record service already emits as events can be oracle
   conditions. Everything else needs a manual approval key and a dispute path.
4. **Oracle-backed Bull-Grade** — only if an outside party needs to verify the
   *inputs* to an assessment. Attest the signal snapshot hash, never the verdict.
   The verdict is editorial and should stay legibly human.

NFC/QR: the tag encodes `https://bullprintlab.com/link/<unit>` and nothing else.
No wallet, no key, no chain reference on the tag. The tag can outlive any chain.

## 11. Manufacturing & provenance

The floor already produces everything needed; it just isn't captured.

```
CAD generator  ──> spec.json + REPORT.json + mesh        sha256 each  ─┐
slicer         ──> gcode                                  sha256      ─┤
printer        ──> job start/end, machine, material lot               ─┼─> events
inspection     ──> verdict, findings, mass, dimensions                ─┤
finishing      ──> sewing, Bull Button set, colorway                  ─┘
                                    │
                                    └──> serial minted  ──> BullTaker  ──> /link/<unit>
```

Three things to get right:

1. **The material lot, not just the material.** `standards.ts` already knows
   TPU 95A from 90A from PEBA; a Bull-Link needs the *spool*. Chemistry
   (polyester vs polyether TPU) is a standing open gap in the other repo and it
   decides wet durability. Record the lot from day one or it is unrecoverable.
2. **The generator commit.** A slide is re-derivable only if the record says
   which commit of `bullslides2_gen.py` and which spec sha256 built it. This is
   what makes BEST IN BULL™ mean "re-derivable byte for byte" rather than
   "we looked at it."
3. **Inspection is the mint.** Already true. Keep it true when this is
   automated — the automation assembles the record and stops.

## 12. Build order

Phase 1 — the record exists and the site can read it. No chain, no wallet.

1. ~~Resolve the naming (§3.1).~~ **Done — D-01, D-03.**
2. Stand up the record service: extract `events`/`persistence`/`defendable`,
   add `bull-link`, one Postgres, one deploy target.
3. `ManufacturingEvent` + `PhysicalUnit` + `Inspection`; wire `/api/mfg/event`
   and `/api/inspect`.
4. `/link/<unit>/` as a statically rendered page from the fold. This is the
   first thing that makes a physical object feel individual, and it is the
   cheapest.
5. Product families: split `/store/` into `/slides/ /bands/ /bits/ /lab/`.
6. `BullGradeAssessment` + `/bull-grade/<project>/`, editorial gate, disclosure
   field. Ethos as a snapshot adapter.
7. Homepage feed from a published snapshot.
8. Extend `blog.py` front matter to link an issue to a project and assessment.

Phase 2 — identity and automation.
Owner claim (email, then wallet). NFC/QR on Bull Bits. BrAhMa discover/research
queue with the human approve step. Gated drops keyed on unit ownership.

Phase 3 — external verification.
Merkle anchoring. Escrow on objective milestones. Oracle attestation of signal
snapshots. Autonomous discovery, still gated.

---

## Decisions taken — 2026-08-16

These were open questions in the first draft of this file. They are settled now,
and the sections above are written against them.

### D-01 · The drop's vocabulary LAYERS on `brand/BRAND.md`. It does not replace it.

Nine named things, each with one job. Nothing retires.

```
BULLPRINT LAB     the house
BrAhMa            the AI
BULL-GRADE        the standard
  BULL ON / OFF   the verdict on a project
BEST IN BULL™     the gate on a unit          <- stays separate, never merges
THE BULLPRINT     the masthead
  Bullish Print   one issue of it
BULLMAKER         brings the mark
BULLTAKER         takes the number
  Bull-Link       that unit's record
```

The load-bearing half of this decision is the fourth line. A project's Bull-Grade
says BullPrint Lab found qualities worth recognising. A unit's BEST IN BULL™ says
this object was inspected and is re-derivable byte for byte from its spec. They
are different kinds of claim with different evidence, and a project being
Bull-Grade must never imply anything about a physical unit. `BullGradeAssessment`
and `Inspection` are separate aggregates in §5 for exactly this reason, and no
code path may derive one from the other.

Consequence for §3.1: only the tagline is a straight replacement.
"They Run. We Print." supersedes "We print what we're bullish on." in
`build.py` `TITLE`/`DESC`, `llms.txt`, the OG tags, the design export and
`blog.py` `BRAND`.

### D-02 · The record service is the openfootlab-os spine, deployed with its own data plane.

`events`, `persistence`, `defendable` and `manufacturing` are promoted to a
shared layer and consumed by BullPrint Lab. BPL runs **its own instance and its
own Postgres** — same code, separate data.

This is what makes §3.5 architectural rather than a promise: BPL and OpenFootLab
can never read each other's records, because there is no connection string that
reaches. Shared code, split state. The word "defendable" travels; a health claim
does not.

### D-04 · Three products. Insoles, slides, headbands. Nothing else.

The rule is one sentence: **we do not offer what we do not print.**

That retires Bull Swims (a water shoe never printed and never costed against a
real machine) and the Bull Heel Cup (parked behind an open question about its own
cut line). It also retires **Bull Bits and Bull Lab** from the drop brief before
they ever existed — Bull Lab in particular is a category for experiments, which
is a catalogue with a better name. And it forces the headband to change
definition: the export's own copy called it *"the first BullPrint product that
isn't printed"* and admitted *"nothing on our floor makes it."* The headband we
offer is the one with a **printed TPU Bull Button** sewn through the mesh. The
button is the print, and the print is why it is ours to sell.

Wristbands go with it — the product is a headband, singular.

This is enforced rather than remembered. `build.py` carries `THE_LINE` and
`RETIRED`, `purge_line()` corrects the design export mechanically on the way
through, and `check_line()` fails the build if a retired name reaches any
published page. It caught a real leak on its first run: `prerender.html` — the
static copy non-JS crawlers read — still carried BULL SWIMS after the live app
had stopped rendering it, which is the worst version of that bug.

Supersedes the drop brief's four product families. Where the brief and this
disagree, this wins.

### D-03 · The material list gives up the name "Bull-Grade".

`BG-01` / `BG-02` in openfootlab-os becomes the house material standard under
another name. It is internal, has no public surface, and this drop makes
Bull-Grade a public standard — two meanings would spend it.

Open sub-task, not yet done: pick the replacement name and sweep it through
`models/bullslides/.claude/agent-memory/`, `packages/manufacturing/src/`, and the
materials-engineer memory that currently records
`project_bullgrade_receipt_gaps`. Until that sweep lands, a reader of the other
repo will still find the old meaning.
