#!/usr/bin/env python3
"""
BullPrint Lab — build the Printful store.

    python3 art/printful.py check     # which store am I pointed at
    python3 art/printful.py plan      # what would be created, with prices
    python3 art/printful.py create    # actually create it
    python3 art/printful.py products  # what is live now
    python3 art/printful.py delete ID # remove one sync product

PRICING
-------
The house rule is 15% over TOTAL cost, and total cost means blank + shipping —
not blank alone. Applied to the blank alone every line is negative: a tee
retails $12.94 against $9.25 + $4.99 shipping and loses $3.98 before Stripe
takes its cut. So retail = (variant_price + SHIP) * 1.15, computed PER VARIANT,
because Printful prices 2XL higher than S-XL and a flat retail would quietly
lose money on the big sizes.

At 15% a tee nets about $1.60 after Stripe. That is thin enough that one
customer-caused return wipes out eleven sales, and it is recorded here so the
number is visible rather than buried in a spreadsheet.

PRINT FILES
-----------
Printful FETCHES art from a public URL — it does not accept an upload from this
script. The files are served from this repo at bullprintlab.com/art/print/,
which is already public and already verified reachable (HTTP 200).

POSITION
--------
Given explicitly rather than left to auto-fit. Auto-fit scales art to fill the
placement, so a 9 inch seal drawn for a 9 inch chest would come back 12 inches
wide — the design intent silently rescaled. Every placement below states its
own area and the inches the sheet called for.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).parent
API = "https://api.printful.com"
TOKEN = (pathlib.Path.home() / ".config/bullprintlab/printful.token").read_text().strip()
ART = "https://bullprintlab.com/art/print"

SHIP = 4.99          # US, first unit of a one-item order
MARKUP = 1.15        # house rule


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + TOKEN,
                 "Content-Type": "application/json",
                 # Printful sits behind Cloudflare, which 403s the default
                 # Python-urllib signature with "error code: 1010". curl works,
                 # urllib does not, and the body is not JSON — which is what
                 # made the first failure look like a Printful outage.
                 "User-Agent": "BullPrintLab/1.0 (+https://bullprintlab.com)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            # Printful rate-limits at 120 req/min and answers 429 with a plain
            # body, not JSON — parsing it blind is how this first failed.
            if e.code == 429 and attempt < 3:
                wait = int(e.headers.get("Retry-After", 20))
                print(f"      rate limited, waiting {wait}s")
                time.sleep(wait)
                continue
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"code": e.code, "error": {"message": raw[:200]}}
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(5)
                continue
            return {"code": 0, "error": {"message": str(e)}}
    return {"code": 0, "error": {"message": "gave up after retries"}}


def retail(cost: float) -> str:
    return f"{round((cost + SHIP) * MARKUP, 2):.2f}"


# ── the line ────────────────────────────────────────────────────────────────
# blank        catalog product id
# placement    Printful placement key
# area         printfile pixels (w, h) for that placement
# art          file stem in art/print/
# inches       printed width the merch sheet calls for
# top_in       how far below the placement top the art sits
# colours      {colour name: [variant ids, ordered S..2XL]}

TEE_SIZES = ["S", "M", "L", "XL", "2XL"]
TEE = {
    "Black":   [11546, 11547, 11548, 11549, 11550],
    "Natural": [11556, 11557, 11558, 11559, 11560],
    "Gold":    [15849, 15850, 15851, 15852, 15853],
    "White":   [11576, 11577, 11578, 11579, 11580],
}

PRODUCTS = [
    # ── tees, Gildan 5000, DTG front, 12 x 16 in area ──────────────────────
    dict(name="Genesis Seal Tee", blank=438, placement="front", area=(1800, 2400),
         art="t01-seal-{ink}", inches=9.0, top_in=2.0,
         variants={"Black": "gold", "Natural": "ink", "Gold": "ink"}),
    dict(name="BULLISH Tee", blank=438, placement="front", area=(1800, 2400),
         art="t02-bullish-{ink}", inches=10.5, top_in=3.4,
         variants={"Black": "gold", "Natural": "ink"}),
    dict(name="WE PRINT. Tee", blank=438, placement="back", area=(1800, 2400),
         art="t03b-bull-{ink}", inches=11.0, top_in=2.4,
         variants={"Natural": "ink", "White": "ink", "Black": "gold"}),
    dict(name="BULL ON. Tee", blank=438, placement="front", area=(1800, 2400),
         art="t04f-bull-on-{ink}", inches=9.0, top_in=4.0,
         variants={"Gold": "ink", "Black": "gold"}),
]

INK_FOR = {"gold": "gold", "ink": "ink", "bone": "bone"}


def art_aspect(stem: str) -> float:
    """h/w of the actual PNG, so the position block carries a real height."""
    from PIL import Image
    im = Image.open(HERE / "print" / f"{stem}.png")
    return im.size[1] / im.size[0]


def build() -> list[dict]:
    """Turn the table above into Printful sync-product payloads."""
    out = []
    for p in PRODUCTS:
        aw, ah = p["area"]
        px_per_in = aw / 12.0 if aw == 1800 else aw / 12.0
        w = round(p["inches"] * px_per_in)
        for colour, ink in p["variants"].items():
            art = p["art"].format(ink=INK_FOR[ink])
            url = f"{ART}/{art}.png"
            h = round(w * art_aspect(art))
            if h > ah:                       # never taller than the placement
                h = ah
                w = round(h / art_aspect(art))
            svs = []
            for vid in TEE[colour]:
                svs.append(dict(
                    variant_id=vid, retail_price=None,   # filled from live cost
                    files=[dict(type=p["placement"], url=url, position=dict(
                        area_width=aw, area_height=ah,
                        width=w, height=h,
                        top=round(p["top_in"] * px_per_in),
                        left=round((aw - w) / 2)))]))
            out.append(dict(
                name=f"BullPrint Lab — {p['name']} ({colour})",
                colour=colour, art=art, url=url, inches=p["inches"],
                placement=p["placement"], variants=svs))
    return out


def costs() -> dict[int, float]:
    """Live variant cost, so retail is never computed off a stale number."""
    d = call("GET", "/products/438")
    return {v["id"]: float(v["price"]) for v in d["result"]["variants"]}


def cmd_check() -> None:
    d = call("GET", "/stores")
    for s in d.get("result", []):
        print(f"  store id={s['id']}  '{s['name']}'  type={s.get('type')}")
    n = call("GET", "/store/products?limit=100").get("result", [])
    print(f"  {len(n)} sync product(s) live")


def cmd_products() -> None:
    for p in call("GET", "/store/products?limit=100").get("result", []):
        print(f"  {p['id']}  {p['name'][:56]:<56} variants={p['variants']} synced={p['synced']}")


def cmd_plan(create: bool = False) -> None:
    price = costs()
    plan = build()
    print(f"  {len(plan)} product(s), {sum(len(p['variants']) for p in plan)} variants\n")
    for p in plan:
        lo = retail(min(price[v["variant_id"]] for v in p["variants"]))
        hi = retail(max(price[v["variant_id"]] for v in p["variants"]))
        print(f"  {p['name']}")
        print(f"      art {p['art']}.png  ·  {p['inches']} in  ·  {p['placement']}")
        print(f"      retail ${lo} (S-XL) – ${hi} (2XL)   "
              f"cost ${min(price[v['variant_id']] for v in p['variants']):.2f}"
              f"+${SHIP} ship")
        for v in p["variants"]:
            v["retail_price"] = retail(price[v["variant_id"]])
        if not create:
            continue
        body = {"sync_product": {"name": p["name"], "thumbnail": p["url"]},
                "sync_variants": [{k: v for k, v in sv.items()} for sv in p["variants"]]}
        r = call("POST", "/store/products", body)
        if r.get("code") in (200, 201):
            print(f"      CREATED id={r['result']['id']}")
        else:
            print(f"      FAILED {r.get('code')}: "
                  f"{r.get('error', {}).get('message', r)}")
        print()


def cmd_fix() -> None:
    """Re-PUT every live product with a complete position block.

    Printful returns position:null when it rejects the block, which looks
    identical to "no position given" — so this verifies afterwards instead of
    trusting the 200.
    """
    live = {p["name"]: p["id"] for p in
            call("GET", "/store/products?limit=100").get("result", [])}
    price = costs()
    for p in build():
        pid = live.get(p["name"])
        if not pid:
            print(f"  {p['name']}: not live, skipped")
            continue
        for v in p["variants"]:
            v["retail_price"] = retail(price[v["variant_id"]])
        r = call("PUT", f"/store/products/{pid}",
                 {"sync_product": {"name": p["name"], "thumbnail": p["url"]},
                  "sync_variants": p["variants"]})
        ok = r.get("code") in (200, 201)
        chk = call("GET", f"/store/products/{pid}")
        pos = (chk.get("result", {}).get("sync_variants") or [{}])[0]
        pos = (pos.get("files") or [{}])[0].get("position") or {}
        good = pos.get("width") is not None
        print(f"  {p['name'][:50]:<50} {'PUT ok' if ok else 'PUT FAIL'}  "
              f"position={'set ' + str(pos.get('width')) + 'px' if good else 'STILL NULL'}")


def cmd_delete(pid: str) -> None:
    r = call("DELETE", f"/store/products/{pid}")
    print(" ", r.get("code"), r.get("result") or r.get("error"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    {"check": cmd_check, "products": cmd_products,
     "plan": lambda: cmd_plan(False), "create": lambda: cmd_plan(True),
     "fix": cmd_fix,
     "delete": lambda: cmd_delete(sys.argv[2])}[cmd]()
