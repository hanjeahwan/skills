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
  "## Profile decision",
  "## Library discovery evidence",
  "## Prior learning applied",
  "## Public exports",
  "## Props",
  "## Semantic DOM and styling hooks",
  "## Runtime behavior",
  "## Styling behavior matrix",
  "## Layout and visual ownership matrix",
  "## Docs demo parity matrix",
  "## Positioning and containing-block matrix",
  "## CSS ownership and source leakage audit",
  "## Tailwind-first styling audit",
  "## Viewer shell and global CSS audit",
  "## Refs, static members, and imperative API",
  "## Runtime warnings and developer feedback",
  "## Verification ownership and subagent audit log",
  "## Subagent dispatch log",
  "## False-pass prevention assertions",
  "## Independent verifier report",
  "## Accessibility and keyboard behavior",
  "## Cross-project edge-case gate",
  "## Deprecated API decision",
  "## Deliberate non-goals",
  "## Acceptance checklist",
];

const checklistItems = [
  "Target stack verified",
  "Profile decision recorded",
  "Library discovery evidence complete",
  "Source API traced",
  "Deprecated/legacy API decision recorded",
  "Provider/default context checked",
  "Internal primitive delegation checked",
  "Semantic DOM slots mapped",
  "Docs demos copied as fixtures",
  "Style graph fully translated",
  "Layout and visual ownership verified",
  "Tailwind-first styling verified",
  "Theme token inheritance verified",
  "Token units preserved",
  "Positioned elements traced",
  "Connectors/tracks/separators asserted",
  "Source CSS leakage prevented",
  "Viewer shell/global CSS isolated",
  "Refs and imperative API verified",
  "Runtime warnings decided",
  "Controlled/uncontrolled behavior verified",
  "Keyboard/focus/IME behavior verified",
  "Portal/z-index/stacking behavior verified",
  "Locale/date/time behavior verified",
  "Accessibility verified",
  "Browser visual evidence captured",
  "Agent execution mode recorded",
  "Independent verifier completed",
  "Subagent side-branch audits completed",
  "False-pass prevention assertions landed",
  "Benchmark/viewer scope decided",
  "Learnings/profile updates captured",
  "Learning regression assertions landed",
];

const validStatuses = new Set(["pass", "not applicable", "source-backed non-goal", "blocked"]);

const section = (heading) => {
  const start = text.indexOf(heading);
  if (start < 0) return "";
  const rest = text.slice(start + heading.length);
  const next = rest.search(/\r?\n##\s+/);
  return next < 0 ? rest : rest.slice(0, next);
};

const isPlaceholder = (value) => {
  const trimmed = (value ?? "").trim();
  return !trimmed || /^<[^>]+>$/.test(trimmed) || /\b(todo|tbd|placeholder)\b/i.test(trimmed);
};

for (const heading of requiredHeadings) {
  if (!text.includes(heading)) fail(`missing heading: ${heading}`);
  else ok(`heading exists: ${heading}`);
}

const profileText = section("## Profile decision");
if (!/profiles\/[a-z0-9-]+\.md|temporary profile/i.test(profileText)) {
  fail("profile decision must name a known profile path or a temporary profile");
}

const discoveryText = section("## Library discovery evidence");
for (const required of [
  "Source docs/source/package",
  "API extraction path",
  "Demo/examples path",
  "Theme/token model",
  "Slot/class/style API",
  "Internal primitives",
  "Deprecated/legacy policy",
  "Source CSS deny patterns",
]) {
  if (!discoveryText.includes(required)) fail(`library discovery evidence missing row: ${required}`);
}

const checklistText = section("## Acceptance checklist");
if (!/\|\s*Item\s*\|\s*Status\s*\|\s*Evidence\s*\|\s*Implementation\s*\|\s*Verified by\s*\|/i.test(checklistText)) {
  fail("acceptance checklist must include Item, Status, Evidence, Implementation, and Verified by columns");
}

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
  if (!validStatuses.has(status)) fail(`invalid status for ${item}: ${status || "<missing>"}`);
  else ok(`valid status for ${item}: ${status}`);

  if (cells.length < 5) {
    fail(`missing Verified by cell for ${item}`);
    continue;
  }

  const evidence = cells[2];
  const implementation = cells[3];
  const verifiedBy = cells[4];

  if (status === "blocked" && !allowBlocked) fail(`blocked acceptance checklist item: ${item}`);
  if (status !== "blocked") {
    if (isPlaceholder(evidence)) fail(`missing concrete evidence for ${item}`);
    if (isPlaceholder(implementation)) fail(`missing concrete implementation for ${item}`);
    if (isPlaceholder(verifiedBy)) fail(`missing verifier attribution for ${item}`);
  }

  if (
    status === "pass" &&
    [
      "Independent verifier completed",
      "Browser visual evidence captured",
      "Docs demos copied as fixtures",
      "Positioned elements traced",
      "Connectors/tracks/separators asserted",
      "Learnings/profile updates captured",
      "Learning regression assertions landed",
    ].includes(item) &&
    !/(ui_[a-z_]+|generic-subagent|subagent|verifier|agent)/i.test(`${evidence} ${implementation} ${verifiedBy}`)
  ) {
    fail(`${item} must include independent verifier or subagent attribution`);
  }
}

