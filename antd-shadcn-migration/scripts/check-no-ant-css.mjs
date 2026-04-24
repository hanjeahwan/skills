import fs from "node:fs";
import path from "node:path";

const targets = process.argv.slice(2);
if (targets.length === 0) {
  console.error("Usage: node scripts/check-no-ant-css.mjs <target-path...>");
  process.exit(2);
}

const allowedDocSegments = new Set(["docs", "contracts", "migrations", "learnings", "references"]);
const codeExtensions = new Set([".css", ".scss", ".sass", ".less", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]);
const forbiddenPatterns = [
  { name: "Ant class selector/string", regex: /\bant-[a-z0-9-]+/i },
  { name: "Ant CSS variable", regex: /--ant-[a-z0-9-]+/i },
  { name: "Ant generated CSS import", regex: /from\s+["']antd\/dist|import\s+["']antd\/dist|from\s+["']antd\/es\/.*\/style|import\s+["']antd\/es\/.*\/style/i },
  { name: "Ant prefix selector", regex: /\[class\*=["']ant-|\.ant-/i },
];

const fail = (message) => {
  console.error(`FAIL: ${message}`);
  process.exitCode = 1;
};
const ok = (message) => console.log(`OK: ${message}`);

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
    if (child.name === "node_modules" || child.name === "dist" || child.name === "build" || child.name === ".next") continue;
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
    const text = fs.readFileSync(file, "utf8");
    const lines = text.split(/\r?\n/);
    for (let index = 0; index < lines.length; index += 1) {
      for (const pattern of forbiddenPatterns) {
        if (pattern.regex.test(lines[index])) {
          fail(`${pattern.name} in ${file}:${index + 1}`);
        }
      }
    }
  }
}

if (scanned === 0) fail("no runtime source/CSS files were scanned");
else ok(`scanned ${scanned} runtime source/CSS files`);

if (!process.exitCode) ok("no Ant runtime CSS leakage found");
