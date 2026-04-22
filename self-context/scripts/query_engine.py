#!/usr/bin/env python3
"""Hybrid self-context query engine: FTS + dense retrieval + graph expansion + rerank."""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from build_memory_index import hashed_embeddings
from ledger_paths import resolve_ledger_path
from source_families import QUERY_ENGINE_VERSION


TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_+.#/-]*", re.IGNORECASE)
STOPWORDS = {
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
}

INTENT_HINTS = {
    "proof": ["proof", "evidence", "source", "commit", "citation", "trace"],
    "coding_style": ["code", "coding", "react", "next", "typescript", "style", "pattern", "component"],
    "act_as_me": ["prefer", "preference", "decision", "choose", "act", "behalf", "would", "should", "review", "reviews"],
    "work_context": [
        "work",
        "career",
        "job",
        "done",
        "built",
        "shipped",
        "lead",
        "strength",
        "ownership",
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
    "personal_context": ["personal", "life", "habit", "like", "goal"],
    "gap": ["unknown", "gap", "missing", "unsafe", "assume", "uncertain"],
}

CHINESE_INTENT_HINTS = {
    "proof": ["证明", "证据", "来源"],
    "coding_style": ["代码", "编程", "风格", "规范", "组件", "前端"],
    "act_as_me": ["偏好", "决定", "选择", "代表", "替我", "review", "评审"],
    "work_context": ["工作", "能力", "做过", "实力", "领导", "ownership", "几年", "经验", "多久", "全栈", "强项", "擅长", "影响力"],
    "personal_context": ["个人", "生活", "习惯", "目标"],
    "gap": ["不知道", "缺少", "不确定", "不能假设"],
}

BOOTSTRAP_HINTS = ["before acting", "act as", "work like", "represent"]
CHINESE_BOOTSTRAP_HINTS = ["替我做", "代表我", "开始前要知道"]
ARCHITECTURE_HINTS = {"prefer", "preference", "architecture", "decision", "frontend"}
CHINESE_ARCHITECTURE_HINTS = ["架构", "方案"]
EXPERIENCE_HINTS = {"experience", "exp", "year", "years", "career", "worked", "fullstack", "full-stack", "full", "stack"}
ROLE_HINTS = {"kind", "type", "engineer", "role", "identity", "lead"}
STACK_HINTS = {"stack", "technology", "technologies", "tech", "react", "angular", "typescript", "next"}
IMPACT_HINTS = {"impact", "strong", "strength", "strengths", "improved", "improve"}
STRENGTH_HINTS = {"strong", "strength", "strengths"}
REVIEW_HINTS = {"review", "reviews", "pr", "prs"}
LEARNING_HINTS = {"improved", "improve", "growth", "trajectory", "learned", "changed"}
DOMAIN_HINTS = {"domain", "product", "business", "recruiting", "candidate", "employee", "analytics"}
CHINESE_EXPERIENCE_HINTS = ["几年", "经验", "工作多久", "多久", "全栈"]
CHINESE_ROLE_HINTS = ["什么类型", "什么工程师", "角色", "定位"]
CHINESE_STACK_HINTS = ["技术栈", "会什么技术", "react", "angular", "typescript"]
CHINESE_IMPACT_HINTS = ["强项", "擅长", "影响力", "贡献"]
CHINESE_STRENGTH_HINTS = ["强项", "擅长"]
CHINESE_REVIEW_HINTS = ["review", "评审", "PR", "代码审查"]
CHINESE_LEARNING_HINTS = ["成长", "进步", "这些年", "变化"]
CHINESE_DOMAIN_HINTS = ["业务领域", "产品领域", "领域", "懂哪些业务"]
OFFICIAL_PROFILE_HINTS = {"official", "formal", "title", "role", "promotion", "declared", "tenure"}
AUTHORITY_HINTS = {"authority", "relies", "rely", "depends", "dependency", "codeowners", "owner", "permission", "reviewer", "mentions"}
RELEASE_HINTS = {"release", "hotfix", "deploy", "deployment", "ci", "cd", "cicd", "workflow", "github", "actions", "pipeline"}
JIRA_LEADERSHIP_HINTS = {"jira", "qa", "blocked", "blocker", "reopen", "done", "ticket", "transition"}
ARCHITECTURE_MATERIAL_HINTS = {"doc", "docs", "document", "documentation", "rfc", "confluence", "standard", "standards", "migration"}
AGENT_COLLAB_HINTS = {"agent", "codex", "claude", "cursor", "collaborate", "collaboration", "session", "sessions"}
PORTFOLIO_HINTS = {"portfolio", "case", "cases", "case-study", "case studies", "showcase", "screenshot", "screenshots", "public"}
PERSONAL_HINTS = {"personal", "value", "values", "life", "preference", "preferences", "goal", "goals", "boundary", "boundaries"}
CHINESE_OFFICIAL_PROFILE_HINTS = ["正式", "职位", "头衔", "年限", "晋升"]
CHINESE_AUTHORITY_HINTS = ["依赖", "前端决定", "权限", "负责人", "默认 reviewer", "谁依赖"]
CHINESE_RELEASE_HINTS = ["release", "发布", "部署", "hotfix", "CI", "CD", "CI/CD", "流水线"]
CHINESE_JIRA_LEADERSHIP_HINTS = ["jira", "qa", "阻塞", "blocked", "done", "协调"]
CHINESE_ARCHITECTURE_MATERIAL_HINTS = ["架构文档", "文档", "rfc", "标准", "迁移计划"]
CHINESE_AGENT_COLLAB_HINTS = ["agent", "代理", "协作", "一起工作", "会话"]
CHINESE_PORTFOLIO_HINTS = ["作品", "案例", "作品案例", "展示", "截图"]
CHINESE_PERSONAL_HINTS = ["个人", "偏好", "价值观", "目标", "边界", "生活"]

BROAD_SELF_ORDER = {
    "context:self_model.master_persona": 155,
    "context:self_model.agent_operating_context": 126,
    "context:self_model.declared_profile": 125,
    "context:self_model.career_timeline": 124,
    "context:self_model.experience_scope": 123,
    "context:self_model.role_identity": 121,
    "context:self_model.technical_stack": 119,
    "context:self_model.coding_style": 132,
    "context:self_model.architecture_judgment": 128,
    "context:self_model.quality_bar": 122,
    "context:self_model.delivery_leadership": 118,
    "context:self_model.ai_product_judgment": 112,
    "context:self_model.domain_knowledge": 108,
    "context:self_model.impact_profile": 106,
    "context:self_model.review_style": 105,
    "context:self_model.review_authority": 104,
    "context:self_model.repo_authority": 103,
    "context:self_model.release_ownership": 102,
    "context:self_model.jira_leadership": 101,
    "context:self_model.architecture_material": 100,
    "context:self_model.agent_collaboration_style": 99,
    "context:self_model.portfolio_cases": 98,
    "context:self_model.personal_identity": 97,
    "context:self_model.learning_trajectory": 102,
    "context:self_model.boundaries_unknowns": 88,
}

BROAD_EXPERIENCE_ORDER = {
    "context:self_model.declared_profile": 160,
    "context:self_model.career_timeline": 158,
    "context:self_model.experience_scope": 154,
    "context:self_model.role_identity": 144,
    "context:self_model.technical_stack": 134,
    "context:experience_scope.frontend_heavy_full_product_scope": 132,
    "context:career_timeline.evidence_backed_engineering_years": 130,
    "context:self_model.boundaries_unknowns": 116,
    "context:self_model.master_persona": 108,
}

BROAD_OFFICIAL_PROFILE_ORDER = {
    "context:self_model.declared_profile": 170,
    "context:self_model.career_timeline": 154,
    "context:self_model.experience_scope": 142,
    "context:self_model.role_identity": 136,
    "context:self_model.boundaries_unknowns": 126,
}

BROAD_ROLE_ORDER = {
    "context:self_model.role_identity": 156,
    "context:self_model.experience_scope": 146,
    "context:self_model.review_authority": 138,
    "context:self_model.delivery_leadership": 130,
    "context:self_model.master_persona": 120,
}

BROAD_STACK_ORDER = {
    "context:self_model.technical_stack": 156,
    "context:technical_stack.frontend_api_infra_ai_stack": 148,
    "context:self_model.coding_style": 138,
    "context:self_model.experience_scope": 130,
    "context:topic.react": 122,
    "context:topic.typescript": 118,
}

BROAD_IMPACT_ORDER = {
    "context:self_model.impact_profile": 156,
    "context:self_model.delivery_leadership": 144,
    "context:self_model.quality_bar": 136,
    "context:self_model.experience_scope": 128,
    "context:self_model.master_persona": 112,
}

BROAD_STRENGTH_ORDER = {
    "context:self_model.experience_scope": 158,
    "context:self_model.technical_stack": 146,
    "context:self_model.role_identity": 140,
    "context:self_model.ai_product_judgment": 134,
    "context:self_model.domain_knowledge": 128,
    "context:self_model.impact_profile": 122,
    "context:self_model.master_persona": 112,
}

BROAD_REVIEW_ORDER = {
    "context:self_model.review_style": 162,
    "context:self_model.review_authority": 158,
    "context:self_model.quality_bar": 146,
    "context:self_model.architecture_judgment": 138,
    "context:self_model.role_identity": 132,
    "context:review_authority.pr_quality_gate_authority": 130,
}

BROAD_AUTHORITY_ORDER = {
    "context:self_model.repo_authority": 166,
    "context:self_model.review_authority": 150,
    "context:self_model.role_identity": 138,
    "context:self_model.delivery_leadership": 124,
    "context:self_model.boundaries_unknowns": 112,
}

BROAD_RELEASE_ORDER = {
    "context:self_model.release_ownership": 166,
    "context:self_model.delivery_leadership": 148,
    "context:self_model.impact_profile": 138,
    "context:self_model.quality_bar": 126,
    "context:self_model.experience_scope": 116,
}

BROAD_JIRA_ORDER = {
    "context:self_model.jira_leadership": 166,
    "context:self_model.delivery_leadership": 148,
    "context:self_model.quality_bar": 136,
    "context:self_model.impact_profile": 124,
    "context:self_model.boundaries_unknowns": 112,
}

BROAD_ARCHITECTURE_MATERIAL_ORDER = {
    "context:self_model.architecture_material": 166,
    "context:self_model.architecture_judgment": 144,
    "context:self_model.learning_trajectory": 126,
    "context:self_model.boundaries_unknowns": 120,
}

BROAD_AGENT_COLLAB_ORDER = {
    "context:self_model.agent_collaboration_style": 166,
    "context:self_model.agent_operating_context": 154,
    "context:self_model.quality_bar": 132,
    "context:self_model.architecture_judgment": 126,
}

BROAD_PORTFOLIO_ORDER = {
    "context:self_model.portfolio_cases": 166,
    "context:self_model.impact_profile": 130,
    "context:self_model.domain_knowledge": 122,
    "context:self_model.boundaries_unknowns": 118,
}

BROAD_PERSONAL_ORDER = {
    "context:self_model.personal_identity": 166,
    "context:self_model.agent_operating_context": 136,
    "context:self_model.boundaries_unknowns": 132,
    "context:self_model.master_persona": 110,
}

BROAD_LEARNING_ORDER = {
    "context:self_model.learning_trajectory": 158,
    "context:self_model.career_timeline": 142,
    "context:self_model.technical_stack": 136,
    "context:self_model.ai_product_judgment": 130,
    "context:self_model.master_persona": 112,
}

BROAD_DOMAIN_ORDER = {
    "context:self_model.domain_knowledge": 156,
    "context:self_model.experience_scope": 134,
    "context:topic.recruiting": 126,
    "context:topic.employee": 122,
    "context:topic.analytics": 118,
}

BROAD_CODING_ORDER = {
    "context:self_model.coding_style": 150,
    "context:topic.react": 144,
    "context:coding_style.stateful_product_workflows": 140,
    "context:coding_style.typed_api_contracts": 134,
    "context:coding_style.component_composition": 128,
    "context:coding_style.reactive_async_flows": 126,
    "context:topic.typescript": 115,
    "context:topic.frontend": 100,
    "context:self_model.architecture_judgment": 92,
}

BROAD_BOOTSTRAP_ORDER = {
    "context:self_model.agent_operating_context": 158,
    "context:self_model.architecture_judgment": 144,
    "context:self_model.quality_bar": 138,
    "context:self_model.delivery_leadership": 132,
    "context:self_model.boundaries_unknowns": 126,
    "context:self_model.master_persona": 118,
    "context:self_model.coding_style": 108,
    "context:self_model.ai_product_judgment": 104,
    "context:self_model.domain_knowledge": 100,
}

BROAD_ACT_AS_ME_ORDER = {
    "context:self_model.architecture_judgment": 152,
    "context:self_model.quality_bar": 146,
    "context:preference.high_bar_correctness": 138,
    "context:decision_pattern.maintainability_standards": 134,
    "context:decision_pattern.migration_upgrade_execution": 128,
    "context:decision_pattern.product_edge_case_sensitivity": 124,
    "context:decision_pattern.pr_quality_gate": 122,
    "context:self_model.coding_style": 108,
    "context:topic.architecture": 104,
}


def is_bootstrap_query(query: str, intent: str, terms: set[str]) -> bool:
    if intent != "act_as_me":
        return False
    lowered = query.lower()
    if any(hint in lowered for hint in BOOTSTRAP_HINTS):
        return True
    if any(hint in query for hint in CHINESE_BOOTSTRAP_HINTS):
        return True
    return bool({"act", "represent"} & terms)


def has_any_hint(query: str, terms: set[str], english_hints: set[str], chinese_hints: list[str]) -> bool:
    lowered = query.lower()
    if english_hints & terms:
        return True
    if any(hint in lowered for hint in english_hints if len(hint) > 2):
        return True
    return any(hint in query for hint in chinese_hints)


def is_architecture_query(query: str, terms: set[str]) -> bool:
    return bool(ARCHITECTURE_HINTS & terms) or any(hint in query for hint in CHINESE_ARCHITECTURE_HINTS)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return rows


def parse_json(value: str | bytes | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def expanded_tokens(text: str) -> set[str]:
    output: set[str] = set()
    for token in tokenize(text):
        output.add(token)
        for part in re.split(r"[_./-]+", token):
            if part:
                output.add(part)
    return output


def hint_matches(hint: str, terms: set[str], lowered: str) -> bool:
    normalized = hint.lower()
    if re.fullmatch(r"[a-z0-9_+.#/-]+", normalized) and len(normalized) <= 3:
        return normalized in terms
    return normalized in terms or normalized in lowered


def search_terms(query: str) -> list[str]:
    return [term for term in tokenize(query) if term not in STOPWORDS]


def infer_intent(query: str) -> str:
    terms = set(tokenize(query))
    lowered = query.lower()
    if any(hint_matches(hint, terms, lowered) for hint in INTENT_HINTS["proof"]) or any(hint in query for hint in CHINESE_INTENT_HINTS["proof"]):
        return "proof"
    if any(hint in lowered for hint in BOOTSTRAP_HINTS) or any(hint in query for hint in CHINESE_BOOTSTRAP_HINTS):
        return "act_as_me"
    if has_any_hint(query, terms, RELEASE_HINTS, CHINESE_RELEASE_HINTS) or has_any_hint(query, terms, JIRA_LEADERSHIP_HINTS, CHINESE_JIRA_LEADERSHIP_HINTS):
        return "work_context"
    if has_any_hint(query, terms, OFFICIAL_PROFILE_HINTS, CHINESE_OFFICIAL_PROFILE_HINTS):
        return "work_context"
    if has_any_hint(query, terms, AUTHORITY_HINTS, CHINESE_AUTHORITY_HINTS):
        return "relationship_context"
    if has_any_hint(query, terms, ARCHITECTURE_MATERIAL_HINTS, CHINESE_ARCHITECTURE_MATERIAL_HINTS):
        return "work_context"
    if has_any_hint(query, terms, AGENT_COLLAB_HINTS, CHINESE_AGENT_COLLAB_HINTS):
        return "act_as_me"
    if has_any_hint(query, terms, PORTFOLIO_HINTS, CHINESE_PORTFOLIO_HINTS):
        return "project_context"
    if has_any_hint(query, terms, PERSONAL_HINTS, CHINESE_PERSONAL_HINTS):
        return "personal_context"
    for intent, hints in INTENT_HINTS.items():
        if intent == "proof":
            continue
        if any(hint_matches(hint, terms, lowered) for hint in hints):
            return intent
    for intent, hints in CHINESE_INTENT_HINTS.items():
        if any(hint in query for hint in hints):
            return intent
    return "self_knowledge"


def fts_query(terms: list[str]) -> str:
    safe_terms = []
    for term in terms:
        cleaned = re.sub(r"[^a-z0-9_]+", " ", term.lower()).strip()
        if cleaned:
            safe_terms.extend(part for part in cleaned.split() if part and part not in STOPWORDS)
    return " OR ".join(f'"{term}"' for term in sorted(set(safe_terms)))


def context_pack_from_sql(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "intent": row["intent"],
        "title": row["title"],
        "direct_answer": row["direct_answer"],
        "useful_context": parse_json(row["useful_context_json"], []),
        "behavioral_guidance": parse_json(row["behavioral_guidance_json"], []),
        "known_limits": parse_json(row["known_limits_json"], []),
        "memory_atoms": parse_json(row["memory_atoms_json"], []),
        "private_trace_refs": parse_json(row["private_trace_refs_json"], []),
        "topics": parse_json(row["topics_json"], []),
        "retrieval_text": row["retrieval_text"],
        "updated_at": row["updated_at"],
    }


def load_context_packs(ledger: Path) -> list[dict[str, Any]]:
    db_path = ledger / "derived" / "self_context.sqlite3"
    if db_path.exists():
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            return [context_pack_from_sql(row) for row in connection.execute("SELECT * FROM context_packs")]
    return read_jsonl(ledger / "derived" / "context_packs.jsonl")


def load_edges(ledger: Path) -> list[dict[str, Any]]:
    db_path = ledger / "derived" / "self_context.sqlite3"
    if db_path.exists():
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute("SELECT * FROM memory_graph_edges")]
    return read_jsonl(ledger / "derived" / "memory_graph_edges.jsonl")


def load_provenance(ledger: Path) -> list[dict[str, Any]]:
    db_path = ledger / "derived" / "self_context.sqlite3"
    if db_path.exists():
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute("SELECT * FROM provenance_links")]
    return read_jsonl(ledger / "derived" / "provenance_links.jsonl")


