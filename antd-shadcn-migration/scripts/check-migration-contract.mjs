import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const allowBlocked = args.includes("--allow-blocked");
const contractPath = args.find((arg) => arg !== "--allow-blocked");
if (!contractPath) {
  console.error("Usage: node scripts/check-migration-contract.mjs <contract.md> [--allow-blocked]");
  process.exit(2);
}

const absolutePath = path.resolve(contractPath);
const text = fs.readFileSync(absolutePath, "utf8");
const fail = (message) => {
  console.error(`FAIL: ${message}`);
  process.exitCode = 1;
};
const ok = (message) => console.log(`OK: ${message}`);

const requiredHeadings = [
  "## Prior learning applied",
  "## Public exports",
  "## Props",
  "## Semantic DOM and styling hooks",
  "## Runtime behavior",
  "## Styling behavior matrix",
  "## Layout and visual ownership matrix",
  "## Docs demo parity matrix",
  "## Positioning and containing-block matrix",
  "## CSS ownership and Ant leakage audit",
  "## Viewer shell and global CSS audit",
  "## Refs, static members, and imperative API",
  "## Runtime warnings and developer feedback",
  "## Verification ownership and subagent audit log",
  "## False-pass prevention assertions",
  "## Independent verifier report",
  "## Accessibility and keyboard behavior",
  "## Cross-project edge-case gate",
  "## Deprecated API decision",
  "## Deliberate non-goals",
  "## Acceptance checklist",
];

for (const heading of requiredHeadings) {
  if (!text.includes(heading)) fail(`missing heading: ${heading}`);
  else ok(`heading exists: ${heading}`);
}

const validStatuses = new Set(["pass", "not applicable", "source-backed non-goal", "blocked"]);
const checklistItems = [
  "Target stack verified",
  "Ant source API traced",
  "Deprecated API decision recorded",
  "ConfigProvider/default context checked",
  "rc/shared primitive delegation checked",
  "Semantic DOM slots mapped",
  "Docs demos copied as fixtures",
  "Style graph fully translated",
  "Layout and visual ownership verified",
  "Token units preserved",
  "Positioned elements traced",
  "Connectors/tracks/separators asserted",
  "Ant CSS leakage prevented",
  "Viewer shell/global CSS isolated",
  "Refs and imperative API verified",
  "Runtime warnings decided",
  "Controlled/uncontrolled behavior verified",
  "Keyboard/focus/IME behavior verified",
  "Portal/z-index/stacking behavior verified",
  "Locale/date/time behavior verified",
  "Accessibility verified",
  "Browser visual evidence captured",
  "Independent verifier completed",
  "Subagent side-branch audits completed",
  "False-pass prevention assertions landed",
  "Benchmark/viewer gate aligned",
  "Benchmark/viewer scope decided",
  "Learnings captured and promoted",
  "Learning regression assertions landed",
];

const checklistStart = text.indexOf("## Acceptance checklist");
if (checklistStart >= 0) {
  const checklistText = text.slice(checklistStart).split(/\r?\n##\s+/)[0];
  if (!/\|\s*Item\s*\|\s*Status\s*\|\s*Evidence\s*\|\s*Implementation\s*\|\s*Verified by\s*\|/i.test(checklistText)) {
    fail("acceptance checklist must include a Verified by column");
  }

  const isPlaceholder = (value) => {
    const trimmed = (value ?? "").trim();
    return !trimmed || /^<[^>]+>$/.test(trimmed) || /\b(todo|tbd|placeholder)\b/i.test(trimmed);
  };

  for (const item of checklistItems) {
    const row = checklistText
      .split(/\r?\n/)
      .find((line) => line.startsWith("|") && line.includes(`| ${item} |`));
    if (!row) {
      fail(`missing acceptance checklist item: ${item}`);
      continue;
    }
    const cells = row.split("|").map((cell) => cell.trim()).filter(Boolean);
    const status = cells[1];
    if (!validStatuses.has(status)) fail(`invalid status for ${item}: ${status}`);
    else ok(`valid status for ${item}: ${status}`);

    if (cells.length < 5) {
      fail(`missing Verified by cell for ${item}`);
      continue;
    }

    const evidence = cells[2];
    const implementation = cells[3];
    const verifiedBy = cells[4];

    if (status === "blocked" && !allowBlocked) {
      fail(`blocked acceptance checklist item: ${item}`);
    }

    if (status !== "blocked") {
      if (isPlaceholder(evidence)) fail(`missing concrete evidence for ${item}`);
      if (isPlaceholder(implementation)) fail(`missing concrete implementation for ${item}`);
      if (isPlaceholder(verifiedBy)) fail(`missing verifier attribution for ${item}`);
    }

    if (
      status === "pass" &&
      item === "Independent verifier completed" &&
      !/(subagent|verifier|reviewer|fallback|user-approved|agent)/i.test(`${evidence} ${implementation} ${verifiedBy}`)
    ) {
      fail("Independent verifier completed row must name verifier evidence");
    }
  }
}

if (!/Benchmark\/viewer scope decided/.test(text)) {
  fail("missing benchmark/viewer scope decision");
}

const verifierReport = text.slice(text.indexOf("## Independent verifier report"));
if (text.includes("## Independent verifier report")) {
  if (!/Verifier:\s*(?!<)/i.test(verifierReport)) fail("independent verifier report is missing concrete Verifier");
  if (!/Falsification attempts:\s*[\s\S]*?-\s*(?!<)/i.test(verifierReport)) {
    fail("independent verifier report is missing falsification attempts");
  }
  const finalVerdict = verifierReport.match(/Final verdict:\s*([^\r\n]+)/i)?.[1]?.trim();
  if (!finalVerdict) fail("independent verifier report is missing Final verdict");
  else if (!allowBlocked && finalVerdict !== "verified-pass") {
    fail(`independent verifier final verdict is not verified-pass: ${finalVerdict}`);
  }
}

if (/### Regression assertion[\s\S]*?<one objective assertion/.test(text)) {
  fail("learning regression assertion is still a placeholder");
}

if (!process.exitCode) ok("migration contract check passed");
