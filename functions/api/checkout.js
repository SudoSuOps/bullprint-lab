/**
 * POST /api/checkout — create a Stripe Checkout Session for a build profile.
 *
 * Cards and USDC ride the same session. Stripe's dynamic payment methods show
 * stablecoins automatically once "Stablecoins and Crypto" is approved on the
 * account, so there is no separate crypto integration and no second webhook —
 * the only requirement is that every line item is USD, which this one is.
 *
 * The whole build profile goes into `metadata`. The print queue needs the foot,
 * not the payment: the profile and the payment are separate records joined on
 * profile_id, so a refund never erases a print job and a reprint never needs a
 * second charge.
 *
 * Bindings:
 *   STRIPE_SECRET_KEY  secret
 *   STRIPE_PRICE_ID    plain   price_… for Drop 001
 *   TURNSTILE_SECRET   secret  (shared with /api/submit)
 */

const STRIPE_API = "https://api.stripe.com/v1/checkout/sessions";
const TURNSTILE_VERIFY =
  "https://challenges.cloudflare.com/turnstile/v0/siteverify";

const json = (status, body) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });

const clean = (v, max) =>
  typeof v === "string" ? v.replace(/\s+/g, " ").trim().slice(0, max) : "";

const isEmail = (v) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);

/** Stripe caps metadata at 50 keys, 40 char keys, 500 char values. */
const meta = (o) => {
  const out = {};
  for (const [k, v] of Object.entries(o)) {
    const s = clean(String(v ?? ""), 500);
    if (s) out[k.slice(0, 40)] = s;
  }
  return out;
};

async function verifyTurnstile(token, ip, secret) {
  if (!secret || !token) return false;
  const body = new FormData();
  body.append("secret", secret);
  body.append("response", token);
  if (ip) body.append("remoteip", ip);
  const r = await fetch(TURNSTILE_VERIFY, { method: "POST", body });
  return (await r.json()).success === true;
}

export async function onRequestPost({ request, env }) {
  let payload;
  try {
    payload = await request.json();
  } catch {
    return json(400, { ok: false, error: "MALFORMED REQUEST" });
  }

  if (!env.STRIPE_SECRET_KEY || !env.STRIPE_PRICE_ID) {
    console.log("checkout not configured: STRIPE_SECRET_KEY / STRIPE_PRICE_ID");
    return json(500, { ok: false, error: "CHECKOUT IS DOWN — EMAIL THE LAB" });
  }

  const ok = await verifyTurnstile(
    payload.token,
    request.headers.get("cf-connecting-ip"),
    env.TURNSTILE_SECRET
  );
  if (!ok) {
    return json(403, { ok: false, error: "VERIFICATION FAILED — RELOAD AND RETRY" });
  }

  const d = payload.data || {};
  const email = clean(d.email, 254);
  const shoe = clean(d.shoe, 200);
  if (!isEmail(email)) return json(422, { ok: false, error: "ADD AN EMAIL SO WE CAN REPLY" });
  if (!shoe) return json(422, { ok: false, error: "TELL US THE SHOE — WE CUT THE OUTLINE TO IT" });

  const profile = meta({
    profile_id: d.profileId,
    drop: "001",
    size: d.size,
    width: d.width,
    arch: d.arch,
    fit: d.fit,
    feel: d.feel,
    shoe,
    notes: d.notes,
    cell_mm: d.cell,
    wall_mm: d.wall,
    density: d.density,
  });

  const origin = new URL(request.url).origin;
  const form = new URLSearchParams();
  form.set("mode", "payment");
  form.set("line_items[0][price]", env.STRIPE_PRICE_ID);
  form.set("line_items[0][quantity]", "1");
  form.set("customer_email", email);
  form.set("success_url", `${origin}/order/confirmed?session_id={CHECKOUT_SESSION_ID}`);
  form.set("cancel_url", `${origin}/#order`);
  form.set("submit_type", "pay");
  // A made-to-order physical good needs an address, and the print queue needs
  // to know where it is going before it starts.
  form.set("shipping_address_collection[allowed_countries][0]", "US");
  form.set("phone_number_collection[enabled]", "true");
  // Same profile on the session AND the payment intent: the session is the
  // checkout, the payment intent is what a refund or a dispute references.
  for (const [k, v] of Object.entries(profile)) {
    form.set(`metadata[${k}]`, v);
    form.set(`payment_intent_data[metadata][${k}]`, v);
  }
  form.set("payment_intent_data[description]",
    `BullPrint Drop 001 · ${profile.profile_id || "profile"} · ${shoe}`);

  const r = await fetch(STRIPE_API, {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
      "content-type": "application/x-www-form-urlencoded",
      // Stripe replays this instead of double-charging a double-click.
      "idempotency-key": `${profile.profile_id || "p"}-${email}-${Date.now() >> 14}`,
    },
    body: form,
  });

  const session = await r.json();
  if (!r.ok || !session.url) {
    console.log("stripe session failed:", r.status, JSON.stringify(session.error || session));
    return json(502, { ok: false, error: "CHECKOUT IS DOWN — EMAIL THE LAB" });
  }

  return json(200, { ok: true, url: session.url });
}

export async function onRequest({ request }) {
  if (request.method === "POST") return onRequestPost(...arguments);
  return json(405, { ok: false, error: "POST ONLY" });
}
