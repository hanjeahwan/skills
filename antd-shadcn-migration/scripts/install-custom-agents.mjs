import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourceDir = path.join(root, "agents");
const args = process.argv.slice(2);

const usage = () => {
  console.error("Usage:");
  console.error("  node scripts/install-custom-agents.mjs --scope user [--force]");
  console.error("  node scripts/install-custom-agents.mjs --scope project --target <repo> [--force]");
  process.exit(2);
};

const readFlag = (name) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
};

const hasFlag = (name) => args.includes(name);
const scope = readFlag("--scope");
const target = readFlag("--target");
const force = hasFlag("--force");

if (!scope || !["user", "project"].includes(scope)) usage();
if (scope === "project" && !target) usage();
if (!fs.existsSync(sourceDir)) {
  console.error(`Missing source agents directory: ${sourceDir}`);
  process.exit(1);
}

const destinationDir =
  scope === "user"
    ? path.join(os.homedir(), ".codex", "agents")
    : path.join(path.resolve(target), ".codex", "agents");

const files = fs
  .readdirSync(sourceDir)
  .filter((file) => file.endsWith(".toml"))
  .sort();

if (files.length === 0) {
  console.error(`No agent templates found in ${sourceDir}`);
  process.exit(1);
}

fs.mkdirSync(destinationDir, { recursive: true });

const installed = [];
const overwritten = [];
const skipped = [];

for (const file of files) {
  const source = path.join(sourceDir, file);
  const destination = path.join(destinationDir, file);
  const exists = fs.existsSync(destination);

  if (exists && !force) {
    skipped.push(file);
    continue;
  }

  fs.copyFileSync(source, destination);
  if (exists) overwritten.push(file);
  else installed.push(file);
}

const displayPath = destinationDir.replaceAll(path.sep, "/");

console.log(`Custom agents destination: ${displayPath}`);
console.log(`Installed: ${installed.length ? installed.join(", ") : "none"}`);
console.log(`Overwritten: ${overwritten.length ? overwritten.join(", ") : "none"}`);
console.log(`Skipped: ${skipped.length ? skipped.join(", ") : "none"}`);
console.log("Restart Codex or open a new Codex session so the custom agents are loaded.");
console.log("Until they are callable in the current session, dispatch equivalent fresh-context generic subagents and record fallback reason: custom-agent-unavailable.");
