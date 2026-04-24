import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skillPath = path.join(root, "SKILL.md");
const referencesDir = path.join(root, "references");
const profilesDir = path.join(root, "profiles");
const agentsDir = path.join(root, "agents");
const evalsPath = path.join(root, "evals", "evals.json");

const requiredCustomAgents = [
  { file: "ui-profile-builder.toml", name: "ui_profile_builder", sandbox: "read-only" },
  { file: "ui-source-auditor.toml", name: "ui_source_auditor", sandbox: "read-only" },
  { file: "ui-style-graph-auditor.toml", name: "ui_style_graph_auditor", sandbox: "read-only" },
  { file: "ui-demo-parity-auditor.toml", name: "ui_demo_parity_auditor", sandbox: "read-only" },
  { file: "ui-browser-geometry-verifier.toml", name: "ui_browser_geometry_verifier", sandbox: "workspace-write" },
  { file: "ui-contract-closure-verifier.toml", name: "ui_contract_closure_verifier", sandbox: "read-only" },
  { file: "ui-learning-promoter.toml", name: "ui_learning_promoter", sandbox: "read-only" },
];

const requiredProfiles = ["antd.md", "profile-template.md"];
const requiredReferences = [
  "source-library-discovery.md",
  "contract-template.md",
  "testing-and-acceptance.md",
  "learnings-and-profile-evolution.md",
  "component-classes.md",
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

if (!fs.existsSync(skillPath)) {
  fail("SKILL.md is missing");
  process.exit(1);
}

const skill = read(skillPath);
const lines = skill.split(/\r?\n/);

const frontmatterMatch = skill.match(/^---\r?\n([\s\S]*?)\r?\n---/);
if (!frontmatterMatch) {
  fail("SKILL.md is missing YAML frontmatter");
} else {
  const frontmatter = frontmatterMatch[1];
  const name = frontmatter.match(/^name:\s*(.+)$/m)?.[1]?.trim();
  const description = frontmatter.match(/^description:\s*(.+)$/m)?.[1]?.trim();

  if (name !== "ui-library-to-shadcn-tailwindcss") fail(`frontmatter name is ${name || "<missing>"}`);
  else ok("frontmatter name is valid");

  if (!description) fail("frontmatter is missing description");
  else {
    if (description.length > 1024) fail(`description is ${description.length} chars, expected <= 1024`);
    else ok(`description length is ${description.length}`);
    if (/^(use this skill|i can|you can)/i.test(description)) fail("description should be third-person, not second-person instruction");
    else ok("description uses third-person style");
    for (const token of ["AntD", "MUI", "Chakra", "Mantine", "Headless UI", "Radix Themes", "shadcn", "Tailwind CSS v4"]) {
      if (!description.includes(token)) fail(`description missing trigger token: ${token}`);
    }
  }
}

if (lines.length > 500) fail(`SKILL.md has ${lines.length} lines, expected <= 500`);
else ok(`SKILL.md has ${lines.length} lines`);

if (!skill.includes("~/.codex/agents")) fail("SKILL.md must document global custom agent installation at ~/.codex/agents");
else ok("SKILL.md documents global custom agent directory");
if (!skill.includes(".codex/agents/")) fail("SKILL.md must document project custom agent installation at .codex/agents/");
else ok("SKILL.md documents project custom agent directory");
if (/install-custom-agents\.mjs/.test(skill)) fail("SKILL.md should not recommend install-custom-agents.mjs");

const markdownFiles = [skillPath];
for (const dir of [referencesDir, profilesDir]) {
  if (!fs.existsSync(dir)) {
    fail(`${path.basename(dir)} directory is missing`);
    continue;
  }
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isFile() && entry.name.endsWith(".md")) markdownFiles.push(path.join(dir, entry.name));
  }
}

for (const file of markdownFiles) {
  const text = read(file);
  const display = path.relative(root, file).replaceAll(path.sep, "/");
  if (/[A-Za-z]:\\/.test(text)) fail(`${display} contains a Windows-style drive path`);
  if (/\\[A-Za-z0-9_. -]+\\/.test(text)) fail(`${display} contains a Windows-style slash path`);
}

const links = [...skill.matchAll(/\]\(((?:references|profiles)\/[^)]+\.md)\)/g)].map((match) => match[1]);
const uniqueLinks = [...new Set(links)];
if (uniqueLinks.length === 0) fail("SKILL.md does not link any references or profiles");
else {
  for (const link of uniqueLinks) {
    const parts = link.split("/");
    if (parts.length !== 2) fail(`deep link is not allowed: ${link}`);
    const target = path.join(root, ...parts);
    if (!fs.existsSync(target)) fail(`missing linked file: ${link}`);
    else ok(`linked file exists: ${link}`);
  }
}

for (const required of requiredReferences) {
  if (!fs.existsSync(path.join(referencesDir, required))) fail(`missing reference: references/${required}`);
  else ok(`reference exists: references/${required}`);
}

for (const required of requiredProfiles) {
  if (!fs.existsSync(path.join(profilesDir, required))) fail(`missing profile: profiles/${required}`);
  else ok(`profile exists: profiles/${required}`);
}

for (const file of markdownFiles.filter((file) => file !== skillPath)) {
  const text = read(file);
  const display = path.relative(root, file).replaceAll(path.sep, "/");
  if (/\]\(((?:references|profiles)\/|.*\/(?:references|profiles)\/)/.test(text)) {
    fail(`${display} links to another reference/profile; keep secondary docs one level deep from SKILL.md`);
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

if (!fs.existsSync(evalsPath)) fail("evals/evals.json is missing");
else {
  try {
    const evals = JSON.parse(read(evalsPath));
    if (evals.skill_name !== "ui-library-to-shadcn-tailwindcss") fail(`evals skill_name is ${evals.skill_name}`);
    else ok("evals skill_name is valid");
  } catch (error) {
    fail(`evals/evals.json is invalid JSON: ${error.message}`);
  }
}

if (!process.exitCode) ok("skill structure check passed");
