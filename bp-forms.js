/* BullPrint Lab — form submission.
 *
 * The design's three forms originally just flipped a "sent" flag in local
 * state: they looked like they worked and nothing left the browser. This gives
 * them somewhere to go — POST /api/submit, a Pages Function on the same origin,
 * which verifies Turnstile and sends through Resend.
 *
 * Turnstile lives OUTSIDE the React tree on purpose. The page is rendered by
 * the Claude Design runtime, so anything mounted inside it gets torn out on the
 * next re-render — and a captcha widget that vanishes mid-form is worse than no
 * captcha. One invisible widget is rendered once against <body> and executed on
 * demand, returning a fresh token per submission.
 *
 * Exposes window.bpSend(kind, data) -> Promise. Rejects with an Error whose
 * message is already in the site's voice, because that string goes straight
 * into the form's own error slot.
 */
(function () {
  "use strict";

  var SITEKEY = "0x4AAAAAAEQBxUgUlUeDfZjS";
  var ENDPOINT = "/api/submit";
  var widgetId = null;
  var pending = null;

  function container() {
    var el = document.getElementById("bp-turnstile");
    if (!el) {
      el = document.createElement("div");
      el.id = "bp-turnstile";
      document.body.appendChild(el);
    }
    return el;
  }

  function ready() {
    if (widgetId !== null) return true;
    if (!window.turnstile) return false;
    widgetId = window.turnstile.render(container(), {
      sitekey: SITEKEY,
      execution: "execute",
      appearance: "interaction-only",
      callback: function (token) {
        if (pending) { pending.resolve(token); pending = null; }
      },
      "error-callback": function () {
        if (pending) { pending.reject(new Error("net")); pending = null; }
      },
      "timeout-callback": function () {
        if (pending) { pending.reject(new Error("net")); pending = null; }
      },
    });
    return true;
  }

  /** A fresh token per submission — Turnstile tokens are single-use. */
  function token() {
    return new Promise(function (resolve, reject) {
      if (!ready()) { reject(new Error("net")); return; }
      pending = { resolve: resolve, reject: reject };
      try {
        window.turnstile.reset(widgetId);
        window.turnstile.execute(widgetId);
      } catch (e) {
        pending = null;
        reject(new Error("net"));
      }
      setTimeout(function () {
        if (pending) { pending.reject(new Error("net")); pending = null; }
      }, 25000);
    });
  }

  window.bpSend = function (kind, data) {
    return token()
      .then(function (t) {
        return fetch(ENDPOINT, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ form: kind, token: t, data: data }),
        });
      })
      .then(function (r) {
        return r.json().then(function (b) { return { r: r, b: b }; });
      })
      .then(function (x) {
        if (x.r.ok && x.b && x.b.ok) return true;
        throw new Error(
          (x.b && x.b.error) || "COULDN'T SEND — EMAIL BULL@BULLPRINTLAB.COM"
        );
      })
      .catch(function (e) {
        // A network or Turnstile failure must never read like a validation
        // error; the person did nothing wrong and needs a way through.
        if (e && e.message === "net") {
          throw new Error("CONNECTION DROPPED — RETRY, OR EMAIL BULL@BULLPRINTLAB.COM");
        }
        throw e;
      });
  };

  /* The static copy shipped for non-JS crawlers is shown first and dropped the
   * moment the runtime has swapped <x-dc> for the live app. Watching for x-dc
   * to disappear is the honest signal — a timer would either flash duplicate
   * content on a slow device or blank the page on a fast one. */
  function dropPrerender() {
    var pre = document.getElementById("bp-prerender");
    if (!pre) return;
    if (document.querySelector("x-dc")) { requestAnimationFrame(dropPrerender); return; }
    pre.remove();
  }

  function start() { ready(); dropPrerender(); }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