def memory_to_context_ids(packs: list[dict[str, Any]]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = defaultdict(list)
    for pack in packs:
        for memory_id in pack.get("memory_atoms", []):
            mapping[str(memory_id)].append(str(pack.get("id")))
    return {memory_id: sorted(set(ids)) for memory_id, ids in mapping.items()}


def fts_candidates(ledger: Path, terms: list[str], pack_by_id: dict[str, dict[str, Any]], memory_contexts: dict[str, list[str]]) -> dict[str, float]:
    db_path = ledger / "derived" / "self_context.sqlite3"
    query = fts_query(terms)
    if not db_path.exists() or not query:
        return {}
    scores: dict[str, float] = defaultdict(float)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            for rank, row in enumerate(
                connection.execute(
                    "SELECT id, bm25(context_packs_fts) AS score FROM context_packs_fts WHERE context_packs_fts MATCH ? ORDER BY score LIMIT 80",
                    (query,),
                ),
                start=1,
            ):
                if row["id"] in pack_by_id:
                    scores[row["id"]] += 1.0 / (60 + rank)
            for rank, row in enumerate(
                connection.execute(
                    "SELECT id, bm25(memory_atoms_fts) AS score FROM memory_atoms_fts WHERE memory_atoms_fts MATCH ? ORDER BY score LIMIT 80",
                    (query,),
                ),
                start=1,
            ):
                for context_id in memory_contexts.get(row["id"], []):
                    if context_id in pack_by_id:
                        scores[context_id] += 0.9 / (60 + rank)
    except sqlite3.Error:
        return {}
    return dict(scores)


def load_embedding_index(ledger: Path) -> tuple[dict[str, Any], np.ndarray | None, np.ndarray | None, list[dict[str, Any]]]:
    manifest = read_json(ledger / "derived" / "memory_embeddings_manifest.json")
    index_path = Path(str(manifest.get("index_path", ledger / "derived" / "memory_embeddings.npz")))
    if not manifest or not index_path.exists():
        return manifest, None, None, []
    data = np.load(index_path, allow_pickle=False)
    records = json.loads(str(data["records_json"][0]))
    fallback = np.asarray(data["fallback_embeddings"], dtype=np.float32) if "fallback_embeddings" in data.files else None
    return manifest, np.asarray(data["embeddings"], dtype=np.float32), fallback, records


def embed_query(query: str, manifest: dict[str, Any]) -> np.ndarray | None:
    backend = manifest.get("backend")
    model_name = str(manifest.get("model_name", ""))
    if backend == "hashing":
        return hashed_embeddings([query], int(manifest.get("dimension", 384)))[0]
    if backend == "sentence-transformers":
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(model_name)
            embedding = model.encode([query], normalize_embeddings=True, show_progress_bar=False)
            return np.asarray(embedding, dtype=np.float32)[0]
        except Exception:
            return None
    return None


def dense_candidates(ledger: Path, query: str, pack_by_id: dict[str, dict[str, Any]]) -> tuple[dict[str, float], dict[str, Any]]:
    manifest, embeddings, fallback_embeddings, records = load_embedding_index(ledger)
    if embeddings is None or not records:
        return {}, manifest
    query_embedding = embed_query(query, manifest)
    active_embeddings = embeddings
    if query_embedding is None or query_embedding.shape[0] != embeddings.shape[1]:
        if fallback_embeddings is None:
            return {}, manifest
        active_embeddings = fallback_embeddings
        query_embedding = hashed_embeddings([query], int(fallback_embeddings.shape[1]))[0]
    scores = embeddings @ query_embedding
    if active_embeddings is not embeddings:
        scores = active_embeddings @ query_embedding
    top_indices = np.argsort(scores)[::-1][:80]
    output: dict[str, float] = defaultdict(float)
    for rank, index in enumerate(top_indices, start=1):
        score = float(scores[index])
        if score <= 0:
            continue
        record = records[int(index)]
        for context_id in record.get("parent_context_ids", []):
            if context_id in pack_by_id:
                output[context_id] += 0.9 / (60 + rank)
    return dict(output), manifest


def lexical_fallback_candidates(query: str, terms: list[str], packs: list[dict[str, Any]]) -> dict[str, float]:
    if not terms:
        return {}
    output: dict[str, float] = {}
    lowered_terms = set(terms)
    for pack in packs:
        haystack = " ".join(
            [
                str(pack.get("title", "")),
                str(pack.get("direct_answer", "")),
                " ".join(str(item) for item in pack.get("topics", [])),
                " ".join(str(item) for item in pack.get("useful_context", [])),
                str(pack.get("retrieval_text", "")),
            ]
        ).lower()
        matched = sum(1 for term in lowered_terms if term in haystack)
        if matched:
            output[str(pack["id"])] = matched / 100
    return output


def graph_expand(seed_ids: list[str], pack_by_id: dict[str, dict[str, Any]], memory_contexts: dict[str, list[str]], edges: list[dict[str, Any]]) -> dict[str, float]:
    seed_memory_ids = {
        memory_id
        for context_id in seed_ids
        for memory_id in pack_by_id.get(context_id, {}).get("memory_atoms", [])
    }
    if not seed_memory_ids:
        return {}
    output: dict[str, float] = defaultdict(float)
    for edge in edges:
        left = str(edge.get("from_memory_id", ""))
        right = str(edge.get("to_memory_id", ""))
        weight = float(edge.get("weight", 0.0) or 0.0)
        if left in seed_memory_ids:
            for context_id in memory_contexts.get(right, []):
                if context_id in pack_by_id:
                    output[context_id] += 0.15 * weight
        if right in seed_memory_ids:
            for context_id in memory_contexts.get(left, []):
                if context_id in pack_by_id:
                    output[context_id] += 0.1 * weight
    return dict(output)


def broad_candidates(query: str, intent: str, terms: list[str], packs: list[dict[str, Any]]) -> dict[str, float]:
    term_set = set(terms)
    if has_any_hint(query, term_set, ARCHITECTURE_MATERIAL_HINTS, CHINESE_ARCHITECTURE_MATERIAL_HINTS):
        order = BROAD_ARCHITECTURE_MATERIAL_ORDER
    elif has_any_hint(query, term_set, OFFICIAL_PROFILE_HINTS, CHINESE_OFFICIAL_PROFILE_HINTS):
        order = BROAD_OFFICIAL_PROFILE_ORDER
    elif has_any_hint(query, term_set, RELEASE_HINTS, CHINESE_RELEASE_HINTS):
        order = BROAD_RELEASE_ORDER
    elif has_any_hint(query, term_set, JIRA_LEADERSHIP_HINTS, CHINESE_JIRA_LEADERSHIP_HINTS):
        order = BROAD_JIRA_ORDER
    elif has_any_hint(query, term_set, AUTHORITY_HINTS, CHINESE_AUTHORITY_HINTS):
        order = BROAD_AUTHORITY_ORDER
    elif has_any_hint(query, term_set, PORTFOLIO_HINTS, CHINESE_PORTFOLIO_HINTS):
        order = BROAD_PORTFOLIO_ORDER
    elif has_any_hint(query, term_set, PERSONAL_HINTS, CHINESE_PERSONAL_HINTS) and intent != "proof":
        order = BROAD_PERSONAL_ORDER
    elif has_any_hint(query, term_set, AGENT_COLLAB_HINTS, CHINESE_AGENT_COLLAB_HINTS) and not is_bootstrap_query(query, intent, term_set):
        order = BROAD_AGENT_COLLAB_ORDER
    elif has_any_hint(query, term_set, EXPERIENCE_HINTS, CHINESE_EXPERIENCE_HINTS):
        order = BROAD_EXPERIENCE_ORDER
    elif has_any_hint(query, term_set, REVIEW_HINTS, CHINESE_REVIEW_HINTS) and intent != "proof":
        order = BROAD_REVIEW_ORDER
    elif has_any_hint(query, term_set, ROLE_HINTS, CHINESE_ROLE_HINTS):
        order = BROAD_ROLE_ORDER
    elif has_any_hint(query, term_set, STACK_HINTS, CHINESE_STACK_HINTS):
        order = BROAD_STACK_ORDER
    elif has_any_hint(query, term_set, LEARNING_HINTS, CHINESE_LEARNING_HINTS):
        order = BROAD_LEARNING_ORDER
    elif has_any_hint(query, term_set, STRENGTH_HINTS, CHINESE_STRENGTH_HINTS):
        order = BROAD_STRENGTH_ORDER
    elif has_any_hint(query, term_set, IMPACT_HINTS, CHINESE_IMPACT_HINTS):
        order = BROAD_IMPACT_ORDER
    elif has_any_hint(query, term_set, DOMAIN_HINTS, CHINESE_DOMAIN_HINTS):
        order = BROAD_DOMAIN_ORDER
    elif intent == "coding_style" and (not terms or set(terms).issubset({"code", "coding", "style", "pattern", "patterns"})):
        order = BROAD_CODING_ORDER
    elif not terms:
        order = BROAD_SELF_ORDER
    elif is_bootstrap_query(query, intent, term_set):
        order = BROAD_BOOTSTRAP_ORDER
    elif intent == "act_as_me" and is_architecture_query(query, term_set):
        order = BROAD_ACT_AS_ME_ORDER
    else:
        return {}
    output = {}
    for pack in packs:
        pack_id = str(pack.get("id", ""))
        if pack_id in order:
            output[pack_id] = order[pack_id] / 100
    return output


def preferred_context_id(query: str, intent: str, terms: list[str]) -> str:
    term_set = set(terms)
    if intent == "proof":
        return ""
    if is_bootstrap_query(query, intent, term_set):
        return "context:self_model.agent_operating_context"
    if has_any_hint(query, term_set, ARCHITECTURE_MATERIAL_HINTS, CHINESE_ARCHITECTURE_MATERIAL_HINTS):
        return "context:self_model.architecture_material"
    if has_any_hint(query, term_set, OFFICIAL_PROFILE_HINTS, CHINESE_OFFICIAL_PROFILE_HINTS):
        return "context:self_model.declared_profile"
    if has_any_hint(query, term_set, RELEASE_HINTS, CHINESE_RELEASE_HINTS):
        return "context:self_model.release_ownership"
    if has_any_hint(query, term_set, JIRA_LEADERSHIP_HINTS, CHINESE_JIRA_LEADERSHIP_HINTS):
        return "context:self_model.jira_leadership"
    if has_any_hint(query, term_set, AUTHORITY_HINTS, CHINESE_AUTHORITY_HINTS):
        return "context:self_model.repo_authority"
    if has_any_hint(query, term_set, PORTFOLIO_HINTS, CHINESE_PORTFOLIO_HINTS):
        return "context:self_model.portfolio_cases"
    if has_any_hint(query, term_set, PERSONAL_HINTS, CHINESE_PERSONAL_HINTS):
        return "context:self_model.personal_identity"
    if has_any_hint(query, term_set, AGENT_COLLAB_HINTS, CHINESE_AGENT_COLLAB_HINTS):
        return "context:self_model.agent_collaboration_style"
    if has_any_hint(query, term_set, REVIEW_HINTS, CHINESE_REVIEW_HINTS):
        return "context:self_model.review_style"
    if intent == "act_as_me" and is_architecture_query(query, term_set):
        return "context:self_model.architecture_judgment"
    if has_any_hint(query, term_set, EXPERIENCE_HINTS, CHINESE_EXPERIENCE_HINTS):
        return "context:self_model.career_timeline"
    if has_any_hint(query, term_set, ROLE_HINTS, CHINESE_ROLE_HINTS):
        return "context:self_model.role_identity"
    if has_any_hint(query, term_set, STACK_HINTS, CHINESE_STACK_HINTS):
        return "context:self_model.technical_stack"
    if has_any_hint(query, term_set, LEARNING_HINTS, CHINESE_LEARNING_HINTS):
        return "context:self_model.learning_trajectory"
    if has_any_hint(query, term_set, STRENGTH_HINTS, CHINESE_STRENGTH_HINTS):
        return "context:self_model.experience_scope"
    if has_any_hint(query, term_set, IMPACT_HINTS, CHINESE_IMPACT_HINTS):
        return "context:self_model.impact_profile"
    if has_any_hint(query, term_set, DOMAIN_HINTS, CHINESE_DOMAIN_HINTS):
        return "context:self_model.domain_knowledge"
    if intent == "coding_style":
        return "context:self_model.coding_style"
    if not terms:
        return "context:self_model.master_persona"
    return ""


def deterministic_rerank(pack: dict[str, Any], query: str, terms: list[str], intent: str, base_score: float) -> float:
    score = base_score
    pack_id = str(pack.get("id", ""))
    bootstrap_query = is_bootstrap_query(query, intent, set(terms))
    preferred_context = preferred_context_id(query, intent, terms)
    if preferred_context:
        if pack_id == preferred_context:
            score += 1000.0
        elif pack_id.startswith("context:self_model."):
            score -= 35.0
    if pack.get("intent") == intent:
        score += 0.08
    if pack_id.startswith("context:self_model."):
        score += 0.05
    if not terms:
        if pack_id == "context:self_model.master_persona":
            score += 16.0
        elif pack_id.startswith("context:self_model."):
            score += 2.0
    if has_any_hint(query, set(terms), ARCHITECTURE_MATERIAL_HINTS, CHINESE_ARCHITECTURE_MATERIAL_HINTS):
        score += BROAD_ARCHITECTURE_MATERIAL_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.architecture_material":
            score += 34.0
        if pack_id == "context:self_model.master_persona":
            score -= 4.0
    if has_any_hint(query, set(terms), OFFICIAL_PROFILE_HINTS, CHINESE_OFFICIAL_PROFILE_HINTS):
        score += BROAD_OFFICIAL_PROFILE_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.declared_profile":
            score += 140.0
        if pack_id == "context:self_model.career_timeline":
            score += 5.0
        if pack_id != "context:self_model.declared_profile":
            score -= 15.0
    if has_any_hint(query, set(terms), AUTHORITY_HINTS, CHINESE_AUTHORITY_HINTS):
        score += BROAD_AUTHORITY_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.repo_authority":
            score += 140.0
        if pack_id == "context:self_model.review_authority":
            score += 4.0
        if pack_id != "context:self_model.repo_authority":
            score -= 15.0
    if has_any_hint(query, set(terms), RELEASE_HINTS, CHINESE_RELEASE_HINTS):
        score += BROAD_RELEASE_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.release_ownership":
            score += 140.0
        if pack_id != "context:self_model.release_ownership":
            score -= 15.0
    if has_any_hint(query, set(terms), JIRA_LEADERSHIP_HINTS, CHINESE_JIRA_LEADERSHIP_HINTS):
        score += BROAD_JIRA_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.jira_leadership":
            score += 140.0
        if pack_id != "context:self_model.jira_leadership":
            score -= 15.0
    if has_any_hint(query, set(terms), AGENT_COLLAB_HINTS, CHINESE_AGENT_COLLAB_HINTS) and not bootstrap_query:
        score += BROAD_AGENT_COLLAB_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.agent_collaboration_style":
            score += 34.0
    if has_any_hint(query, set(terms), PORTFOLIO_HINTS, CHINESE_PORTFOLIO_HINTS):
        score += BROAD_PORTFOLIO_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.portfolio_cases":
            score += 80.0
        if pack_id == "context:self_model.domain_knowledge":
            score -= 20.0
    if has_any_hint(query, set(terms), PERSONAL_HINTS, CHINESE_PERSONAL_HINTS) and intent != "proof":
        score += BROAD_PERSONAL_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.personal_identity":
            score += 36.0
    if has_any_hint(query, set(terms), EXPERIENCE_HINTS, CHINESE_EXPERIENCE_HINTS):
        score += BROAD_EXPERIENCE_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.career_timeline":
            score += 22.0
        if pack_id == "context:self_model.experience_scope":
            score += 10.0
        if pack_id == "context:self_model.boundaries_unknowns":
            score += 2.0
        if pack_id == "context:self_model.master_persona":
            score -= 5.0
    if has_any_hint(query, set(terms), REVIEW_HINTS, CHINESE_REVIEW_HINTS) and intent != "proof":
        score += BROAD_REVIEW_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.review_style":
            score += 120.0
        if pack_id == "context:self_model.review_authority":
            score += 28.0
        if pack_id == "context:self_model.quality_bar":
            score += 2.0
        if pack_id == "context:self_model.master_persona":
            score -= 4.0
    if has_any_hint(query, set(terms), ROLE_HINTS, CHINESE_ROLE_HINTS):
        score += BROAD_ROLE_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.role_identity":
            score += 13.0
        if pack_id == "context:self_model.master_persona":
            score -= 4.0
    if has_any_hint(query, set(terms), STACK_HINTS, CHINESE_STACK_HINTS):
        score += BROAD_STACK_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.technical_stack":
            score += 12.0
    if has_any_hint(query, set(terms), STRENGTH_HINTS, CHINESE_STRENGTH_HINTS):
        score += BROAD_STRENGTH_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.experience_scope":
            score += 24.0
    if has_any_hint(query, set(terms), LEARNING_HINTS, CHINESE_LEARNING_HINTS):
        score += BROAD_LEARNING_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.learning_trajectory":
            score += 55.0
        if pack_id == "context:self_model.review_authority":
            score -= 12.0
    if has_any_hint(query, set(terms), IMPACT_HINTS, CHINESE_IMPACT_HINTS) and not has_any_hint(query, set(terms), STRENGTH_HINTS, CHINESE_STRENGTH_HINTS):
        score += BROAD_IMPACT_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.impact_profile":
            score += 12.0
    if has_any_hint(query, set(terms), DOMAIN_HINTS, CHINESE_DOMAIN_HINTS):
        score += BROAD_DOMAIN_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.domain_knowledge":
            score += 55.0
        if pack_id == "context:self_model.review_authority":
            score -= 12.0
    if intent == "coding_style":
        score += BROAD_CODING_ORDER.get(pack_id, 0) / 1000
        if pack_id == "context:self_model.coding_style":
            score += 12.0
        if pack_id.startswith("context:coding_style."):
            score += 7.0
        if pack_id == "context:topic.react":
            score += 6.0
        if pack_id == "context:topic.frontend":
            score -= 2.0
        if "react" in terms and "react" in pack_id:
            score += 4.0
        if pack_id == "context:self_model.master_persona":
            score -= 6.0
    else:
        score += BROAD_SELF_ORDER.get(pack_id, 0) / 1000
    if intent == "act_as_me":
        if bootstrap_query:
            score += BROAD_BOOTSTRAP_ORDER.get(pack_id, 0) / 1000
            if pack_id == "context:self_model.agent_operating_context":
                score += 12.0
            if pack_id == "context:self_model.architecture_judgment":
                score += 7.5
            if pack_id == "context:self_model.quality_bar":
                score += 6.5
            if pack_id == "context:self_model.delivery_leadership":
                score += 5.5
            if pack_id == "context:self_model.master_persona":
                score -= 3.0
        else:
            score += BROAD_ACT_AS_ME_ORDER.get(pack_id, 0) / 1000
            if is_architecture_query(query, set(terms)):
                if pack_id == "context:self_model.architecture_judgment":
                    score += 55.0
                if pack_id == "context:self_model.quality_bar":
                    score += 4.5
                if pack_id == "context:self_model.review_authority":
                    score -= 12.0
                if pack_id == "context:preference.high_bar_correctness":
                    score += 8.0
                if pack_id.startswith("context:decision_pattern."):
                    score += 6.0
            if pack_id == "context:self_model.master_persona":
                score -= 7.0
    if intent == "proof":
        if "react" in terms and "react" in pack_id:
            score += 12.0
        if pack_id == "context:topic.react":
            score += 14.0
        if pack_id.startswith("context:coding_style."):
            score += 6.0
        if pack_id == "context:topic.frontend":
            score -= 2.0
        if pack_id.startswith("context:self_model."):
            score -= 8.0
        if pack_id == "context:self_model.agent_operating_context":
            score -= 4.0
    haystack = " ".join(
        [
            str(pack.get("title", "")),
            str(pack.get("direct_answer", "")),
            " ".join(str(item) for item in pack.get("topics", [])),
            str(pack.get("retrieval_text", "")),
        ]
    ).lower()
    score += sum(0.015 for term in terms if term in haystack)
    if intent == "proof" and pack.get("private_trace_refs"):
        score += 0.04
    return score


def cross_encoder_rerank(query: str, packs: list[dict[str, Any]], model_name: str) -> list[float] | None:
    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(model_name)
        pairs = [[query, str(pack.get("retrieval_text") or pack.get("direct_answer") or pack.get("title"))] for pack in packs]
        scores = model.predict(pairs)
        return [float(score) for score in scores]
    except Exception:
        return None


def sanitize_pack(row: dict[str, Any], include_trace_refs: bool) -> dict[str, Any]:
    output = {
        "id": row.get("id"),
        "intent": row.get("intent"),
        "title": row.get("title"),
        "direct_answer": row.get("direct_answer"),
        "useful_context": row.get("useful_context", []),
        "behavioral_guidance": row.get("behavioral_guidance", []),
        "known_limits": row.get("known_limits", []),
        "topics": row.get("topics", []),
        "confidence": "strong" if row.get("memory_atoms") else "medium",
        "_score": row.get("_score"),
        "_retrieval_channels": row.get("_retrieval_channels", []),
    }
    if include_trace_refs:
        output["memory_atoms"] = row.get("memory_atoms", [])
        output["private_trace_refs"] = row.get("private_trace_refs", [])
    else:
        output["private_trace_available"] = bool(row.get("private_trace_refs"))
    return output


def provenance_for(rows: list[dict[str, Any]], provenance_rows: list[dict[str, Any]], terms: list[str] | None = None) -> list[dict[str, Any]]:
    memory_ids = {str(memory_id) for row in rows for memory_id in row.get("memory_atoms", [])}
    if terms:
        term_filtered = {
            memory_id
            for memory_id in memory_ids
            if any(term in expanded_tokens(memory_id) for term in terms)
        }
        if term_filtered:
            memory_ids = term_filtered
    output = []
    seen = set()
    for item in provenance_rows:
        if item.get("memory_id") not in memory_ids:
            continue
        key = (item.get("memory_id"), item.get("source_id"))
        if key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "memory_id": item.get("memory_id"),
                "source_id": item.get("source_id"),
                "source_type": item.get("source_type"),
                "support_role": item.get("support_role"),
                "strength": item.get("strength"),
                "reason": item.get("reason"),
            }
        )
        if len(output) >= 80:
            break
    return output


