import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skillPath = path.join(root, "SKILL.md");
const referencesDir = path.join(root, "references");
const agentsDir = path.join(root, "agents");
const installScriptPath = path.join(root, "scripts", "install-custom-agents.mjs");

const requiredCustomAgents = [
  { file: "antd-source-auditor.toml", name: "antd_source_auditor", sandbox: "read-only" },
  { file: "antd-style-graph-auditor.toml", name: "antd_style_graph_auditor", sandbox: "read-only" },
  { file: "antd-demo-parity-auditor.toml", name: "antd_demo_parity_auditor", sandbox: "read-only" },
  { file: "antd-browser-geometry-verifier.toml", name: "antd_browser_geometry_verifier", sandbox: "workspace-write" },
  { file: "antd-contract-closure-verifier.toml", name: "antd_contract_closure_verifier", sandbox: "read-only" },
  { file: "antd-learning-promoter.toml", name: "antd_learning_promoter", sandbox: "read-only" },
];

const fail = (message) => {
  console.error(`FAIL: ${message}`);
  process.exitCode = 1;
};

const ok = (message) => {
  console.log(`OK: ${message}`);
};

const read = (file) => fs.readFileSync(file, "utf8");
const tomlStringField = (text, field) => text.match(new RegExp(`^${field}\\s*=\\s*"([^"]+)"`, "m"))?.[1];
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

if (!fs.existsSync(agentsDir)) {
  fail("agents directory is missing");
} else {
  ok("agents directory exists");

  for (const expected of requiredCustomAgents) {
    const agentPath = path.join(agentsDir, expected.file);
    if (!fs.existsSync(agentPath)) {
      fail(`missing custom agent template: agents/${expected.file}`);
      continue;
    }

    const text = read(agentPath);
    const display = `agents/${expected.file}`;
    const name = tomlStringField(text, "name");
    const description = tomlStringField(text, "description");
    const model = tomlStringField(text, "model");
    const effort = tomlStringField(text, "model_reasoning_effort");
    const sandbox = tomlStringField(text, "sandbox_mode");

    if (name !== expected.name) fail(`${display} name is ${name || "<missing>"}, expected ${expected.name}`);
    else ok(`${display} name is valid`);

    if (!description) fail(`${display} is missing description`);
    else ok(`${display} description exists`);

    if (!/^developer_instructions\s*=\s*"""[\s\S]+?"""/m.test(text)) fail(`${display} is missing developer_instructions`);
    else ok(`${display} developer_instructions exists`);

    if (model !== "gpt-5.5") fail(`${display} model is ${model || "<missing>"}, expected gpt-5.5`);
    else ok(`${display} model is gpt-5.5`);

    if (effort !== "high") fail(`${display} model_reasoning_effort is ${effort || "<missing>"}, expected high`);
    else ok(`${display} reasoning effort is high`);

    if (sandbox !== expected.sandbox) fail(`${display} sandbox_mode is ${sandbox || "<missing>"}, expected ${expected.sandbox}`);
    else ok(`${display} sandbox_mode is ${expected.sandbox}`);
  }
}

if (!fs.existsSync(installScriptPath)) fail("scripts/install-custom-agents.mjs is missing");
else ok("install custom agents script exists");

if (!process.exitCode) ok("skill structure check passed");
