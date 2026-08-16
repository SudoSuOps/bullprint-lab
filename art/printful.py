#!/usr/bin/env python3
"""
BullPrint Lab — build the Printful store.

    python3 art/printful.py check      # which store, how many products live
    python3 art/printful.py plan       # what would be created, with prices
    python3 art/printful.py create     # create everything not already live
    python3 art/printful.py products   # what is live now
    python3 art/printful.py mockup SKU # render one, to look at before shipping
    python3 art/printful.py delete ID

PRICING — the house rule
------------------------
15% over TOTAL cost, and total cost means blank + shipping, not blank alone.
Applied to the blank alone every line is negative: a tee retails $12.94 against
$9.25 + $4.99 shipping and loses $3.98 before Stripe takes a cut. So

    retail = (variant_price + SHIP) * 1.15      computed PER VARIANT

per variant, because Printful prices 2XL above S-XL and one flat retail across a
size run quietly loses money at the big end.

At 15% a tee nets about $1.60 after Stripe. One customer-caused return wipes out
eleven sales. Recorded here so the number stays visible.

EVERYTHING IS RESOLVED LIVE
---------------------------
Variant ids, blank prices and placement areas are fetched from the API, never
pasted in. A hardcoded variant id is a silent wrong-product waiting to happen,
and a hardcoded print area silently rescales art the day Printful changes a
blank.

TWO THINGS THAT BIT, WRITTEN DOWN SO THEY DO NOT AGAIN
------------------------------------------------------
1. Printful sits behind Cloudflare, which 403s the default Python-urllib
   signature with "error code: 1010" and a non-JSON body. It reads exactly like
   an API outage. A User-Agent header is the whole fix.
2. `position` needs a real numeric height. Passing null makes Printful drop the
   WHOLE position block and auto-fit — a 9 inch seal becomes a 12 inch seal and
   nothing in the response says so. Nor can you verify by reading the product
   back: /store/products has no position key at all, so absent reads as null.
   Verify with a mockup and your eyes.
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

SHIP = 4.99
MARKUP = 1.15

# Embroidery thread is a FIXED palette — the brand gold #E8B23A is not in it and
# cannot be. Nearest by RGB distance is 1951 Gold #FFCC00 (delta 68) over
# 1672 Old Gold #A67843 (delta 88), so stitched gold runs brighter than printed
# gold. That is a property of thread, not a choice, and it is written down so
# nobody "fixes" the mismatch later by changing the brand colour.
THREAD = {"gold": "#FFCC00", "ink": "#000000", "bone": "#FFFFFF"}


def thread_option(placement: str) -> str:
    """Printful names the option after the placement, with one special case:
    `embroidery_front` takes plain `thread_colors`, everything else takes
    `thread_colors_<rest>`."""
    rest = placement.replace("embroidery_", "")
    return "thread_colors" if rest == "front" else f"thread_colors_{rest}"


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + TOKEN,
                 "Content-Type": "application/json",
                 "User-Agent": "BullPrintLab/1.0 (+https://bullprintlab.com)"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            if e.code == 429 and attempt < 4:
                time.sleep(int(e.headers.get("Retry-After", 15)))
                continue
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"code": e.code, "error": {"message": raw[:200]}}
        except urllib.error.URLError:
            if attempt < 4:
                time.sleep(5)
                continue
            return {"code": 0, "error": {"message": "unreachable"}}
    return {"code": 0, "error": {"message": "gave up"}}


def retail(cost: float) -> str:
    return f"{round((cost + SHIP) * MARKUP, 2):.2f}"


# ── the line ────────────────────────────────────────────────────────────────
# colours: {Printful colour name: ink}. The ink picks the art file — dark blanks
# take gold, light blanks take ink, per the merch sheet's colourway rule.
# sizes: [] means one-size, take every variant of that colour.

TEE = ["S", "M", "L", "XL", "2XL"]

LINE = [
    # ── tees · Gildan 5000 · DTG ────────────────────────────────────────────
    dict(sku="seal-tee", name="Genesis Seal Tee", blank=438, place="front",
         art="t01-seal", inches=9.0, top_in=2.0, sizes=TEE,
         colours={"Black": "gold", "Natural": "ink", "Gold": "ink"}),
    dict(sku="bullish-tee", name="BULLISH Tee", blank=438, place="front",
         art="t02-bullish", inches=10.5, top_in=3.4, sizes=TEE,
         colours={"Black": "gold", "Natural": "ink"}),
    dict(sku="weprint-tee", name="WE PRINT. Tee", blank=438, place="back",
         art="t03b-bull", inches=11.0, top_in=2.4, sizes=TEE,
         colours={"Natural": "ink", "White": "ink", "Black": "gold"}),
    dict(sku="bullon-tee", name="BULL ON. Tee", blank=438, place="front",
         art="t04f-bull-on", inches=9.0, top_in=4.0, sizes=TEE,
         colours={"Gold": "ink", "Black": "gold"}),

    # ── other tee blanks ────────────────────────────────────────────────────
    dict(sku="seal-softstyle", name="Genesis Seal Tee · Softstyle", blank=12,
         place="front", art="t01-seal", inches=9.0, top_in=2.0, sizes=TEE,
         colours={"Black": "gold", "Natural": "ink"}),
    dict(sku="seal-fitted", name="Genesis Seal Tee · Fitted", blank=108,
         place="front", art="t01-seal", inches=9.0, top_in=2.0, sizes=TEE,
         colours={"Black": "gold", "White": "ink"}),
    dict(sku="seal-womens-v", name="Genesis Seal Tee · Women's V-Neck", blank=782,
         place="front", art="t01-seal", inches=8.0, top_in=2.0,
         sizes=["S", "M", "L", "XL"],
         colours={"Solid Black Blend": "gold", "Solid White Blend": "ink"}),

    # ── fleece ──────────────────────────────────────────────────────────────
    # 1629 offers no DTG placements at all — technique=DTG is rejected — so the
    # zip hoodie is embroidered, and the seal is too fine for thread. It gets
    # the bull. NOT on the back: Printful answers "Large embroidery placements
    # cannot be used in API" for embroidery_large_back, which is dashboard-only.
    # Left chest is the placement the API will actually take.
    dict(sku="bull-zip-hoodie", name="Bull Full-Zip Hoodie", blank=1629,
         place="embroidery_chest_left", art="emb-square-675", inches=3.5,
         top_in=0.0, sizes=TEE, embroidery=True,
         colours={"Black": "gold", "Navy": "gold"}),
    dict(sku="weprint-hoodie", name="WE PRINT. Hoodie", blank=602, place="back",
         art="t03b-bull", inches=11.0, top_in=2.4, sizes=TEE,
         colours={"Black": "gold", "Bone": "ink"}),
    dict(sku="bull-cruiser", name="Bull Hoodie · Organic Cruiser", blank=834,
         place="front", art="t06-bull-mascot", inches=8.0, top_in=3.0, sizes=TEE,
         tech="DTG", fixed=True, colours={"Black": "gold", "White": "gold"}),
    dict(sku="bull-sweatpants", name="Bull Sweatpants", blank=895,
         place="leg_front_left", art="cap-bull", inches=3.0, top_in=2.0,
         sizes=TEE, tech="DTG", colours={"Black": "gold"}),
    dict(sku="bull-fleece-pants", name="Bull Fleece Sweatpants", blank=412,
         place="leg_front_left", art="cap-bull", inches=3.0, top_in=2.0,
         sizes=TEE, colours={"Black": "gold"}),
    dict(sku="bull-fleece-shorts", name="Bull Fleece Shorts", blank=482,
         place="leg_front_left", art="cap-bull", inches=3.0, top_in=2.0,
         sizes=TEE, colours={"Black": "gold"}),

    # ── apron ───────────────────────────────────────────────────────────────
    dict(sku="seal-apron", name="Genesis Seal Apron", blank=565, place="front",
         art="t01-seal", inches=8.0, top_in=2.0, sizes=[],
         colours={"Black": "gold"}),

    # ── embroidery · caps and socks ─────────────────────────────────────────
    # No seal and no genesis hash up here: 7px ring text and 64 characters come
    # back as lint at 3 inches. Caps get the bull, which is why emb_* exists.
    dict(sku="cap-trucker", name="Bull Trucker", blank=252,
         place="embroidery_front_large", art="emb-wide-1770", inches=5.9,
         top_in=0.0, sizes=[], embroidery=True,
         colours={"Black": "gold", "Black/ White": "gold", "Khaki": "ink",
                  "Navy": "gold", "Charcoal": "gold", "White": "ink"}),
    dict(sku="cap-rope", name="Bull Rope Cap", blank=846,
         place="embroidery_front", art="emb-small-600", inches=2.0,
         top_in=0.0, sizes=[], embroidery=True,
         colours={"Black/White": "gold", "White/Black": "ink"}),
    dict(sku="cap-dad", name="Bull Dad Hat", blank=755,
         place="embroidery_front_large", art="emb-wide-1770", inches=5.5,
         top_in=0.0, sizes=[], embroidery=True,
         colours={"Black": "gold", "Navy": "gold", "White": "ink"}),
    dict(sku="socks", name="Bull Crew Socks", blank=502,
         place="embroidery_outside_left", art="emb-sock-177", inches=1.2,
         top_in=0.0, sizes=[], embroidery=True,
         colours={"Black": "gold", "White": "ink", "Heather Grey": "ink"}),
]


def art_size(stem: str) -> tuple[int, int]:
    from PIL import Image
    return Image.open(HERE / "print" / f"{stem}.png").size


_cache: dict = {}


def blank_info(pid: int, embroidery: str) -> dict:
    """Variants and placement areas, live."""
    key = (pid, embroidery)
    if key in _cache:
        return _cache[key]
    v = call("GET", f"/products/{pid}").get("result", {})
    q = f"?technique={embroidery}" if embroidery else ""
    pf = call("GET", f"/mockup-generator/printfiles/{pid}{q}").get("result", {})
    files = {f["printfile_id"]: f for f in pf.get("printfiles", [])}
    areas = {}
    vp = pf.get("variant_printfiles") or []
    if vp:
        for place, fid in vp[0]["placements"].items():
            f = files.get(fid)
            if f:
                areas[place] = (f["width"], f["height"], f.get("dpi") or 150)
    _cache[key] = dict(variants=v.get("variants", []), areas=areas)
    time.sleep(0.4)
    return _cache[key]


def build() -> list[dict]:
    out = []
    for p in LINE:
        info = blank_info(p["blank"], p.get("tech", "EMBROIDERY" if p.get("embroidery") else ""))
        area = info["areas"].get(p["place"])
        if not area:
            print(f"  ! {p['sku']}: placement {p['place']!r} not offered "
                  f"(have {sorted(info['areas'])})")
            continue
        aw, ah, dpi = area
        for colour, ink in p["colours"].items():
            vs = [v for v in info["variants"] if v["color"] == colour
                  and (not p["sizes"] or v["size"] in p["sizes"])]
            if not vs:
                have = sorted({v["color"] for v in info["variants"]})[:6]
                print(f"  ! {p['sku']}: no variant for colour {colour!r} "
                      f"(have {have}…)")
                continue
            if p["sizes"]:
                vs.sort(key=lambda v: p["sizes"].index(v["size"]))
            stem = p["art"] if p.get("fixed") else f"{p['art']}-{ink}"
            iw, ih = art_size(stem)
            w = round(p["inches"] * dpi)
            h = round(w * ih / iw)
            if w > aw:
                w, h = aw, round(aw * ih / iw)
            if h > ah:
                h, w = ah, round(ah * iw / ih)
            top = round(p["top_in"] * dpi)
            if top + h > ah:
                top = max(0, (ah - h) // 2)
            url = f"{ART}/{stem}.png"
            slug = colour.lower().replace("/", "").replace(" ", "")
            opts = []
            if p.get("embroidery"):
                opts = [dict(id=thread_option(p["place"]), value=[THREAD[ink]]),
                        dict(id="embroidery_type", value="flat")]
            out.append(dict(
                sku=f"{p['sku']}-{slug}",
                name=f"BullPrint Lab — {p['name']} ({colour})",
                url=url, stem=stem, place=p["place"], inches=p["inches"],
                blank=p["blank"],
                variants=[dict(variant_id=v["id"],
                               retail_price=retail(float(v["price"])),
                               options=opts,
                               files=[dict(type=p["place"], url=url, position=dict(
                                   area_width=aw, area_height=ah,
                                   width=w, height=h, top=top,
                                   left=round((aw - w) / 2)))])
                          for v in vs]))
    return out


def live_names() -> dict[str, int]:
    return {p["name"]: p["id"] for p in
            call("GET", "/store/products?limit=100").get("result", [])}


def cmd_check() -> None:
    for s in call("GET", "/stores").get("result", []):
        print(f"  store id={s['id']}  '{s['name']}'  type={s.get('type')}")
    print(f"  {len(live_names())} sync product(s) live")


def cmd_products() -> None:
    ps = call("GET", "/store/products?limit=100").get("result", [])
    for p in ps:
        print(f"  {p['id']}  {p['name'][:58]:<58} v={p['variants']} synced={p['synced']}")
    print(f"  {len(ps)} product(s)")


def cmd_plan(create: bool = False) -> None:
    plan = build()
    live = live_names() if create else {}
    print(f"\n  {len(plan)} product(s), "
          f"{sum(len(p['variants']) for p in plan)} variants\n")
    made = skipped = failed = 0
    for p in plan:
        lo = min(v["retail_price"] for v in p["variants"])
        hi = max(v["retail_price"] for v in p["variants"])
        rng = f"${lo}" if lo == hi else f"${lo}-{hi}"
        line = f"  {p['name'][:54]:<54} {rng:>14}  {p['stem']}"
        if not create:
            print(line)
            continue
        if p["name"] in live:
            print(line + "   already live")
            skipped += 1
            continue
        r = call("POST", "/store/products",
                 {"sync_product": {"name": p["name"], "thumbnail": p["url"]},
                  "sync_variants": p["variants"]})
        if r.get("code") in (200, 201):
            print(line + f"   CREATED {r['result']['id']}")
            made += 1
        else:
            print(line + f"   FAILED {r.get('code')} "
                         f"{str(r.get('error', {}).get('message'))[:60]}")
            failed += 1
        time.sleep(0.5)
    if create:
        print(f"\n  created {made} · already live {skipped} · failed {failed}")


def cmd_mockup(sku: str) -> None:
    p = next((x for x in build() if x["sku"].startswith(sku)), None)
    if not p:
        sys.exit(f"no sku matching {sku}")
    f = p["variants"][0]["files"][0]
    r = call("POST", f"/mockup-generator/create-task/{p['blank']}",
             {"variant_ids": [p["variants"][0]["variant_id"]], "format": "jpg",
              "files": [{"placement": f["type"], "image_url": f["url"],
                         "position": f["position"]}]})
    if r.get("code") != 200:
        sys.exit(f"  {r}")
    key = r["result"]["task_key"]
    for _ in range(25):
        time.sleep(6)
        t = call("GET", f"/mockup-generator/task?task_key={key}").get("result", {})
        if t.get("status") == "completed":
            print(" ", p["name"])
            print(" ", t["mockups"][0]["mockup_url"])
            return
        if t.get("status") == "failed":
            sys.exit(f"  failed: {t.get('error')}")
    sys.exit("  timed out")


def cmd_delete(pid: str) -> None:
    print(" ", call("DELETE", f"/store/products/{pid}"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    {"check": cmd_check, "products": cmd_products,
     "plan": lambda: cmd_plan(False), "create": lambda: cmd_plan(True),
     "mockup": lambda: cmd_mockup(sys.argv[2]),
     "delete": lambda: cmd_delete(sys.argv[2])}[cmd]()
