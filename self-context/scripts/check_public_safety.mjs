import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";

const repoRoot = process.cwd();
const files = execFileSync("git", ["ls-files", "--cached", "--others", "--exclude-standard"], {
  cwd: repoRoot,
  encoding: "utf8",
})
  .split(/\r?\n/)
  .filter(Boolean)
  .filter((file) => !file.includes("node_modules/"))
  .filter((file) => !file.endsWith("package-lock.json"))
  .filter((file) => file !== "scripts/check_public_safety.mjs");

const privateTerms = [
  /\bHanje\b/i,
  /\bhanjeahwan\b/i,
  /\bPulsifi\b/i,
  /\bcheeyuen\b/i,
  /\b0102438414\b/,
  /\bhanjeahwan@gmail\.com\b/i,
];

const secretPatterns = [
  /\bsk-[A-Za-z0-9_-]{20,}\b/,
  /\bATATT[A-Za-z0-9_\-=]{20,}\b/,
  /\bghp_[A-Za-z0-9_]{20,}\b/,
  /\bgithub_pat_[A-Za-z0-9_]{20,}\b/,
];

const forbiddenRepoPaths = [
  /^sources\//,
  /^events\//,
  /^derived\//,
  /^exports\//,
  /^profiles\//,
  /^reports\//,
  /^ledger\//,
  /^\.self-context\//,
];

const failures = [];

for (const file of files) {
  if (forbiddenRepoPaths.some((pattern) => pattern.test(file))) {
    failures.push(`${file}: private ledger path is tracked`);
    continue;
  }

  const absolute = path.join(repoRoot, file);
  let text = "";
  try {
    text = readFileSync(absolute, "utf8");
  } catch {
    continue;
  }

  for (const pattern of privateTerms) {
    if (pattern.test(text)) {
      failures.push(`${file}: contains private showcase term ${pattern}`);
    }
  }

  for (const pattern of secretPatterns) {
    if (pattern.test(text)) {
      failures.push(`${file}: contains secret-like token ${pattern}`);
    }
  }
}

if (failures.length > 0) {
  console.error("Public safety check failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log(`Public safety check passed for ${files.length} tracked files.`);
