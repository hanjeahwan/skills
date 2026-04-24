import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const profileIndex = args.indexOf("--profile");
const profilePath = profileIndex >= 0 ? args[profileIndex + 1] : undefined;
const targets = args.filter((arg, index) => arg !== "--profile" && index !== profileIndex + 1);

if (!profilePath || targets.length === 0) {
  console.error("Usage: node scripts/check-no-source-css.mjs --profile <profile.md> <target-path...>");
  process.exit(2);
}

const allowedDocSegments = new Set(["docs", "contracts", "migrations", "learnings", "references", "profiles"]);
const codeExtensions = new Set([".css", ".scss", ".sass", ".less", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]);
const fallbackDenyPatterns = [
  { name: "source class selector/string", regex: /\bant-[a-z0-9-]+/i },
  { name: "source CSS variable", regex: /--ant-[a-z0-9-]+/i },
  { name: "source generated CSS import", regex: /from\s+["']antd\/dist|import\s+["']antd\/dist|from\s+["']antd\/es\/.*\/style|import\s+["']antd\/es\/.*\/style/i },
  { name: "source prefix selector", regex: /\[class\*=["']ant-|\.ant-/i },
];

const fail = (message) => {
  console.error(`FAIL: ${message}`);
  process.exitCode = 1;
};
const ok = (message) => console.log(`OK: ${message}`);

const read = (file) => fs.readFileSync(file, "utf8");

const parseProfile = (file) => {
  const absolute = path.resolve(file);
  if (!fs.existsSync(absolute)) {
    fail(`profile does not exist: ${file}`);
    return { id: "unknown", patterns: fallbackDenyPatterns };
  }

  const text = read(absolute);
  const id = text.match(/^profile_id:\s*(.+)$/m)?.[1]?.trim() ?? path.basename(file, ".md");
  const lines = text.split(/\r?\n/);
  const patterns = [];
  let inPatterns = false;

  for (const line of lines) {
    if (/^runtime_css_deny_patterns:\s*$/.test(line.trim())) {
      inPatterns = true;
      continue;
    }
    if (inPatterns && /^##\s+/.test(line)) break;
    if (!inPatterns) continue;

    const match = line.match(/^\s*-\s*(.+?)\s*$/);
    if (!match) continue;
    let raw = match[1];
    if ((raw.startsWith('"') && raw.endsWith('"')) || (raw.startsWith("'") && raw.endsWith("'"))) {
      try {
        raw = JSON.parse(raw);
      } catch {
        raw = raw.slice(1, -1);
      }
    }
    try {
      patterns.push({ name: `${id} deny pattern ${patterns.length + 1}`, regex: new RegExp(raw, "i") });
    } catch (error) {
      fail(`invalid deny pattern in ${file}: ${raw} (${error.message})`);
    }
  }

  if (patterns.length === 0) {
    fail(`profile has no runtime_css_deny_patterns: ${file}`);
    return { id, patterns: fallbackDenyPatterns };
  }

  return { id, patterns };
};

const { id: profileId, patterns: forbiddenPatterns } = parseProfile(profilePath);

const walk = (entry) => {
  const absolute = path.resolve(entry);
  if (!fs.existsSync(absolute)) {
    fail(`path does not exist: ${entry}`);
    return [];
  }
  const stat = fs.statSync(absolute);
  if (stat.isFile()) return [absolute];
  if (!stat.isDirectory()) return [];

  const files = [];
  for (const child of fs.readdirSync(absolute, { withFileTypes: true })) {
    if (["node_modules", "dist", "build", ".next", ".turbo", "coverage"].includes(child.name)) continue;
    files.push(...walk(path.join(absolute, child.name)));
  }
  return files;
};

const isAllowedDocPath = (file) => {
  const parts = path.normalize(file).split(path.sep).map((part) => part.toLowerCase());
  return parts.some((part) => allowedDocSegments.has(part));
};

let scanned = 0;
for (const target of targets) {
  for (const file of walk(target)) {
    const extension = path.extname(file).toLowerCase();
    if (!codeExtensions.has(extension)) continue;
    if (isAllowedDocPath(file)) continue;

    scanned += 1;
    const lines = read(file).split(/\r?\n/);
    for (let index = 0; index < lines.length; index += 1) {
      for (const pattern of forbiddenPatterns) {
        if (pattern.regex.test(lines[index])) fail(`${pattern.name} in ${file}:${index + 1}`);
      }
    }
  }
}

if (scanned === 0) fail("no runtime source/CSS files were scanned");
else ok(`profile ${profileId}: scanned ${scanned} runtime source/CSS files`);

if (!process.exitCode) ok("no source-library runtime CSS leakage found");
