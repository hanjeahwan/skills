import { statSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";

const TOKEN_PATTERN = /[a-z0-9][a-z0-9_+.#/-]*/gi;
const STOPWORDS = new Set([
  "a",
  "about",
  "an",
  "are",
  "claim",
  "do",
  "does",
  "for",
  "hanje",
  "hanjeahwan",
  "he",
  "his",
  "how",
  "i",
  "in",
  "is",
  "know",
  "me",
  "my",
  "of",
  "proof",
  "should",
  "show",
  "s",
  "the",
  "to",
  "what",
  "you",
]);

const INTENT_HINTS = {
  coding_style: ["code", "coding", "react", "next", "typescript", "style", "pattern", "component"],
  act_as_me: ["prefer", "preference", "decision", "choose", "act", "behalf", "would", "should", "review", "reviews"],
  work_context: [
    "work",
    "career",
    "job",
    "done",
    "built",
    "shipped",
    "lead",
    "strength",
    "experience",
    "exp",
    "year",
    "years",
    "fullstack",
    "full-stack",
    "full",
    "stack",
    "impact",
    "strong",
    "strengths",
    "improved",
    "improve",
    "growth",
    "trajectory",
  ],
  personal_context: ["personal", "life", "habit", "like", "goal"],
  proof: ["proof", "evidence", "source", "commit", "citation"],
  gap: ["unknown", "gap", "missing", "unsafe", "assume", "uncertain"],
};

const CHINESE_INTENT_HINTS = {
  coding_style: ["代码", "编程", "风格", "规范", "组件", "前端"],
  act_as_me: ["偏好", "决定", "选择", "代表", "替我", "review", "评审"],
  work_context: ["工作", "能力", "做过", "实力", "领导", "几年", "经验", "多久", "全栈", "强项", "擅长", "影响力"],
  personal_context: ["个人", "生活", "习惯", "目标"],
  proof: ["证明", "证据", "来源"],
  gap: ["不知道", "缺少", "不确定", "不能假设"],
};

const BOOTSTRAP_HINTS = ["before acting", "act as", "work like", "represent"];
const CHINESE_BOOTSTRAP_HINTS = ["替我做", "代表我", "开始前要知道"];
const GENERIC_CODING_TERMS = new Set(["code", "coding", "style", "pattern", "patterns"]);
const ARCHITECTURE_HINTS = new Set(["prefer", "preference", "architecture", "decision", "frontend"]);
const CHINESE_ARCHITECTURE_HINTS = ["架构", "方案"];
const EXPERIENCE_HINTS = new Set(["experience", "exp", "year", "years", "career", "worked", "fullstack", "full-stack", "full", "stack"]);
const ROLE_HINTS = new Set(["kind", "type", "engineer", "role", "identity", "lead"]);
const STACK_HINTS = new Set(["stack", "technology", "technologies", "tech", "react", "angular", "typescript", "next"]);
const IMPACT_HINTS = new Set(["impact", "strong", "strength", "strengths", "improved", "improve"]);
const STRENGTH_HINTS = new Set(["strong", "strength", "strengths"]);
const REVIEW_HINTS = new Set(["review", "reviews", "pr", "prs"]);
const LEARNING_HINTS = new Set(["improved", "improve", "growth", "trajectory", "learned", "changed"]);
const DOMAIN_HINTS = new Set(["domain", "product", "business", "recruiting", "candidate", "employee", "analytics"]);
const CHINESE_EXPERIENCE_HINTS = ["几年", "经验", "工作多久", "多久", "全栈"];
const CHINESE_ROLE_HINTS = ["什么类型", "什么工程师", "角色", "定位"];
const CHINESE_STACK_HINTS = ["技术栈", "会什么技术", "react", "angular", "typescript"];
const CHINESE_IMPACT_HINTS = ["强项", "擅长", "影响力", "贡献"];
const CHINESE_STRENGTH_HINTS = ["强项", "擅长"];
const CHINESE_REVIEW_HINTS = ["review", "评审", "PR", "代码审查"];
const CHINESE_LEARNING_HINTS = ["成长", "进步", "这些年", "变化"];
const CHINESE_DOMAIN_HINTS = ["业务领域", "产品领域", "领域", "懂哪些业务"];
const OFFICIAL_PROFILE_HINTS = new Set(["official", "formal", "title", "role", "promotion", "declared", "tenure"]);
const AUTHORITY_HINTS = new Set(["authority", "relies", "rely", "depends", "dependency", "codeowners", "owner", "permission", "reviewer", "mentions"]);
const RELEASE_HINTS = new Set(["release", "hotfix", "deploy", "deployment", "ci", "cd", "cicd", "workflow", "github", "actions", "pipeline"]);
const JIRA_LEADERSHIP_HINTS = new Set(["jira", "qa", "blocked", "blocker", "reopen", "done", "ticket", "transition"]);
const ARCHITECTURE_MATERIAL_HINTS = new Set(["doc", "docs", "document", "documentation", "rfc", "confluence", "standard", "standards", "migration"]);
const AGENT_COLLAB_HINTS = new Set(["agent", "codex", "claude", "cursor", "collaborate", "collaboration", "session", "sessions"]);
const PORTFOLIO_HINTS = new Set(["portfolio", "case", "cases", "case-study", "showcase", "screenshot", "screenshots", "public"]);
const PERSONAL_HINTS = new Set(["personal", "value", "values", "life", "preference", "preferences", "goal", "goals", "boundary", "boundaries"]);
const CHINESE_OFFICIAL_PROFILE_HINTS = ["正式", "职位", "头衔", "年限", "晋升"];
const CHINESE_AUTHORITY_HINTS = ["依赖", "前端决定", "权限", "负责人", "默认 reviewer", "谁依赖"];
const CHINESE_RELEASE_HINTS = ["release", "发布", "部署", "hotfix", "CI", "CD", "CI/CD", "流水线"];
const CHINESE_JIRA_LEADERSHIP_HINTS = ["jira", "qa", "阻塞", "blocked", "done", "协调"];
const CHINESE_ARCHITECTURE_MATERIAL_HINTS = ["架构文档", "文档", "rfc", "标准", "迁移计划"];
const CHINESE_AGENT_COLLAB_HINTS = ["agent", "代理", "协作", "一起工作", "会话"];
const CHINESE_PORTFOLIO_HINTS = ["作品", "案例", "作品案例", "展示", "截图"];
const CHINESE_PERSONAL_HINTS = ["个人", "偏好", "价值观", "目标", "边界", "生活"];

const cacheByLedger = new Map();

function derivedPath(ledgerPath, name) {
  return path.join(ledgerPath, "derived", name);
}

function contextPacksPath(ledgerPath) {
  return derivedPath(ledgerPath, "context_packs.jsonl");
}

function tokenize(text) {
  return [...String(text || "").matchAll(TOKEN_PATTERN)].map((match) => match[0].toLowerCase());
}

function inferIntent(query) {
  const terms = new Set(tokenize(query));
  const lowered = String(query || "").toLowerCase();
  if (
    INTENT_HINTS.proof.some((hint) => terms.has(hint) || lowered.includes(hint)) ||
    CHINESE_INTENT_HINTS.proof.some((hint) => String(query || "").includes(hint))
  ) {
    return "proof";
  }
  if (
    BOOTSTRAP_HINTS.some((hint) => lowered.includes(hint)) ||
    CHINESE_BOOTSTRAP_HINTS.some((hint) => String(query || "").includes(hint))
  ) {
    return "act_as_me";
  }
  if (
    hasAnyHint(query, [...terms], RELEASE_HINTS, CHINESE_RELEASE_HINTS) ||
    hasAnyHint(query, [...terms], JIRA_LEADERSHIP_HINTS, CHINESE_JIRA_LEADERSHIP_HINTS) ||
    hasAnyHint(query, [...terms], ARCHITECTURE_MATERIAL_HINTS, CHINESE_ARCHITECTURE_MATERIAL_HINTS)
  ) {
    return "work_context";
  }
  if (hasAnyHint(query, [...terms], OFFICIAL_PROFILE_HINTS, CHINESE_OFFICIAL_PROFILE_HINTS)) return "work_context";
  if (hasAnyHint(query, [...terms], AUTHORITY_HINTS, CHINESE_AUTHORITY_HINTS)) return "relationship_context";
  if (hasAnyHint(query, [...terms], AGENT_COLLAB_HINTS, CHINESE_AGENT_COLLAB_HINTS)) return "act_as_me";
  if (hasAnyHint(query, [...terms], PORTFOLIO_HINTS, CHINESE_PORTFOLIO_HINTS)) return "project_context";
  if (hasAnyHint(query, [...terms], PERSONAL_HINTS, CHINESE_PERSONAL_HINTS)) return "personal_context";
  for (const [intent, hints] of Object.entries(INTENT_HINTS)) {
    if (hints.some((hint) => terms.has(hint) || lowered.includes(hint))) return intent;
  }
  for (const [intent, hints] of Object.entries(CHINESE_INTENT_HINTS)) {
    if (hints.some((hint) => String(query || "").includes(hint))) return intent;
  }
  return "self_knowledge";
}

function isBootstrapQuery(query, intent, terms) {
  if (intent !== "act_as_me") return false;
  const lowered = String(query || "").toLowerCase();
  if (
    BOOTSTRAP_HINTS.some((hint) => lowered.includes(hint)) ||
    CHINESE_BOOTSTRAP_HINTS.some((hint) => String(query || "").includes(hint))
  ) {
    return true;
  }
  return terms.includes("act") || terms.includes("represent");
}

function hasAnyHint(query, terms, englishHints, chineseHints) {
  const termSet = new Set(terms);
  const lowered = String(query || "").toLowerCase();
  for (const hint of englishHints) {
    if (termSet.has(hint) || (String(hint).length > 2 && lowered.includes(hint))) return true;
  }
  return chineseHints.some((hint) => String(query || "").includes(hint));
}

function searchTerms(query) {
  return tokenize(query).filter((term) => !STOPWORDS.has(term));
}

function parseJsonl(text, filePath) {
  const rows = [];
  const lines = text.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line) continue;
    try {
      rows.push(JSON.parse(line));
    } catch (error) {
      throw new Error(`${filePath}:${index + 1}: invalid JSONL: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  return rows;
}

function asText(value) {
  if (Array.isArray(value)) return value.map(asText).join("\n");
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value || "");
}

function scoreText(text, terms) {
  const lowered = String(text || "").toLowerCase();
  let score = 0;
  for (const term of terms) {
    const count = lowered.split(term).length - 1;
    if (count > 0) score += 1 + Math.log2(count);
  }
  return score;
}

function rowViews(row) {
  return {
    title: asText(row.title),
    topics: asText(row.topics),
    directAnswer: asText(row.direct_answer),
    usefulContext: asText(row.useful_context),
    behavioralGuidance: asText(row.behavioral_guidance),
    knownLimits: asText(row.known_limits),
    retrievalText: asText(row.retrieval_text),
  };
}

function scorePack(row, terms, intent) {
  const weights = {
    title: 6,
    topics: 5,
    directAnswer: 4,
    usefulContext: 2.5,
    behavioralGuidance: 2,
    knownLimits: 1.5,
    retrievalText: 1,
  };
  let score = 0;
  const matched = new Set();
  for (const [field, text] of Object.entries(rowViews(row))) {
    const fieldScore = scoreText(text, terms) * weights[field];
    if (fieldScore > 0) {
      score += fieldScore;
      const lowered = text.toLowerCase();
      for (const term of terms) {
        if (lowered.includes(term)) matched.add(term);
      }
    }
  }
  if (row.intent === intent) score *= 1.35;
  if (intent === "proof") score *= 0.9;
  return { score, matched: [...matched].sort() };
}

function sanitizePack(row, includeProvenance) {
  const output = {
    id: row.id,
    intent: row.intent,
    title: row.title,
    direct_answer: row.direct_answer,
    useful_context: row.useful_context || [],
    behavioral_guidance: row.behavioral_guidance || [],
    known_limits: row.known_limits || [],
    topics: row.topics || [],
    confidence: Array.isArray(row.memory_atoms) && row.memory_atoms.length ? "strong" : "medium",
    _score: row._score,
    _matched_terms: row._matched_terms || [],
  };
  if (includeProvenance) {
    output.memory_atoms = row.memory_atoms || [];
    output.private_trace_refs = row.private_trace_refs || [];
  } else {
    output.private_trace_available = Boolean(row.private_trace_refs?.length);
  }
  return output;
}

function touchCache(cache, now = Date.now()) {
  cache.lastAccessedAtMs = now;
  cache.lastAccessedAt = new Date(now).toISOString();
  return cache;
}

async function loadSelfContextCache(ledgerPath, forceReload = false) {
  const resolvedLedger = path.resolve(ledgerPath);
  const packsPath = contextPacksPath(resolvedLedger);
  const stat = statSync(packsPath);
  const existing = cacheByLedger.get(resolvedLedger);
  if (
    !forceReload &&
    existing &&
    existing.packsPath === packsPath &&
    existing.packsSize === stat.size &&
    existing.packsMtimeMs === stat.mtimeMs
  ) {
    return { cache: touchCache(existing), loaded: false };
  }

  const started = performance.now();
  const loadedAtMs = Date.now();
  const packs = parseJsonl(await readFile(packsPath, "utf8"), packsPath);
  let provenance = [];
  try {
    provenance = parseJsonl(await readFile(derivedPath(resolvedLedger, "provenance_links.jsonl"), "utf8"), "provenance_links.jsonl");
  } catch {
    provenance = [];
  }
  const cache = {
    ledgerPath: resolvedLedger,
    packsPath,
    packsSize: stat.size,
    packsMtimeMs: stat.mtimeMs,
    packCount: packs.length,
    packs,
    provenance,
    loadedAtMs,
    loadedAt: new Date(loadedAtMs).toISOString(),
    lastAccessedAtMs: loadedAtMs,
    lastAccessedAt: new Date(loadedAtMs).toISOString(),
    loadMs: Math.round(performance.now() - started),
  };
  cacheByLedger.set(resolvedLedger, cache);
  return { cache, loaded: true };
}

function provenanceFor(rows, provenanceRows) {
  const memoryIds = new Set(rows.flatMap((row) => row.memory_atoms || []));
  const seen = new Set();
  const output = [];
  for (const item of provenanceRows) {
    if (!memoryIds.has(item.memory_id)) continue;
    const key = `${item.memory_id}|${item.source_id}`;
    if (seen.has(key)) continue;
    seen.add(key);
    output.push({
      memory_id: item.memory_id,
      source_id: item.source_id,
      source_type: item.source_type,
      support_role: item.support_role,
      strength: item.strength,
      reason: item.reason,
    });
    if (output.length >= 80) break;
  }
  return output;
}

export function invalidateSelfContextCache(ledgerPath) {
  cacheByLedger.delete(path.resolve(ledgerPath));
}

export function getSelfContextCacheStatus(ledgerPath) {
  const cache = cacheByLedger.get(path.resolve(ledgerPath));
  if (!cache) return { loaded: false };
  const now = Date.now();
  return {
    loaded: true,
    packsPath: cache.packsPath,
    packCount: cache.packCount,
    size: cache.packsSize,
    mtimeMs: cache.packsMtimeMs,
    loadedAt: cache.loadedAt,
    lastAccessedAt: cache.lastAccessedAt,
    idleMs: Math.max(0, now - cache.lastAccessedAtMs),
    loadMs: cache.loadMs,
  };
}

export async function warmSelfContextCache(ledgerPath, options = {}) {
  const { cache, loaded } = await loadSelfContextCache(ledgerPath, Boolean(options.forceReload));
  return { loaded, ...getSelfContextCacheStatus(cache.ledgerPath) };
}

export function evictExpiredSelfContextCaches(options = {}) {
  const ttlMs = Number(options.ttlMs ?? 0);
  if (!Number.isFinite(ttlMs) || ttlMs <= 0) return { evicted: 0, retained: cacheByLedger.size };
  const now = options.now ?? Date.now();
  const evictedLedgers = [];
  for (const [ledgerPath, cache] of cacheByLedger.entries()) {
    if (now - cache.lastAccessedAtMs > ttlMs) {
      cacheByLedger.delete(ledgerPath);
      evictedLedgers.push(ledgerPath);
    }
  }
  return { evicted: evictedLedgers.length, retained: cacheByLedger.size, evictedLedgers };
}

export async function querySelfContextFast(input) {
  const started = performance.now();
  const { cache, loaded } = await loadSelfContextCache(input.ledgerPath);
  const intent = input.intent || inferIntent(input.query);
  const includeProvenance = Boolean(input.includeProvenance || intent === "proof");
  const terms = searchTerms(input.query);
  const bootstrapQuery = isBootstrapQuery(input.query, intent, terms);
  const architectureFocused =
    terms.some((term) => ARCHITECTURE_HINTS.has(term)) ||
    CHINESE_ARCHITECTURE_HINTS.some((hint) => String(input.query || "").includes(hint));
  const specialRoutingHint =
    architectureFocused ||
    intent === "coding_style" ||
    hasAnyHint(input.query, terms, OFFICIAL_PROFILE_HINTS, CHINESE_OFFICIAL_PROFILE_HINTS) ||
    hasAnyHint(input.query, terms, AUTHORITY_HINTS, CHINESE_AUTHORITY_HINTS) ||
    hasAnyHint(input.query, terms, RELEASE_HINTS, CHINESE_RELEASE_HINTS) ||
    hasAnyHint(input.query, terms, JIRA_LEADERSHIP_HINTS, CHINESE_JIRA_LEADERSHIP_HINTS) ||
    hasAnyHint(input.query, terms, ARCHITECTURE_MATERIAL_HINTS, CHINESE_ARCHITECTURE_MATERIAL_HINTS) ||
    hasAnyHint(input.query, terms, AGENT_COLLAB_HINTS, CHINESE_AGENT_COLLAB_HINTS) ||
    hasAnyHint(input.query, terms, PORTFOLIO_HINTS, CHINESE_PORTFOLIO_HINTS) ||
    hasAnyHint(input.query, terms, PERSONAL_HINTS, CHINESE_PERSONAL_HINTS) ||
    hasAnyHint(input.query, terms, EXPERIENCE_HINTS, CHINESE_EXPERIENCE_HINTS) ||
    hasAnyHint(input.query, terms, REVIEW_HINTS, CHINESE_REVIEW_HINTS) ||
    hasAnyHint(input.query, terms, ROLE_HINTS, CHINESE_ROLE_HINTS) ||
    hasAnyHint(input.query, terms, STACK_HINTS, CHINESE_STACK_HINTS) ||
    hasAnyHint(input.query, terms, LEARNING_HINTS, CHINESE_LEARNING_HINTS) ||
    hasAnyHint(input.query, terms, STRENGTH_HINTS, CHINESE_STRENGTH_HINTS) ||
    hasAnyHint(input.query, terms, IMPACT_HINTS, CHINESE_IMPACT_HINTS) ||
    hasAnyHint(input.query, terms, DOMAIN_HINTS, CHINESE_DOMAIN_HINTS);
  const minScore = input.minScore ?? 1;
  const results = [];
  if (!terms.length && !specialRoutingHint) {
    const broadOrder = new Map([
      ["context:self_model.master_persona", 110],
      ["context:self_model.agent_operating_context", 104],
      ["context:self_model.declared_profile", 103],
      ["context:self_model.career_timeline", 103],
      ["context:self_model.experience_scope", 102],
      ["context:self_model.role_identity", 101],
      ["context:self_model.technical_stack", 100],
      ["context:self_model.coding_style", 102],
      ["context:self_model.architecture_judgment", 98],
      ["context:self_model.quality_bar", 94],
      ["context:self_model.delivery_leadership", 90],
      ["context:self_model.ai_product_judgment", 86],
      ["context:self_model.domain_knowledge", 82],
      ["context:self_model.impact_profile", 80],
      ["context:self_model.review_style", 79],
      ["context:self_model.review_authority", 78],
      ["context:self_model.repo_authority", 77],
      ["context:self_model.release_ownership", 76],
      ["context:self_model.jira_leadership", 75],
      ["context:self_model.architecture_material", 74],
      ["context:self_model.agent_collaboration_style", 73],
      ["context:self_model.portfolio_cases", 72],
      ["context:self_model.personal_identity", 71],
      ["context:self_model.learning_trajectory", 76],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== intent && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: [] });
    }
  } else if (hasAnyHint(input.query, terms, ARCHITECTURE_MATERIAL_HINTS, CHINESE_ARCHITECTURE_MATERIAL_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.architecture_material", 118],
      ["context:self_model.architecture_judgment", 104],
      ["context:self_model.learning_trajectory", 94],
      ["context:self_model.boundaries_unknowns", 90],
    ]);
    for (const pack of cache.packs) {
      if (!String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, OFFICIAL_PROFILE_HINTS, CHINESE_OFFICIAL_PROFILE_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.declared_profile", 118],
      ["context:self_model.career_timeline", 108],
      ["context:self_model.experience_scope", 100],
      ["context:self_model.role_identity", 94],
      ["context:self_model.boundaries_unknowns", 88],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "work_context" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, RELEASE_HINTS, CHINESE_RELEASE_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.release_ownership", 118],
      ["context:self_model.delivery_leadership", 106],
      ["context:self_model.impact_profile", 98],
      ["context:self_model.quality_bar", 90],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "work_context" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, AUTHORITY_HINTS, CHINESE_AUTHORITY_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.repo_authority", 118],
      ["context:self_model.review_authority", 108],
      ["context:self_model.role_identity", 100],
      ["context:self_model.delivery_leadership", 92],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "relationship_context" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, JIRA_LEADERSHIP_HINTS, CHINESE_JIRA_LEADERSHIP_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.jira_leadership", 118],
      ["context:self_model.delivery_leadership", 106],
      ["context:self_model.quality_bar", 98],
      ["context:self_model.impact_profile", 90],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "work_context" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, AGENT_COLLAB_HINTS, CHINESE_AGENT_COLLAB_HINTS) && !bootstrapQuery) {
    const broadOrder = new Map([
      ["context:self_model.agent_collaboration_style", 118],
      ["context:self_model.agent_operating_context", 110],
      ["context:self_model.quality_bar", 98],
      ["context:self_model.architecture_judgment", 92],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "act_as_me" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, PORTFOLIO_HINTS, CHINESE_PORTFOLIO_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.portfolio_cases", 118],
      ["context:self_model.impact_profile", 96],
      ["context:self_model.domain_knowledge", 90],
      ["context:self_model.boundaries_unknowns", 86],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "project_context" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, PERSONAL_HINTS, CHINESE_PERSONAL_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.personal_identity", 118],
      ["context:self_model.agent_operating_context", 96],
      ["context:self_model.boundaries_unknowns", 92],
      ["context:self_model.master_persona", 82],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "personal_context" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, EXPERIENCE_HINTS, CHINESE_EXPERIENCE_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.career_timeline", 118],
      ["context:self_model.experience_scope", 114],
      ["context:self_model.role_identity", 104],
      ["context:self_model.technical_stack", 98],
      ["context:experience_scope.frontend_heavy_full_product_scope", 94],
      ["context:career_timeline.evidence_backed_engineering_years", 92],
      ["context:self_model.boundaries_unknowns", 86],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "work_context" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, REVIEW_HINTS, CHINESE_REVIEW_HINTS) && intent !== "proof") {
    const broadOrder = new Map([
      ["context:self_model.review_style", 120],
      ["context:self_model.review_authority", 118],
      ["context:self_model.quality_bar", 108],
      ["context:self_model.architecture_judgment", 102],
      ["context:self_model.role_identity", 96],
      ["context:review_authority.pr_quality_gate_authority", 94],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "act_as_me" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, ROLE_HINTS, CHINESE_ROLE_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.role_identity", 118],
      ["context:self_model.experience_scope", 108],
      ["context:self_model.review_authority", 102],
      ["context:self_model.delivery_leadership", 96],
      ["context:self_model.master_persona", 90],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "self_knowledge" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, STACK_HINTS, CHINESE_STACK_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.technical_stack", 118],
      ["context:technical_stack.frontend_api_infra_ai_stack", 110],
      ["context:self_model.coding_style", 102],
      ["context:self_model.experience_scope", 96],
      ["context:topic.react", 90],
      ["context:topic.typescript", 86],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "self_knowledge" && pack.intent !== "coding_style" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, LEARNING_HINTS, CHINESE_LEARNING_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.learning_trajectory", 118],
      ["context:self_model.career_timeline", 104],
      ["context:self_model.technical_stack", 98],
      ["context:self_model.ai_product_judgment", 92],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "self_knowledge" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, STRENGTH_HINTS, CHINESE_STRENGTH_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.experience_scope", 118],
      ["context:self_model.technical_stack", 108],
      ["context:self_model.role_identity", 102],
      ["context:self_model.ai_product_judgment", 96],
      ["context:self_model.domain_knowledge", 90],
      ["context:self_model.impact_profile", 84],
    ]);
    for (const pack of cache.packs) {
      if (!String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, IMPACT_HINTS, CHINESE_IMPACT_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.impact_profile", 118],
      ["context:self_model.delivery_leadership", 108],
      ["context:self_model.quality_bar", 102],
      ["context:self_model.experience_scope", 96],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "work_context" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (hasAnyHint(input.query, terms, DOMAIN_HINTS, CHINESE_DOMAIN_HINTS)) {
    const broadOrder = new Map([
      ["context:self_model.domain_knowledge", 118],
      ["context:self_model.experience_scope", 100],
      ["context:topic.recruiting", 92],
      ["context:topic.employee", 88],
      ["context:topic.analytics", 84],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "self_knowledge" && !String(pack.id || "").startsWith("context:self_model.") && !String(pack.id || "").startsWith("context:topic.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (intent === "coding_style" && (!terms.length || terms.every((term) => GENERIC_CODING_TERMS.has(term)))) {
    const broadOrder = new Map([
      ["context:self_model.coding_style", 110],
      ["context:topic.react", 102],
      ["context:coding_style.stateful_product_workflows", 98],
      ["context:coding_style.typed_api_contracts", 94],
      ["context:topic.typescript", 90],
      ["context:self_model.architecture_judgment", 82],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "coding_style" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (bootstrapQuery) {
    const broadOrder = new Map([
      ["context:self_model.agent_operating_context", 118],
      ["context:self_model.architecture_judgment", 110],
      ["context:self_model.quality_bar", 106],
      ["context:self_model.delivery_leadership", 102],
      ["context:self_model.boundaries_unknowns", 98],
      ["context:self_model.master_persona", 94],
      ["context:self_model.coding_style", 86],
      ["context:self_model.ai_product_judgment", 82],
      ["context:self_model.domain_knowledge", 78],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "act_as_me" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else if (intent === "act_as_me" && architectureFocused) {
    const broadOrder = new Map([
      ["context:self_model.architecture_judgment", 114],
      ["context:self_model.quality_bar", 108],
      ["context:preference.high_bar_correctness", 102],
      ["context:decision_pattern.maintainability_standards", 98],
      ["context:decision_pattern.migration_upgrade_execution", 94],
      ["context:decision_pattern.product_edge_case_sensitivity", 90],
      ["context:decision_pattern.pr_quality_gate", 88],
      ["context:self_model.coding_style", 82],
      ["context:topic.architecture", 78],
    ]);
    for (const pack of cache.packs) {
      if (pack.intent !== "act_as_me" && !String(pack.id || "").startsWith("context:self_model.")) continue;
      const score = (broadOrder.get(pack.id) || 0) + (pack.memory_atoms?.length || 0);
      results.push({ ...pack, _score: score, _matched_terms: terms.slice(0, 25) });
    }
  } else {
    for (const pack of cache.packs) {
      const { score, matched } = scorePack(pack, terms, intent);
      if (score < minScore) continue;
      results.push({
        ...pack,
        _score: Number(score.toFixed(3)),
        _matched_terms: matched.slice(0, 25),
      });
    }
  }
  results.sort((left, right) => right._score - left._score || (right.memory_atoms?.length || 0) - (left.memory_atoms?.length || 0));
  const selected = results.slice(0, input.top ?? 5);
  const answerContexts = selected.map((row) => sanitizePack(row, includeProvenance));
  return {
    query: input.query,
    intent,
    answer_contexts: answerContexts,
    ...(includeProvenance ? { provenance: provenanceFor(selected, cache.provenance) } : {}),
    meta: {
      engine: "fast-js-self-context",
      elapsedMs: Math.round(performance.now() - started),
      cacheLoadedThisCall: loaded,
      cacheLoadMs: loaded ? cache.loadMs : 0,
      cachedPacks: cache.packCount,
      candidateRows: results.length,
      returnedRows: answerContexts.length,
      provenanceIncluded: includeProvenance,
    },
  };
}