const ownershipText = section("## Verification ownership and subagent audit log");
if (!/\|\s*Audit branch\s*\|\s*Dispatch mode\s*\|\s*Agent or subagent role\s*\|\s*Owner\s*\|/i.test(ownershipText)) {
  fail("verification ownership table must include Dispatch mode, Agent or subagent role, and Owner columns");
}
if (!/(custom-agent|generic-subagent|self-review-blocked)/.test(ownershipText)) {
  fail("verification ownership table must record a dispatch mode");
}
if (!/(ui_(profile_builder|source_auditor|style_graph_auditor|demo_parity_auditor|browser_geometry_verifier|contract_closure_verifier|learning_promoter)|generic subagent)/.test(ownershipText)) {
  fail("verification ownership table must name a bundled custom agent or equivalent generic subagent role");
}

const dispatchText = section("## Subagent dispatch log");
if (!/\|\s*Branch\s*\|\s*Dispatch mode\s*\|\s*Agent\/subagent\s*\|\s*Fallback reason\s*\|/i.test(dispatchText)) {
  fail("subagent dispatch log must include Branch, Dispatch mode, Agent/subagent, and Fallback reason columns");
}
if (!/(custom-agent|generic-subagent|self-review-blocked)/.test(dispatchText)) fail("subagent dispatch log must record dispatch mode");

const tailwindText = section("## Tailwind-first styling audit");
if (!/Tailwind|utility|source-backed non-goal/i.test(tailwindText)) {
  fail("tailwind-first styling audit must include utility-first evidence or source-backed non-goal");
}

const leakageText = section("## CSS ownership and source leakage audit");
if (!/(deny|forbidden|check-no-source-css|source CSS|prefix)/i.test(leakageText)) {
  fail("source leakage audit must name deny patterns or no-source-css check evidence");
}

const verifierReport = section("## Independent verifier report");
if (text.includes("## Independent verifier report")) {
  if (!/Verifier:\s*(?!<)/i.test(verifierReport)) fail("independent verifier report is missing concrete Verifier");
  const dispatchMode = verifierReport.match(/Dispatch mode:\s*([^\r\n]+)/i)?.[1]?.trim();
  if (!dispatchMode) fail("independent verifier report is missing Dispatch mode");
  else if (!["custom-agent", "generic-subagent", "self-review-blocked"].includes(dispatchMode)) fail(`independent verifier report has invalid Dispatch mode: ${dispatchMode}`);
  else if (!allowBlocked && dispatchMode === "self-review-blocked") fail("independent verifier report cannot use self-review-blocked for final acceptance");

  if (!/Custom agent:\s*(?!<)/i.test(verifierReport)) fail("independent verifier report is missing concrete Custom agent");
  else if (!/(ui_browser_geometry_verifier|ui_contract_closure_verifier|not available)/i.test(verifierReport)) {
    fail("independent verifier report must name an expected verifier custom agent or not available");
  }

  const fallbackReason = verifierReport.match(/Fallback reason:\s*([^\r\n]+)/i)?.[1]?.trim();
  if (!fallbackReason) fail("independent verifier report is missing Fallback reason");
  else if (!["none", "custom-agent-unavailable", "subagent-unavailable"].includes(fallbackReason)) fail(`independent verifier report has invalid Fallback reason: ${fallbackReason}`);
  if (dispatchMode === "custom-agent" && fallbackReason !== "none") fail("custom-agent dispatch mode must use Fallback reason: none");
  if (dispatchMode === "generic-subagent" && fallbackReason !== "custom-agent-unavailable") fail("generic-subagent dispatch mode must use Fallback reason: custom-agent-unavailable");
  if (dispatchMode === "self-review-blocked" && fallbackReason !== "subagent-unavailable") fail("self-review-blocked dispatch mode must use Fallback reason: subagent-unavailable");

  if (!/Falsification attempts:\s*[\s\S]*?-\s*(?!<)/i.test(verifierReport)) fail("independent verifier report is missing falsification attempts");
  const finalVerdict = verifierReport.match(/Final verdict:\s*([^\r\n]+)/i)?.[1]?.trim();
  if (!finalVerdict) fail("independent verifier report is missing Final verdict");
  else if (!allowBlocked && finalVerdict !== "verified-pass") fail(`independent verifier final verdict is not verified-pass: ${finalVerdict}`);
  if (!/Risk note:\s*(?!<)/i.test(verifierReport)) fail("independent verifier report is missing concrete Risk note");
}

if (/### Regression assertion[\s\S]*?<one objective assertion/.test(text)) fail("learning regression assertion is still a placeholder");
if (/\bMigration completed\b/i.test(text) && /self-review-blocked/i.test(text) && !allowBlocked) {
  fail("contract cannot claim Migration completed with self-review-blocked evidence");
}

if (!process.exitCode) ok("migration contract check passed");
