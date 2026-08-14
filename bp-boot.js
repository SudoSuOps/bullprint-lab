/* BullPrint Lab — hand the parked template to the runtime.
 *
 * The design's <x-dc> template ships inside an inert <template> so that naive
 * text extraction (most AI crawlers) never reads its 80 {{ }} expressions as if
 * they were copy. Inert also means the runtime cannot see it, so it gets cloned
 * into the document here, before DOMContentLoaded, which is when support.js
 * boots and looks for <x-dc>.
 *
 * This is a FILE and not an inline <script> on purpose. Inline was blocked by
 * the site's own CSP the moment it hit production — the page rendered its static
 * copy, removed it, and went black, because script-src has no 'unsafe-inline'.
 * A CSP hash would also have worked and would have broken again the next time a
 * character in it changed. Same-origin file, nothing to keep in sync.
 */
(function () {
  "use strict";
  var t = document.getElementById("bp-tpl");
  if (!t || !t.content) return;
  t.parentNode.insertBefore(t.content.cloneNode(true), t);
  t.remove();
})();
