import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skillPath = path.join(root, "SKILL.md");
const referencesDir = path.join(root, "references");

const fail = (message) => {
  console.error(`FAIL: ${message}`);
  process.exitCode = 1;
};

const ok = (message) => {
  console.log(`OK: ${message}`);
};

const read = (file) => fs.readFileSync(file, "utf8");
const skill = read(skillPath);
const lines = skill.split(/\r?\n/);

const frontmatterMatch = skill.match(/^---\r?\n([\s\S]*?)\r?\n---/);
if (!frontmatterMatch) {
  fail("SKILL.md is missing YAML frontmatter");
} else {
  const frontmatter = frontmatterMatch[1];
  const name = frontmatter.match(/^name:\s*(.+)$/m)?.[1]?.trim();
  const description = frontmatter.match(/^description:\s*(.+)$/m)?.[1]?.trim();

  if (!name) fail("frontmatter is missing name");
  else if (!/^[a-z0-9-]{1,64}$/.test(name)) fail("name must be lowercase letters, numbers, and hyphens only, max 64 chars");
  else ok("name is valid");

  if (!description) fail("frontmatter is missing description");
  else {
    if (description.length > 1024) fail(`description is ${description.length} chars, expected <= 1024`);
    else ok(`description length is ${description.length}`);
    if (/^(use this skill|i can|you can)/i.test(description)) {
      fail("description should be third-person, not second-person instruction");
    } else {
      ok("description uses third-person style");
    }
  }
}

if (lines.length > 500) fail(`SKILL.md has ${lines.length} lines, expected <= 500`);
else ok(`SKILL.md has ${lines.length} lines`);

const markdownFiles = [skillPath];
if (fs.existsSync(referencesDir)) {
  for (const entry of fs.readdirSync(referencesDir, { withFileTypes: true })) {
    if (entry.isFile() && entry.name.endsWith(".md")) {
      markdownFiles.push(path.join(referencesDir, entry.name));
    }
  }
}

for (const file of markdownFiles) {
  const text = read(file);
  const display = path.relative(root, file).replaceAll(path.sep, "/");
  if (/[A-Za-z]:\\/.test(text)) fail(`${display} contains a Windows-style drive path`);
  if (/\\[A-Za-z0-9_.-]+\\/.test(text)) fail(`${display} contains a Windows-style slash path`);
}

const referenceLinks = [...skill.matchAll(/\]\((references\/[^)]+\.md)\)/g)].map((match) => match[1]);
const uniqueLinks = [...new Set(referenceLinks)];
if (uniqueLinks.length === 0) {
  fail("SKILL.md does not link any references");
} else {
  for (const link of uniqueLinks) {
    const target = path.join(root, ...link.split("/"));
    if (!fs.existsSync(target)) fail(`missing reference: ${link}`);
    else ok(`reference exists: ${link}`);
  }
}

for (const file of markdownFiles.filter((file) => file !== skillPath)) {
  const text = read(file);
  const display = path.relative(root, file).replaceAll(path.sep, "/");
  if (/\]\((references\/|.*\/references\/)/.test(text)) {
    fail(`${display} links to another reference; keep references one level deep from SKILL.md`);
  }
}

if (!process.exitCode) ok("skill structure check passed");
