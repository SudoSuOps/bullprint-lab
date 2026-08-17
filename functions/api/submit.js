/**
 * POST /api/submit — the site's three forms land here.
 *
 * Same-origin by design: the CSP the site ships is `form-action 'self'` and
 * `connect-src 'self'`, so a Pages Function needs no CSP exception, and the
 * Resend key never leaves the edge. A third-party form service would need both
 * a hole in the CSP and a copy of every customer's order.
 *
 * Flow: verify Turnstile -> validate -> send through Resend -> 200.
 *
 * Bindings (Pages project -> Settings -> Environment variables):
 *   TURNSTILE_SECRET  secret  — from the Turnstile widget
 *   RESEND_API_KEY    secret  — from Resend
 *   MAIL_FROM         plain   — e.g. lab@send.bullprintlab.com  (a SUBDOMAIN:
 *                               the apex SPF belongs to Proton and there can
 *                               only be one v=spf1 record on a domain)
 *   MAIL_TO_ORDERS    plain   — print@bullprintlab.com
 *   MAIL_TO_GENERAL   plain   — bull@bullprintlabs.com
 */

const TURNSTILE_VERIFY =
  "https://challenges.cloudflare.com/turnstile/v0/siteverify";
const RESEND_SEND = "https://api.resend.com/emails";

const LIMITS = { short: 200, long: 2000, email: 254 };

const json = (status, body) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      // this endpoint is for our own page only
      "access-control-allow-origin": "https://bullprintlab.com",
      "vary": "origin",
    },
  });

const clean = (v, max) =>
  typeof v === "string" ? v.replace(/\s+/g, " ").trim().slice(0, max) : "";

const isEmail = (v) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);

/** Escape before interpolating anything a stranger typed into HTML. */
const esc = (v) =>
  String(v).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const rows = (pairs) =>
  pairs
    .filter(([, v]) => v)
    .map(
      ([k, v]) =>
        `<tr><td style="padding:6px 14px 6px 0;color:#8A8578;font:600 12px/1.4 monospace;white-space:nowrap;vertical-align:top">${esc(
          k
        )}</td><td style="padding:6px 0;color:#111;font:400 14px/1.5 system-ui">${esc(
          v
        ).replace(/\n/g, "<br>")}</td></tr>`
    )
    .join("");

/** The three forms, each declaring what it needs and what it becomes. */
const FORMS = {
  order: (d) => {
    const email = clean(d.email, LIMITS.email);
    const shoe = clean(d.shoe, LIMITS.short);
    if (!isEmail(email)) return { error: "ADD AN EMAIL SO WE CAN REPLY" };
    if (!shoe) return { error: "TELL US THE SHOE — WE CUT THE OUTLINE TO IT" };
    return {
      to: "orders",
      replyTo: email,
      subject: `BUILD REQUEST · ${clean(d.fit, 20)} ${clean(d.size, 8)} · ${shoe}`,
      pairs: [
        ["EMAIL", email],
        ["SHOE", shoe],
        ["SIZE", clean(d.size, 8)],
        ["FIT", clean(d.fit, 20)],
        ["WIDTH", clean(d.width, 20)],
        ["ARCH", clean(d.arch, 20)],
        ["FEEL", clean(d.feel, 40)],
        ["CELL / WALL", `${clean(d.cell, 8)} mm / ${clean(d.wall, 8)} mm`],
        ["DENSITY", clean(d.density, 20)],
        ["PAY", clean(d.pay, 20)],
        ["NOTES", clean(d.notes, LIMITS.long)],
      ],
    };
  },
  custom: (d) => {
    const email = clean(d.email, LIMITS.email);
    if (!isEmail(email)) return { error: "WE NEED AN EMAIL TO SEND THE SAMPLE PLAN" };
    return {
      to: "orders",
      replyTo: email,
      subject: `CUSTOM RUN · ${clean(d.brand, 60) || "UNNAMED MARK"} · ${clean(d.qty, 20)}`,
      pairs: [
        ["EMAIL", email],
        ["BRAND", clean(d.brand, LIMITS.short)],
        ["QUANTITY", clean(d.qty, 20)],
        ["ARTWORK", clean(d.file, LIMITS.short)],
        ["NOTES", clean(d.notes, LIMITS.long)],
      ],
    };
  },
  contact: (d) => {
    const email = clean(d.email, LIMITS.email);
    const msg = clean(d.msg, LIMITS.long);
    if (!isEmail(email)) return { error: "ADD AN EMAIL SO WE CAN REPLY" };
    if (!msg) return { error: "ADD A MESSAGE" };
    return {
      to: "general",
      replyTo: email,
      subject: `${clean(d.topic, 20) || "OTHER"} · ${email}`,
      pairs: [
        ["EMAIL", email],
        ["TOPIC", clean(d.topic, 20)],
        ["MESSAGE", msg],
      ],
    };
  },
  /**
   * A meeting REQUEST, not a booking. The person names windows that suit them
   * and a human confirms one, so nothing here reserves anything and there is no
   * calendar state to fall out of step with reality. That is the whole design:
   * a picker that hands out confirmed times needs somewhere to store them, and
   * storing them badly is worse than not offering the feature at all.
   *
   * Windows arrive as an array of short labels. They are cleaned, de-duplicated
   * and capped HERE rather than trusted from the page, because the page is not
   * the only thing that can POST to this endpoint.
   */
  book: (d) => {
    const email = clean(d.email, LIMITS.email);
    const slots = (Array.isArray(d.slots) ? d.slots : [])
      .map((v) => clean(v, 24))
      .filter(Boolean);
    const uniq = [...new Set(slots)].slice(0, 3);
    if (!isEmail(email)) return { error: "ADD AN EMAIL SO WE CAN CONFIRM" };
    if (!uniq.length) return { error: "PICK AT LEAST ONE WINDOW THAT SUITS YOU" };
    const topic = clean(d.topic, 20) || "OTHER";
    return {
      // an order or a custom run is a print conversation; press and anything
      // else is not. Same split the other three forms already use.
      to: topic === "ORDER" || topic === "CUSTOM" ? "orders" : "general",
      replyTo: email,
      subject: `CALL REQUEST · ${clean(d.mins, 12) || "30 MIN"} · ${topic} · ${email}`,
      pairs: [
        ["EMAIL", email],
        ["LENGTH", clean(d.mins, 12)],
        ["ABOUT", topic],
        ["WINDOWS", uniq.join("  ·  ")],
        ["TIMEZONE", clean(d.tz, 60)],
        ["NOTES", clean(d.notes, LIMITS.long)],
      ],
    };
  },
};

