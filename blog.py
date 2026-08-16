#!/usr/bin/env python3
"""
BEST IN BULL — the journal, generated from markdown.

Deliberately plain static HTML with no runtime. The home page is a client-side
app because it has a configurator in it; the journal has no reason to be, and
every reason not to: this is the part of the site an AI crawler that never runs
JavaScript can read completely, and it is where the citable material lives —
real numbers off real parts.

    content/blog/<slug>.md  ->  blog/<slug>/index.html
                            ->  blog/index.html

Front matter is a plain key: value block ended by a line of `---`.
"""
from __future__ import annotations

import html as _html
import pathlib
import re
from datetime import date

SITE = "https://bullprintlab.com"
BRAND = "BullPrint Lab"

# The design's tokens, lifted so the journal reads as the same object.
CSS = """
:root{--bg:#0B0B0D;--ink:#F4F2ED;--gold:#E8B23A;--dim:#8A8578;--line:rgba(255,255,255,.09)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:400 17px/1.65 Archivo,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--gold);text-decoration:none}a:hover{color:#F5D07A}
::selection{background:var(--gold);color:var(--bg)}
:focus-visible{outline:2px solid var(--gold);outline-offset:3px}
.wrap{max-width:760px;margin:0 auto;padding:0 24px}
header.top{border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(11,11,13,.9);backdrop-filter:blur(10px);z-index:9}
header.top .wrap{display:flex;align-items:center;justify-content:space-between;height:64px}
.mark{font:800 15px/1 Archivo,sans-serif;letter-spacing:.14em;color:var(--ink)}
.mark span{color:var(--gold)}
.nav{font:600 11px/1 'JetBrains Mono',monospace;letter-spacing:.16em;color:var(--dim)}
.nav a{margin-left:22px}
/* the buy form — /store/ only, the one page here that takes money */
form.buy{margin:26px 0 0;padding:22px;border:1px solid rgba(232,178,58,.32);background:#0E0E11;display:flex;flex-direction:column;gap:14px}
form.buy .buy-price{margin:0;font:500 13px/1 'JetBrains Mono',monospace;letter-spacing:.14em;color:#8B8780}
form.buy .buy-price strong{color:#E8B23A;font-size:20px;letter-spacing:0}
form.buy label{display:flex;flex-direction:column;gap:6px;font:700 10px/1 'JetBrains Mono',monospace;letter-spacing:.18em;color:#8B8780}
form.buy input,form.buy select{appearance:none;background:#0B0B0D;border:1px solid rgba(255,255,255,.14);color:#F4F2ED;padding:12px 13px;font:400 15px/1.3 Archivo,system-ui,sans-serif;border-radius:0}
form.buy input:focus,form.buy select:focus{outline:2px solid #E8B23A;outline-offset:1px;border-color:transparent}
form.buy button{appearance:none;cursor:pointer;border:0;width:100%;background:linear-gradient(120deg,#F5D07A,#E8B23A 45%,#A87F24);color:#0B0B0D;padding:17px 22px;font:700 12px/1 'JetBrains Mono',monospace;letter-spacing:.2em}
form.buy button:hover{filter:brightness(1.07)}
form.buy button:disabled{opacity:.55;cursor:default;filter:none}
form.buy .bp-buy-error{margin:0;min-height:1em;font:700 11px/1.5 'JetBrains Mono',monospace;letter-spacing:.12em;color:#E8B23A}
form.buy .bp-buy-error:empty{min-height:0}
form.buy .buy-note{margin:0;font:400 13px/1.6 Archivo,system-ui,sans-serif;color:#6E6B66}
#bp-turnstile{position:fixed;left:-9999px;top:0}
.kicker{font:700 11px/1 'JetBrains Mono',monospace;letter-spacing:.2em;color:var(--gold);text-transform:uppercase}
h1{font:900 clamp(34px,6vw,58px)/1.03 Archivo,sans-serif;letter-spacing:-.02em;margin:18px 0 14px}
h2{font:800 26px/1.2 Archivo,sans-serif;letter-spacing:-.01em;margin:44px 0 12px}
h3{font:700 19px/1.3 Archivo,sans-serif;margin:32px 0 8px}
.meta{font:600 11px/1 'JetBrains Mono',monospace;letter-spacing:.14em;color:var(--dim)}
.lede{font-size:20px;color:#D9D5CC;margin:0 0 30px}
article p{margin:0 0 20px}
article ul,article ol{margin:0 0 20px;padding-left:22px}
article li{margin:0 0 8px}
blockquote{margin:26px 0;padding:2px 0 2px 20px;border-left:2px solid var(--gold);color:#D9D5CC}
code{font:500 14px/1 'JetBrains Mono',monospace;background:#141417;padding:2px 6px;border:1px solid var(--line)}
pre{background:#141417;border:1px solid var(--line);padding:16px;overflow-x:auto}
pre code{background:none;border:none;padding:0;line-height:1.6}
table{border-collapse:collapse;width:100%;margin:0 0 24px;font-size:15px;display:block;overflow-x:auto}
th,td{text-align:left;padding:9px 14px 9px 0;border-bottom:1px solid var(--line);white-space:nowrap}
th{font:700 11px/1 'JetBrains Mono',monospace;letter-spacing:.14em;color:var(--dim);text-transform:uppercase}
hr{border:none;border-top:1px solid var(--line);margin:44px 0}
.post-list{list-style:none;padding:0;margin:0}
.post-list li{border-bottom:1px solid var(--line);padding:26px 0}
.post-list h2{margin:8px 0 8px;font-size:24px}
.post-list p{margin:0;color:var(--dim)}
footer.foot{border-top:1px solid var(--line);margin-top:70px;padding:34px 0 60px}
footer.foot .wrap{display:flex;flex-wrap:wrap;gap:14px 26px;justify-content:space-between}
.tags{margin:26px 0 0}
.tag{display:inline-block;margin:0 6px 6px 0;padding:5px 10px;border:1px solid var(--line);font:600 10px/1 'JetBrains Mono',monospace;letter-spacing:.14em;color:var(--dim)}
article img{display:block;width:100%;height:auto;margin:30px 0;border:1px solid var(--line);background:#000}
.titles{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border:1px solid var(--line);margin:38px 0}
.titles>div{background:var(--bg);padding:30px 26px}
.titles h2{margin:0 0 4px;font-size:clamp(28px,4vw,40px);line-height:1.02}
.titles .role{font:700 11px/1 'JetBrains Mono',monospace;letter-spacing:.2em;color:var(--gold);margin:0 0 16px}
.titles p{color:#D9D5CC;font-size:15.5px}
.spec{list-style:none;padding:0;margin:22px 0 0;border-top:1px solid var(--line)}
.spec li{display:grid;grid-template-columns:112px 1fr;gap:14px;padding:11px 0;border-bottom:1px solid var(--line);margin:0;font-size:13.5px}
.spec b{font:700 10px/1.5 'JetBrains Mono',monospace;letter-spacing:.14em;color:var(--dim);font-weight:700}
.pull{margin:22px 0 0;padding:16px 18px;border:1px solid var(--gold);color:var(--gold);font:600 15px/1.45 Archivo,sans-serif}
.lozenge{display:inline-block;padding:7px 16px;border:1px solid var(--gold);border-radius:999px;font:700 10px/1 'JetBrains Mono',monospace;letter-spacing:.2em;color:var(--gold)}
@media(max-width:720px){.titles{grid-template-columns:1fr}}
.note{margin:46px 0 0;padding:16px 18px;border:1px solid var(--line);background:#101013;color:var(--dim);font-size:14px}
"""


