/**
 * Proof for the /api/submit validators. Run from the repo root:
 *
 *     node functions/api/submit.test.mjs
 *
 * No runner, no dependencies — the repo has neither, and a test that needs a
 * toolchain installed before it can be believed is a test nobody runs.
 *
 * It imports the real module, with only the Cloudflare entry points stripped,
 * so what is under test is exactly the code that ships. The `book` form gets
 * the most attention because it is the newest and because it takes an ARRAY
 * from a stranger, which is the one input shape here that can arrive as
 * something other than a string.
 */
import { readFileSync } from "node:fs";

let src = readFileSync(new URL("./submit.js", import.meta.url), "utf8");
src = src.replace(/export async function[\s\S]*$/, "") + "\nexport { FORMS };";
const { FORMS } = await import(
  "data:text/javascript;base64," + Buffer.from(src).toString("base64")
);

let pass = 0;
const failures = [];
const t = (name, got, want) => {
  if (JSON.stringify(got) === JSON.stringify(want)) {
    pass++;
    console.log(`  ok    ${name}`);
  } else {
    failures.push(name);
    console.log(`  FAIL  ${name}`);
    console.log(`          got  ${JSON.stringify(got)}`);
    console.log(`          want ${JSON.stringify(want)}`);
  }
};
const pair = (r, k) => (r.pairs || []).find(([a]) => a === k)?.[1];

const { book, contact } = FORMS;

console.log("book — what it refuses");
t("no email", book({ slots: ["MON AM"] }).error, "ADD AN EMAIL SO WE CAN CONFIRM");
t("malformed email", book({ email: "nope", slots: ["MON AM"] }).error,
  "ADD AN EMAIL SO WE CAN CONFIRM");
t("no windows", book({ email: "a@b.co" }).error,
  "PICK AT LEAST ONE WINDOW THAT SUITS YOU");
t("windows that are all blank", book({ email: "a@b.co", slots: ["", "  "] }).error,
  "PICK AT LEAST ONE WINDOW THAT SUITS YOU");
// the page always sends an array; anything else reached this endpoint directly
t("windows sent as a string, not an array",
  book({ email: "a@b.co", slots: "MON AM" }).error,
  "PICK AT LEAST ONE WINDOW THAT SUITS YOU");
t("windows sent as null", book({ email: "a@b.co", slots: null }).error,
  "PICK AT LEAST ONE WINDOW THAT SUITS YOU");

console.log("\nbook — where it routes");
const req = book({ email: "a@b.co", slots: ["MON AM"], mins: "30 MIN", topic: "PRESS" });
t("a valid request has no error", req.error, undefined);
t("press is not a print conversation", req.to, "general");
t("order is", book({ email: "a@b.co", slots: ["MON AM"], topic: "ORDER" }).to, "orders");
t("custom is", book({ email: "a@b.co", slots: ["MON AM"], topic: "CUSTOM" }).to, "orders");
t("a missing topic defaults to OTHER, so general",
  book({ email: "a@b.co", slots: ["MON AM"] }).to, "general");
t("the sender is the reply-to", req.replyTo, "a@b.co");
t("the subject carries length and topic", req.subject,
  "CALL REQUEST · 30 MIN · PRESS · a@b.co");
t("a missing length still reads as 30 MIN",
  book({ email: "a@b.co", slots: ["MON AM"] }).subject,
  "CALL REQUEST · 30 MIN · OTHER · a@b.co");

console.log("\nbook — the window set is cleaned here, not on the page");
t("duplicates collapse",
  pair(book({ email: "a@b.co", slots: ["MON AM", "MON AM", "TUE PM"] }), "WINDOWS"),
  "MON AM  ·  TUE PM");
t("more than three are capped",
  pair(book({ email: "a@b.co", slots: ["MON AM", "TUE AM", "WED AM", "THU AM"] }), "WINDOWS"),
  "MON AM  ·  TUE AM  ·  WED AM");
t("newlines inside a label collapse",
  pair(book({ email: "a@b.co", slots: ["MON\n\nAM"] }), "WINDOWS"), "MON AM");

console.log("\nbook — nothing a stranger types sets its own length");
const nasty = book({
  email: "a@b.co",
  slots: ["<script>alert(1)</script>"],
  topic: "<b>x</b>",
  notes: "x".repeat(5000),
});
t("a long window label is cut to 24", pair(nasty, "WINDOWS").length <= 24, true);
t("notes are cut to the long limit", pair(nasty, "NOTES").length, 2000);
t("topic is cut to 20", pair(nasty, "ABOUT").length <= 20, true);

console.log("\ncontact — unchanged by the booking work");
t("still needs a message", contact({ email: "a@b.co" }).error, "ADD A MESSAGE");
t("still needs an email", contact({ msg: "hi" }).error, "ADD AN EMAIL SO WE CAN REPLY");
t("still routes to general", contact({ email: "a@b.co", msg: "hi" }).to, "general");

console.log(`\n${pass} passed, ${failures.length} failed`);
if (failures.length) {
  console.log(failures.map((f) => `  - ${f}`).join("\n"));
  process.exit(1);
}