async function verifyTurnstile(token, ip, secret) {
  if (!secret) return { ok: false, why: "TURNSTILE_SECRET is not set" };
  if (!token) return { ok: false, why: "no turnstile token" };
  const body = new FormData();
  body.append("secret", secret);
  body.append("response", token);
  if (ip) body.append("remoteip", ip);
  const r = await fetch(TURNSTILE_VERIFY, { method: "POST", body });
  const out = await r.json();
  return out.success
    ? { ok: true }
    : { ok: false, why: (out["error-codes"] || []).join(",") || "rejected" };
}

export async function onRequestPost({ request, env }) {
  let payload;
  try {
    payload = await request.json();
  } catch {
    return json(400, { ok: false, error: "MALFORMED REQUEST" });
  }

  const build = FORMS[payload && payload.form];
  if (!build) return json(400, { ok: false, error: "UNKNOWN FORM" });

  const gate = await verifyTurnstile(
    payload.token,
    request.headers.get("cf-connecting-ip"),
    env.TURNSTILE_SECRET
  );
  if (!gate.ok) {
    console.log("turnstile rejected:", gate.why);
    return json(403, { ok: false, error: "VERIFICATION FAILED — RELOAD AND RETRY" });
  }

  const spec = build(payload.data || {});
  if (spec.error) return json(422, { ok: false, error: spec.error });

  if (!env.RESEND_API_KEY || !env.MAIL_FROM) {
    console.log("mail not configured: RESEND_API_KEY / MAIL_FROM missing");
    return json(500, { ok: false, error: "THE LAB'S MAILBOX IS DOWN — EMAIL US DIRECTLY" });
  }

  const to =
    spec.to === "orders"
      ? env.MAIL_TO_ORDERS || "print@bullprintlab.com"
      : env.MAIL_TO_GENERAL || "bull@bullprintlabs.com";

  const res = await fetch(RESEND_SEND, {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.RESEND_API_KEY}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      from: env.MAIL_FROM,
      to: [to],
      reply_to: spec.replyTo,
      subject: spec.subject,
      html:
        `<div style="background:#0B0B0D;padding:20px 24px"><span style="color:#E8B23A;font:800 15px/1 system-ui;letter-spacing:.14em">BULLPRINT LAB</span>` +
        `<span style="color:#5C5952;font:600 12px/1 monospace;letter-spacing:.14em"> · ${esc(
          payload.form.toUpperCase()
        )}</span></div>` +
        `<table style="border-collapse:collapse;margin:20px 24px">${rows(spec.pairs)}</table>` +
        `<p style="margin:24px;color:#8A8578;font:400 12px/1.5 system-ui">Reply to this email and it goes straight to them.</p>`,
      text: spec.pairs
        .filter(([, v]) => v)
        .map(([k, v]) => `${k}: ${v}`)
        .join("\n"),
    }),
  });

  if (!res.ok) {
    console.log("resend failed:", res.status, await res.text());
    return json(502, { ok: false, error: "COULD NOT SEND — EMAIL US DIRECTLY" });
  }

  return json(200, { ok: true });
}

/** Anything but POST on this path is a mistake, not a route. */
export async function onRequest({ request }) {
  if (request.method === "POST") return onRequestPost(...arguments);
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "access-control-allow-origin": "https://bullprintlab.com",
        "access-control-allow-methods": "POST, OPTIONS",
        "access-control-allow-headers": "content-type",
        "access-control-max-age": "86400",
      },
    });
  }
  return json(405, { ok: false, error: "POST ONLY" });
}
