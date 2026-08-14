/**
 * GET /api/btc — Bitcoin spot, proxied and cached at the edge.
 *
 * The browser must not call CoinGecko directly. It rate-limits by IP, so a
 * popular post would degrade the ticker for everyone at once, and a first-paint
 * dependency on a third-party API is a bad trade for a number this decorative.
 * One cached response at the edge serves every visitor. It also keeps the page
 * single-origin, so the site's `connect-src 'self'` CSP stays closed.
 *
 * Failure is a first-class state, not an exception. If both sources are down
 * this returns ok:false and the ticker says so. A brand whose whole pitch is
 * that claims come with verification does not get to render an invented price.
 */

const TTL = 45; // seconds at the edge — the design polls at 60

const COINGECKO =
  "https://api.coingecko.com/api/v3/simple/price" +
  "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true";
const COINBASE = "https://api.coinbase.com/v2/prices/BTC-USD/spot";

const reply = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      // let the edge serve this to everyone for TTL, and let a stale copy cover
      // a brief upstream outage rather than blanking the strip
      "cache-control": `public, max-age=${TTL}, s-maxage=${TTL}, stale-while-revalidate=120`,
    },
  });

async function fromCoinGecko() {
  const r = await fetch(COINGECKO, {
    headers: { accept: "application/json" },
    cf: { cacheTtl: TTL, cacheEverything: true },
  });
  if (!r.ok) throw new Error(`coingecko ${r.status}`);
  const d = await r.json();
  const usd = d && d.bitcoin && d.bitcoin.usd;
  if (typeof usd !== "number") throw new Error("coingecko shape");
  return {
    usd,
    change24h: typeof d.bitcoin.usd_24h_change === "number"
      ? d.bitcoin.usd_24h_change
      : null,
    source: "coingecko",
  };
}

async function fromCoinbase() {
  const r = await fetch(COINBASE, {
    headers: { accept: "application/json" },
    cf: { cacheTtl: TTL, cacheEverything: true },
  });
  if (!r.ok) throw new Error(`coinbase ${r.status}`);
  const d = await r.json();
  const usd = d && d.data && parseFloat(d.data.amount);
  if (!Number.isFinite(usd)) throw new Error("coinbase shape");
  // Coinbase spot carries no 24h change. Reporting null is the honest move —
  // the strip renders "24H —" rather than implying a flat market.
  return { usd, change24h: null, source: "coinbase" };
}

export async function onRequestGet() {
  for (const get of [fromCoinGecko, fromCoinbase]) {
    try {
      const q = await get();
      return reply({ ok: true, ...q, at: Date.now() });
    } catch (e) {
      console.log("btc source failed:", e.message);
    }
  }
  return reply({ ok: false, error: "RATE OFFLINE" }, 200);
}
