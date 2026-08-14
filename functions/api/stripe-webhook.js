/**
 * POST /api/stripe-webhook — Stripe tells us a build was paid for.
 *
 * The signature is verified properly, with a constant-time compare and a
 * timestamp tolerance. An unverified webhook is a public endpoint that anyone
 * can post a fake paid order to, and the thing on the other end of this one
 * starts a print job.
 *
 * On checkout.session.completed it emails the build sheet to the print queue.
 * It deliberately does NOT assign a serial: BEST IN BULL™ is a human-gated
 * transition and the serial mints at inspection, not at checkout. That is why
 * the confirmation says BULLTAKER PENDING.
 *
 * Bindings:
 *   STRIPE_WEBHOOK_SECRET  secret  whsec_…
 *   RESEND_API_KEY         secret
 *   MAIL_FROM / MAIL_TO_ORDERS
 */

const enc = new TextEncoder();

/** Timing-safe compare — a fast reject leaks the signature one byte at a time. */
function safeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function verify(body, header, secret, toleranceSec = 300) {
  if (!header || !secret) return false;
  const parts = Object.fromEntries(
    header.split(",").map((p) => p.split("=", 2)).filter((p) => p.length === 2)
  );
  const t = parseInt(parts.t, 10);
  if (!t || !parts.v1) return false;
  // Reject replays. Stripe signs the timestamp for exactly this reason.
  if (Math.abs(Date.now() / 1000 - t) > toleranceSec) return false;

  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(`${t}.${body}`));
  const hex = [...new Uint8Array(sig)]
    .map((b) => b.toString(16).padStart(2, "0")).join("");
  // Stripe may send several v1 signatures during a secret rotation.
  return header.split(",")
    .filter((p) => p.trim().startsWith("v1="))
    .some((p) => safeEqual(hex, p.trim().slice(3)));
}

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export async function onRequestPost({ request, env }) {
  const body = await request.text();
  const ok = await verify(body, request.headers.get("stripe-signature"), env.STRIPE_WEBHOOK_SECRET);
  if (!ok) {
    console.log("stripe webhook: bad signature");
    return new Response("bad signature", { status: 400 });
  }

  let event;
  try {
    event = JSON.parse(body);
  } catch {
    return new Response("bad json", { status: 400 });
  }

  if (event.type !== "checkout.session.completed") {
    // 200 on everything else, or Stripe retries events we simply do not want.
    return new Response("ignored", { status: 200 });
  }

  const s = event.data.object;
  const m = s.metadata || {};
  const ship = s.shipping_details || s.customer_details || {};
  const addr = ship.address || {};

  const rows = [
    ["PROFILE", m.profile_id],
    ["PAID", `$${((s.amount_total || 0) / 100).toFixed(2)} ${String(s.currency || "usd").toUpperCase()}`],
    ["EMAIL", s.customer_details && s.customer_details.email],
    ["PHONE", s.customer_details && s.customer_details.phone],
    ["SHOE", m.shoe],
    ["SIZE / FIT", [m.size, m.fit].filter(Boolean).join(" · ")],
    ["WIDTH / ARCH", [m.width, m.arch].filter(Boolean).join(" · ")],
    ["FEEL", m.feel],
    ["CELL / WALL", [m.cell_mm && `${m.cell_mm} mm`, m.wall_mm && `${m.wall_mm} mm`].filter(Boolean).join(" / ")],
    ["DENSITY", m.density],
    ["NOTES", m.notes],
    ["SHIP TO", [ship.name, addr.line1, addr.line2, addr.city, addr.state, addr.postal_code, addr.country].filter(Boolean).join(", ")],
    ["SESSION", s.id],
    ["PAYMENT", typeof s.payment_intent === "string" ? s.payment_intent : ""],
  ].filter(([, v]) => v);

  if (env.RESEND_API_KEY && env.MAIL_FROM) {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.RESEND_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        from: env.MAIL_FROM,
        to: [env.MAIL_TO_ORDERS || "print@bullprintlab.com"],
        reply_to: (s.customer_details && s.customer_details.email) || undefined,
        subject: `PAID · DROP 001 · ${m.profile_id || s.id.slice(-8)} · ${m.shoe || ""}`.trim(),
        html:
          '<div style="background:#0B0B0D;padding:20px 24px">' +
          '<span style="color:#E8B23A;font:800 15px/1 system-ui;letter-spacing:.14em">BULLPRINT LAB</span>' +
          '<span style="color:#5C5952;font:600 12px/1 monospace;letter-spacing:.14em"> · PAID BUILD</span></div>' +
          '<table style="border-collapse:collapse;margin:20px 24px">' +
          rows.map(([k, v]) =>
            `<tr><td style="padding:6px 14px 6px 0;color:#8A8578;font:600 12px/1.4 monospace;white-space:nowrap;vertical-align:top">${esc(k)}</td>` +
            `<td style="padding:6px 0;color:#111;font:400 14px/1.5 system-ui">${esc(v)}</td></tr>`).join("") +
          "</table>" +
          '<p style="margin:24px;color:#8A8578;font:400 12px/1.5 system-ui">' +
          "No serial has been assigned. BEST IN BULL™ is issued at inspection by a human, " +
          "which is why the buyer's confirmation reads BULLTAKER PENDING.</p>",
        text: rows.map(([k, v]) => `${k}: ${v}`).join("\n") +
          "\n\nNo serial assigned — issued at inspection.",
      }),
    });
    if (!r.ok) {
      console.log("order email failed:", r.status, await r.text());
      // 500 so Stripe retries: a paid order that never reached the queue is the
      // one failure that costs a customer their build.
      return new Response("mail failed", { status: 500 });
    }
  } else {
    console.log("PAID ORDER (mail not configured):", JSON.stringify(Object.fromEntries(rows)));
  }

  return new Response("ok", { status: 200 });
}

export async function onRequest({ request }) {
  if (request.method === "POST") return onRequestPost(...arguments);
  return new Response("POST only", { status: 405 });
}
