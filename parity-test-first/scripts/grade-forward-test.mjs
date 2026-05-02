#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const [, , workspaceArg, evalsArg] = process.argv;

if (!workspaceArg || !evalsArg) {
  console.error("Usage: node scripts/grade-forward-test.mjs <iteration-workspace> <evals-json>");
  process.exit(2);
}

const workspace = path.resolve(workspaceArg);
const evalsPath = path.resolve(evalsArg);
const evalSet = JSON.parse(fs.readFileSync(evalsPath, "utf8"));

const normalize = (value) => String(value ?? "").toLowerCase();

function includesAny(text, needles = []) {
  if (!needles.length) return true;
  const normalized = normalize(text);
  return needles.some((needle) => normalized.includes(normalize(needle)));
}

function includesAll(text, needles = []) {
  if (!needles.length) return true;
  const normalized = normalize(text);
  return needles.every((needle) => normalized.includes(normalize(needle)));
}

function forbidsAny(text, needles = []) {
  if (!needles.length) return true;
  const normalized = normalize(text);
  return !needles.some((needle) => normalized.includes(normalize(needle)));
}

function findEvalDir(evalItem) {
  const prefix = `eval-${evalItem.id}-`;
  const match = fs
    .readdirSync(workspace, { withFileTypes: true })
    .find((entry) => entry.isDirectory() && entry.name.startsWith(prefix));
  if (!match) {
    throw new Error(`Missing eval directory for ${prefix} under ${workspace}`);
  }
  return path.join(workspace, match.name);
}

function readRun(evalDir, runName) {
  const outputsDir = path.join(evalDir, runName, "outputs");
  const responsePath = path.join(outputsDir, "response.md");
  const summaryPath = path.join(outputsDir, "summary.json");
  const response = fs.existsSync(responsePath) ? fs.readFileSync(responsePath, "utf8") : "";
  const summary = fs.existsSync(summaryPath) ? fs.readFileSync(summaryPath, "utf8") : "";
  return {
    runName,
    outputsDir,
    responsePath,
    summaryPath,
    text: `${response}\n\n${summary}`
  };
}

function gradeAssertion(assertion, text) {
  const checks = [
    {
      label: "requires_any",
      passed: includesAny(text, assertion.requires_any)
    },
    {
      label: "requires_all",
      passed: includesAll(text, assertion.requires_all)
    },
    {
      label: "forbids_any",
      passed: forbidsAny(text, assertion.forbids_any)
    }
  ];
  const failed = checks.filter((check) => !check.passed).map((check) => check.label);
  return {
    id: assertion.id,
    text: assertion.text,
    passed: failed.length === 0,
    evidence: failed.length === 0 ? "Matched configured lexical checks." : `Failed checks: ${failed.join(", ")}.`
  };
}

function gradeRun(evalItem, run) {
  const expectations = evalItem.assertions.map((assertion) => gradeAssertion(assertion, run.text));
  const passed = expectations.filter((item) => item.passed).length;
  return {
    run_id: `${evalItem.id}-${evalItem.name}-${run.runName}`,
    eval_id: evalItem.id,
    eval_name: evalItem.name,
    configuration: run.runName,
    response_path: run.responsePath,
    summary_path: run.summaryPath,
    passed,
    total: expectations.length,
    score_percent: Math.round((passed / expectations.length) * 1000) / 10,
    expectations
  };
}

const runs = [];

for (const evalItem of evalSet.evals) {
  const evalDir = findEvalDir(evalItem);
  for (const runName of ["with_skill", "without_skill"]) {
    const run = readRun(evalDir, runName);
    const grading = gradeRun(evalItem, run);
    const gradingPath = path.join(evalDir, runName, "grading.json");
    fs.writeFileSync(gradingPath, `${JSON.stringify(grading, null, 2)}\n`);
    runs.push(grading);
  }
}

function summarize(configuration) {
  const matching = runs.filter((run) => run.configuration === configuration);
  const passed = matching.reduce((sum, run) => sum + run.passed, 0);
  const total = matching.reduce((sum, run) => sum + run.total, 0);
  return {
    configuration,
    passed,
    total,
    score_percent: Math.round((passed / total) * 1000) / 10,
    evals: matching.map((run) => ({
      eval_id: run.eval_id,
      eval_name: run.eval_name,
      passed: run.passed,
      total: run.total,
      score_percent: run.score_percent
    }))
  };
}

const summary = {
  skill_name: evalSet.skill_name,
  harness_version: evalSet.harness_version,
  passing_threshold: evalSet.passing_threshold,
  workspace,
  evals_path: evalsPath,
  summary: [summarize("with_skill"), summarize("without_skill")]
};

const withSkill = summary.summary.find((item) => item.configuration === "with_skill");
const baseline = summary.summary.find((item) => item.configuration === "without_skill");
const thresholds = evalSet.passing_threshold ?? {};
const minEvalPercent = thresholds.with_skill_min_eval_percent ?? 80;
const minScore = thresholds.with_skill_min_score_percent ?? 90;
const minDelta = thresholds.baseline_delta_min_points ?? 0;
const delta = Math.round((withSkill.score_percent - baseline.score_percent) * 10) / 10;

summary.production_ready = {
  passed:
    withSkill.score_percent >= minScore &&
    withSkill.evals.every((item) => item.score_percent >= minEvalPercent) &&
    delta >= minDelta,
  delta_points: delta,
  criteria: [
    `with_skill score >= ${minScore}%`,
    `every with_skill eval >= ${minEvalPercent}%`,
    `with_skill beats baseline by >= ${minDelta} points`
  ]
};

const reportJsonPath = path.join(workspace, "production-readiness-grading.json");
fs.writeFileSync(reportJsonPath, `${JSON.stringify(summary, null, 2)}\n`);

const lines = [
  `# ${evalSet.skill_name} Production Readiness Grading`,
  "",
  `Workspace: \`${workspace}\``,
  `Eval set: \`${evalsPath}\``,
  "",
  "## Summary",
  "",
  "| Configuration | Passed | Total | Score |",
  "|---|---:|---:|---:|",
  ...summary.summary.map((item) => `| ${item.configuration} | ${item.passed} | ${item.total} | ${item.score_percent}% |`),
  "",
  `Delta: ${summary.production_ready.delta_points} points`,
  `Production-ready: ${summary.production_ready.passed ? "yes" : "no"}`,
  "",
  "## Per Eval",
  "",
  "| Eval | With skill | Baseline |",
  "|---|---:|---:|"
];

for (const evalItem of evalSet.evals) {
  const withRun = withSkill.evals.find((item) => item.eval_id === evalItem.id);
  const baseRun = baseline.evals.find((item) => item.eval_id === evalItem.id);
  lines.push(`| ${evalItem.name} | ${withRun.passed}/${withRun.total} | ${baseRun.passed}/${baseRun.total} |`);
}

lines.push("", "## Failed With-Skill Assertions", "");
const failedWithSkill = runs
  .filter((run) => run.configuration === "with_skill")
  .flatMap((run) =>
    run.expectations
      .filter((expectation) => !expectation.passed)
      .map((expectation) => `- ${run.eval_name} / ${expectation.id}: ${expectation.text} (${expectation.evidence})`)
  );
lines.push(...(failedWithSkill.length ? failedWithSkill : ["- none"]));

const reportMdPath = path.join(workspace, "production-readiness-grading.md");
fs.writeFileSync(reportMdPath, `${lines.join("\n")}\n`);

console.log(JSON.stringify(summary, null, 2));