def query_self_context(
    ledger: Path,
    query: str,
    top: int = 5,
    intent: str | None = None,
    include_provenance: bool = False,
    min_score: float = 0.0,
    rerank: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    packs = load_context_packs(ledger)
    pack_by_id = {str(pack["id"]): pack for pack in packs}
    memory_contexts = memory_to_context_ids(packs)
    resolved_intent = intent or infer_intent(query)
    provenance_enabled = include_provenance or resolved_intent == "proof"
    terms = search_terms(query)

    channels: dict[str, dict[str, float]] = {}
    channels["broad"] = broad_candidates(query, resolved_intent, terms, packs)
    channels["fts"] = fts_candidates(ledger, terms, pack_by_id, memory_contexts)
    dense, embedding_manifest = dense_candidates(ledger, query, pack_by_id)
    channels["dense"] = dense
    if not channels["fts"]:
        channels["lexical"] = lexical_fallback_candidates(query, terms, packs)

    combined: dict[str, float] = defaultdict(float)
    channel_names: dict[str, set[str]] = defaultdict(set)
    weights = {"broad": 1.0, "fts": 1.0, "dense": 0.9, "lexical": 0.7, "graph": 0.4}
    for channel, scores in channels.items():
        for context_id, score in scores.items():
            if context_id in pack_by_id:
                combined[context_id] += weights.get(channel, 1.0) * score
                channel_names[context_id].add(channel)

    graph_scores = graph_expand(
        [context_id for context_id, _ in sorted(combined.items(), key=lambda item: item[1], reverse=True)[:20]],
        pack_by_id,
        memory_contexts,
        load_edges(ledger),
    )
    for context_id, score in graph_scores.items():
        combined[context_id] += weights["graph"] * score
        channel_names[context_id].add("graph")

    candidates = []
    for context_id, score in combined.items():
        if score < min_score:
            continue
        pack = dict(pack_by_id[context_id])
        pack["_base_score"] = round(score, 6)
        pack["_retrieval_channels"] = sorted(channel_names[context_id])
        candidates.append(pack)

    if not candidates:
        candidates = [dict(pack) for pack in packs if str(pack.get("id", "")).startswith("context:self_model.")][:top]
        for pack in candidates:
            pack["_base_score"] = 0.0
            pack["_retrieval_channels"] = ["fallback"]

    candidates.sort(key=lambda pack: deterministic_rerank(pack, query, terms, resolved_intent, float(pack.get("_base_score", 0.0))), reverse=True)
    candidates = candidates[:50]

    cross_scores = None
    if rerank:
        reranker_model = str(embedding_manifest.get("reranker_model") or "cross-encoder/ms-marco-MiniLM-L6-v2")
        cross_scores = cross_encoder_rerank(query, candidates, reranker_model)
    for index, pack in enumerate(candidates):
        base = float(pack.get("_base_score", 0.0))
        score = deterministic_rerank(pack, query, terms, resolved_intent, base)
        if cross_scores is not None:
            score += float(cross_scores[index]) / 10.0
            pack["_retrieval_channels"] = sorted(set(pack.get("_retrieval_channels", [])) | {"cross_encoder"})
        pack["_score"] = round(score, 6)

    candidates.sort(key=lambda pack: (pack["_score"], len(pack.get("memory_atoms", []))), reverse=True)
    selected = candidates[:top]
    answer_contexts = [sanitize_pack(pack, provenance_enabled) for pack in selected]
    result: dict[str, Any] = {
        "query": query,
        "intent": resolved_intent,
        "answer_contexts": answer_contexts,
        "meta": {
            "engine": QUERY_ENGINE_VERSION,
            "ledger": str(ledger),
            "elapsedMs": round((time.perf_counter() - started) * 1000),
            "context_pack_count": len(packs),
            "candidateRows": len(candidates),
            "returned": len(answer_contexts),
            "provenance_included": provenance_enabled,
            "embedding_backend": embedding_manifest.get("backend"),
            "embedding_model": embedding_manifest.get("model_name"),
            "rerank_requested": rerank,
            "cross_encoder_used": cross_scores is not None,
            "channels": {name: len(scores) for name, scores in channels.items()},
        },
    }
    if provenance_enabled:
        result["provenance"] = provenance_for(selected, load_provenance(ledger), terms)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--intent", choices=["self_knowledge", "act_as_me", "coding_style", "preference", "work_context", "personal_context", "project_context", "relationship_context", "proof", "gap"], help="Override inferred intent.")
    parser.add_argument("--include-provenance", action="store_true")
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--rerank", action="store_true", help="Try CrossEncoder reranking over top candidates.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    result = query_self_context(
        ledger=ledger,
        query=args.query,
        top=args.top,
        intent=args.intent,
        include_provenance=args.include_provenance,
        min_score=args.min_score,
        rerank=args.rerank,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"# Self Context Query\n\nQuery: {args.query}\nIntent: {result['intent']}\n")
    for index, context in enumerate(result["answer_contexts"], start=1):
        print(f"## {index}. {context['title']}")
        print(context["direct_answer"])
        for item in context.get("useful_context", []):
            print(f"- {item}")


if __name__ == "__main__":
    main()
