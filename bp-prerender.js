/* BullPrint Lab — drop the static copy once the runtime is live.
 *
 * Both pages (the site and /platform/) ship a pre-rendered copy of themselves
 * for crawlers that do not execute JavaScript. It is shown first and dropped
 * the moment the runtime has swapped <x-dc> for the live app, or the visitor
 * sees the same content twice.
 *
 * Watching for x-dc to disappear is the honest signal — a timer would either
 * flash duplicate content on a slow device or blank the page on a fast one.
 *
 * This lives in its own file rather than inside bp-forms.js because the
 * platform app has no forms and must not pull in the site's form wiring, and
 * because a FILE is what the CSP allows: script-src has no 'unsafe-inline',
 * and an inline copy of this took production down once already.
 */
(function () {
  "use strict";

  function dropPrerender() {
    var pre = document.getElementById("bp-prerender");
    if (!pre) return;
    if (document.querySelector("x-dc")) { requestAnimationFrame(dropPrerender); return; }
    pre.remove();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", dropPrerender);
  } else {
    dropPrerender();
  }
})();