def parse(path: pathlib.Path, required=("title", "date", "summary")) -> dict:
    raw = path.read_text()
    meta, body = {}, raw
    if raw.startswith("---"):
        head, body = raw[3:].split("\n---", 1)
        for line in head.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    meta["slug"] = path.stem
    meta["body"] = body.strip()
    for req in required:
        if req not in meta:
            raise SystemExit(f"{path.name} is missing front matter: {req}")
    return meta


def md(src: str) -> str:
    """Just enough markdown. Anything fancier belongs in the design, not here."""
    out, lines, i = [], src.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(_html.escape(lines[j]))
                j += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            i = j + 1
            continue
        if ln.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= set("|-: "):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            t = "<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            for r in body:
                t += "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
            out.append(t + "</tbody></table>")
            continue
        if re.match(r"^#{1,3} ", ln):
            n = len(ln) - len(ln.lstrip("#"))
            out.append(f"<h{n}>{inline(ln[n:].strip())}</h{n}>")
            i += 1
            continue
        if ln.startswith("> "):
            buf = []
            while i < len(lines) and lines[i].startswith("> "):
                buf.append(inline(lines[i][2:]))
                i += 1
            out.append("<blockquote><p>" + " ".join(buf) + "</p></blockquote>")
            continue
        if re.match(r"^[-*] ", ln):
            buf = []
            while i < len(lines) and re.match(r"^[-*] ", lines[i]):
                buf.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(buf) + "</ul>")
            continue
        if ln.strip() == "---":
            out.append("<hr>")
            i += 1
            continue
        # Raw HTML block: pass it through untouched. A post that needs a real
        # layout should be able to write one, and escaping it into visible <div>
        # soup is worse than not supporting it at all.
        if re.match(r"^<(div|section|figure|table|aside|details|iframe|svg|picture|video)\b", ln.strip()):
            buf = []
            while i < len(lines) and lines[i].strip():
                buf.append(lines[i])
                i += 1
            out.append("\n".join(buf))
            continue
        if not ln.strip():
            i += 1
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3} |[-*] |> |\||```|---)", lines[i]):
            buf.append(inline(lines[i]))
            i += 1
        out.append("<p>" + " ".join(buf) + "</p>")
    return "\n".join(out)


def inline(s: str) -> str:
    s = _html.escape(s, quote=False)
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",
               r'<img src="\2" alt="\1" loading="lazy" decoding="async">', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def shell(title, desc, canonical, body, jsonld, depth=1, scripts=()):
    """`scripts` is opt-in and empty by default.

    Every page here is flat HTML with no runtime, which is why a non-executing
    crawler can read it completely. /store/ is the one page that has to break
    that: it shows a price, and a price with no way to pay it is not a store.
    So a page may name the scripts it needs, and nothing else changes.
    """
    up = "../" * depth
    # An absolute URL is already resolved; only same-origin paths take the
    # depth prefix. Prefixing both turns https:// into ../https:// silently.
    tags = "".join(
        f'\n<script src="{sc if sc.startswith(("http://", "https://")) else up + sc}"'
        ' defer></script>' for sc in scripts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)}</title>
<meta name="description" content="{_html.escape(desc)}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#0B0B0D">
<meta name="color-scheme" content="dark">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{_html.escape(title)}">
<meta property="og:description" content="{_html.escape(desc)}">
<meta property="og:image" content="{SITE}/assets/insert-spec-sheet.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@bestinbull">
<link rel="stylesheet" href="{up}fonts/fonts.css">
<style>{CSS}</style>
<script type="application/ld+json">{jsonld}</script>{tags}
</head>
<body>
<header class="top"><div class="wrap">
  <a class="mark" href="{up}">BULLPRINT <span>LAB</span></a>
  <nav class="nav"><a href="{up}">SITE</a><a href="{up}store/">STORE</a><a href="{up}blog/">JOURNAL</a><a href="{up}#order">BUILD YOURS</a></nav>
</div></header>
{body}
<footer class="foot"><div class="wrap">
  <span class="meta">BEST IN BULL™ · PRINTED IN HOUSE · JUPITER, FLORIDA</span>
  <span class="meta"><a href="mailto:bullish@bullprintlab.com">BULLISH@BULLPRINTLAB.COM</a> · <a href="tel:+15615327120">561.532.7120</a> · <a href="https://x.com/bestinbull" rel="me">@BESTINBULL</a></span>
</div></footer>
</body>
</html>"""


def build_order_confirmed(root: pathlib.Path) -> None:
    """/order/confirmed — where Stripe returns a buyer after payment.

    Deliberately says BULLTAKER PENDING and not a serial. The serial mints at
    inspection, by a human, which is the whole guardrail: a title that arrives
    at checkout is a receipt with a nicer font.
    """
    url = f"{SITE}/order/confirmed"
    ld = ('{"@context":"https://schema.org","@type":"WebPage","name":"Order confirmed",'
          f'"url":"{url}","inLanguage":"en",'
          '"isPartOf":{"@type":"WebSite","@id":"https://bullprintlab.com/#site"}}')
    body = """<main class="wrap">
  <p class="kicker" style="margin-top:54px">Payment received</p>
  <h1>The build is in<br>the queue.</h1>
  <p class="lede">Your build sheet went to the lab the moment the payment
  cleared. A confirmation is on its way to the address you paid with.</p>

  <div class="titles" style="grid-template-columns:1fr">
    <div>
      <p class="role">Status</p>
      <h2 style="font-size:28px">BULLTAKER PENDING</h2>
      <p>You are not a BullTaker yet, and that is deliberate. The serial is
      issued when the unit passes inspection — not at checkout. If it does not
      pass, it does not ship and no number is ever assigned to it.</p>
      <ul class="spec">
        <li><b>Next</b><span>We cut the outline to your shoe and print</span></li>
        <li><b>Then</b><span>Inspection — geometry, print, finish</span></li>
        <li><b>On pass</b><span>Serial NNN / 100 assigned, cert card written, BEST IN BULL™ stamped</span></li>
      </ul>
      <p class="pull">"Numbered, not mass."</p>
    </div>
  </div>

  <h2>Something wrong with the order?</h2>
  <p>Reply to the confirmation email, or write to
  <a href="mailto:bullish@bullprintlab.com">bullish@bullprintlab.com</a> with your
  profile ID. A person from the lab answers — usually within a day.</p>

  <p class="note">BullPrint Lab makes footwear inserts for comfort and fit
  experimentation. Nothing here is a medical device and nothing here is medical
  advice — no claim is made about treating, preventing or diagnosing anything.</p>
</main>"""
    d = root / "order" / "confirmed"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(
        shell("Order confirmed — BullPrint Lab",
              "Your build is in the queue. The serial is issued at inspection, not at checkout.",
              url, body, ld, depth=2))


def build_pages(root: pathlib.Path) -> list[dict]:
    """content/pages/<slug>.md -> /<slug>/index.html — undated, standalone.

    Same shell as the journal so a page reads as the same object, but WebPage
    rather than BlogPosting: these are not dated entries and should not show up
    in a feed pretending to be.
    """
    src = root / "content" / "pages"
    if not src.exists():
        return []
    out = []
    for f in sorted(src.glob("*.md")):
        m = parse(f, required=("title", "summary"))
        url = f"{SITE}/{m['slug']}/"
        ld = (
            '{"@context":"https://schema.org","@type":"WebPage",'
            f'"name":{_json(m["title"])},"description":{_json(m["summary"])},'
            f'"url":"{url}","inLanguage":"en",'
            '"isPartOf":{"@type":"WebSite","@id":"https://bullprintlab.com/#site"},'
            '"publisher":{"@type":"Organization","@id":"https://bullprintlab.com/#org"}}'
        )
        body = f"""<main class="wrap">
  <p class="kicker" style="margin-top:54px">{_html.escape(m.get('kicker', 'BullPrint Lab'))}</p>
  <h1>{_html.escape(m['title'])}</h1>
  <p class="lede">{inline(m['summary'])}</p>
  {md(m['body'])}
</main>"""
        d = root / m["slug"]
        d.mkdir(exist_ok=True)
        scripts = [x.strip() for x in m.get("scripts", "").split() if x.strip()]
        (d / "index.html").write_text(
            shell(f"{m['title']} — {BRAND}", m["summary"], url, body, ld,
                  depth=1, scripts=scripts))
        out.append(m)
    return out


def build(root: pathlib.Path) -> list[dict]:
    src = root / "content" / "blog"
    if not src.exists():
        return []
    posts = sorted((parse(p) for p in src.glob("*.md")),
                   key=lambda m: m["date"], reverse=True)
    outdir = root / "blog"
    outdir.mkdir(exist_ok=True)

    for m in posts:
        url = f"{SITE}/blog/{m['slug']}/"
        ld = (
            '{"@context":"https://schema.org","@type":"BlogPosting",'
            f'"headline":{_json(m["title"])},"description":{_json(m["summary"])},'
            f'"datePublished":"{m["date"]}","dateModified":"{m.get("updated", m["date"])}",'
            f'"url":"{url}","mainEntityOfPage":{{"@type":"WebPage","@id":"{url}"}},'
            f'"image":"{SITE}/assets/insert-spec-sheet.png",'
            '"author":{"@type":"Organization","name":"BullPrint Lab","url":"https://bullprintlab.com/"},'
            '"publisher":{"@type":"Organization","name":"BullPrint Lab","url":"https://bullprintlab.com/"},'
            f'"isPartOf":{{"@type":"Blog","name":"Best in Bull","@id":"{SITE}/blog/"}}}}'
        )
        tags = "".join(f'<span class="tag">{_html.escape(t.strip())}</span>'
                       for t in m.get("tags", "").split(",") if t.strip())
        # The insert disclaimer belongs on posts about the insert. On an essay
        # it is a non sequitur, and a disclaimer that shows up where it makes no
        # sense is one people stop reading where it does.
        note = "" if m.get("disclaimer", "").lower() in ("no", "none") else (
            '<p class="note">BullPrint Lab makes footwear inserts for comfort and '
            "fit experimentation. Nothing here is a medical device and nothing "
            "here is medical advice — no claim is made about treating, preventing "
            "or diagnosing anything.</p>")
        body = f"""<main class="wrap">
<article>
  <p class="kicker">Best in Bull</p>
  <h1>{_html.escape(m['title'])}</h1>
  <p class="meta">{m['date']}{' · UPDATED ' + m['updated'] if m.get('updated') else ''}</p>
  <p class="lede">{inline(m['summary'])}</p>
  {md(m['body'])}
  <div class="tags">{tags}</div>
  {note}
</article>
</main>"""
        d = outdir / m["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(
            shell(f"{m['title']} — Best in Bull", m["summary"], url, body, ld, depth=2))

    items = "".join(
        f'<li><p class="meta">{m["date"]}</p>'
        f'<h2><a href="/blog/{m["slug"]}/">{_html.escape(m["title"])}</a></h2>'
        f'<p>{inline(m["summary"])}</p></li>' for m in posts)
    ld = (
        '{"@context":"https://schema.org","@type":"Blog","name":"Best in Bull",'
        f'"url":"{SITE}/blog/","description":"The BullPrint Lab journal: drops, '
        'geometry and the receipts behind the BEST IN BULL stamp.",'
        '"publisher":{"@type":"Organization","name":"BullPrint Lab","url":"https://bullprintlab.com/"},'
        '"blogPost":[' + ",".join(
            f'{{"@type":"BlogPosting","headline":{_json(m["title"])},'
            f'"url":"{SITE}/blog/{m["slug"]}/","datePublished":"{m["date"]}"}}'
            for m in posts) + "]}"
    )
    body = f"""<main class="wrap">
  <p class="kicker" style="margin-top:54px">The journal</p>
  <h1>Best in Bull</h1>
  <p class="lede">Drops, geometry, and the receipts behind the stamp. What we
  printed, what we measured, and what it cost us to find out.</p>
  <ul class="post-list">{items}</ul>
</main>"""
    (outdir / "index.html").write_text(
        shell("Best in Bull — the BullPrint Lab journal",
              "Drops, geometry and the receipts behind the BEST IN BULL stamp.",
              f"{SITE}/blog/", body, ld, depth=1))
    return posts


def _json(s: str) -> str:
    import json
    return json.dumps(s)
