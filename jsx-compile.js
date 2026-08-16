#!/usr/bin/env node
/*
 * Compile the design's .jsx x-import modules to plain .js, at BUILD time.
 *
 * WHY THIS EXISTS
 * ---------------
 * `support.js` resolves an x-import by extension:
 *
 *     const kindOf = (u) => /\.(jsx|tsx)(\?|#|$)/i.test(u) ? "jsx" : "js";
 *
 * and for kind "jsx" it calls `ensureBabel()`, which injects
 *
 *     https://unpkg.com/@babel/standalone@7.29.0/babel.min.js
 *
 * into the page. That is a 3 MB third-party script on a site whose CSP is
 * `script-src 'self'` with no external hosts — so the fetch is BLOCKED, the
 * module never loads, and the page renders nothing at all. The Bull Band promo
 * is the first page in this repo to use x-import, so it is the first time this
 * has mattered.
 *
 * Vendoring Babel would fix the CSP and cost every visitor 3 MB to compile
 * source the build already has. Compiling here instead costs the visitor
 * nothing: the emitted files end in .js, so `kindOf` returns "js", `ensureBabel`
 * is never reached, and the runtime path is otherwise byte-identical.
 *
 * EQUIVALENCE
 * -----------
 * The transform below uses the SAME compiler and the SAME options the runtime
 * would have used — `{ filename, presets: ["react", "typescript"] }` against
 * @babel/standalone 7.29.0, verified by build.py against the exact SRI hash
 * support.js pins for it. `filename` keeps the original .jsx name so the
 * typescript preset sees the same extension it would have in the browser.
 *
 *     node jsx-compile.js <babel.min.js> <out-dir> <src.jsx> [src.jsx ...]
 *
 * Driven by build.py; not intended to be run by hand.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const [, , babelPath, outDir, ...sources] = process.argv;

if (!babelPath || !outDir || sources.length === 0) {
  console.error("usage: node jsx-compile.js <babel.min.js> <out-dir> <src.jsx>...");
  process.exit(2);
}

// @babel/standalone is a UMD bundle that expects a browser-ish global. Run it in
// its own context rather than polluting this process, and hand it the two
// globals it probes for.
const sandbox = { window: {}, self: {}, global: {}, console, process };
sandbox.window = sandbox;
sandbox.self = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(babelPath, "utf8"), sandbox, { filename: babelPath });

const Babel = sandbox.Babel;
if (!Babel || typeof Babel.transform !== "function") {
  console.error("babel did not expose transform() — is " + babelPath + " the standalone build?");
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });

for (const src of sources) {
  const code = fs.readFileSync(src, "utf8");
  let out;
  try {
    out = Babel.transform(code, {
      // the name the runtime would have passed — keeps preset behaviour identical
      filename: "./" + path.basename(src),
      presets: ["react", "typescript"],
    }).code;
  } catch (e) {
    console.error("jsx-compile: " + src + "\n  " + e.message);
    process.exit(1);
  }
  const dest = path.join(outDir, path.basename(src).replace(/\.jsx$/, ".js"));
  fs.writeFileSync(dest, out);
  process.stdout.write(
    "  jsx        " + path.basename(src) + " -> " + path.relative(process.cwd(), dest) +
    "  (" + (out.length / 1024).toFixed(0) + " KB)\n"
  );
}
