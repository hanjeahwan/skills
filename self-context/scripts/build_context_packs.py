#!/usr/bin/env python3
"""Build MCP-ready self-context packs from memory atoms."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from build_persona_sections import CANONICAL_SECTION_IDS
from ledger_paths import resolve_ledger_path


INTENT_BY_MEMORY_TYPE = {
    "identity": "self_knowledge",
    "capability": "self_knowledge",
    "coding_style": "coding_style",
    "decision_pattern": "act_as_me",
    "preference": "preference",
    "communication_style": "act_as_me",
    "work_history": "work_context",
    "project_context": "project_context",
    "personal_context": "personal_context",
    "relationship_context": "relationship_context",
    "knowledge": "self_knowledge",
    "goal": "self_knowledge",
    "constraint": "act_as_me",
    "private_boundary": "act_as_me",
    "unknown_gap": "gap",
    "identity_fact": "self_knowledge",
    "career_timeline": "work_context",
    "experience_scope": "work_context",
    "role_identity": "self_knowledge",
    "technical_stack": "self_knowledge",
    "impact_profile": "work_context",
    "declared_profile": "work_context",
    "review_style": "act_as_me",
    "review_authority": "act_as_me",
    "repo_authority": "relationship_context",
    "release_ownership": "work_context",
    "jira_leadership": "work_context",
    "architecture_material": "work_context",
    "agent_collaboration_style": "act_as_me",
    "portfolio_cases": "project_context",
    "personal_identity": "personal_context",
    "learning_trajectory": "self_knowledge",
}

TARGETED_ATOM_MEMORY_TYPES = {
    "coding_style",
    "decision_pattern",
    "capability",
    "knowledge",
    "preference",
    "private_boundary",
    "unknown_gap",
    "career_timeline",
    "experience_scope",
    "role_identity",
    "technical_stack",
    "impact_profile",
    "declared_profile",
    "review_style",
    "review_authority",
    "repo_authority",
    "release_ownership",
    "jira_leadership",
    "architecture_material",
    "agent_collaboration_style",
    "portfolio_cases",
    "personal_identity",
    "learning_trajectory",
}

TARGETED_ATOM_TOPICS = {
    "react",
    "typescript",
    "architecture",
    "ai_product",
    "agent",
    "mcp",
    "security",
    "ci_cd",
    "analytics",
    "recruiting",
    "employee",
    "testing",
    "review",
    "review_authority",
    "web_infra",
    "career_timeline",
    "experience_scope",
    "role_identity",
    "technical_stack",
    "impact",
    "bug_reduction",
    "learning_trajectory",
    "full_stack",
    "declared_profile",
    "review_style",
    "repo_authority",
    "release_ownership",
    "jira_leadership",
    "architecture_material",
    "agent_collaboration",
    "portfolio_cases",
    "personal_identity",
}

TOPIC_INTENT = {
    "react": "coding_style",
    "typescript": "coding_style",
    "architecture": "act_as_me",
    "review": "act_as_me",
    "quality": "act_as_me",
    "delivery": "work_context",
    "leadership": "work_context",
    "ai_product": "act_as_me",
    "agent": "act_as_me",
    "mcp": "act_as_me",
    "recruiting": "self_knowledge",
    "employee": "self_knowledge",
    "analytics": "self_knowledge",
    "admin": "self_knowledge",
    "career_timeline": "work_context",
    "experience_scope": "work_context",
    "role_identity": "self_knowledge",
    "technical_stack": "self_knowledge",
    "impact": "work_context",
    "bug_reduction": "work_context",
    "declared_profile": "work_context",
    "review_style": "act_as_me",
    "review_authority": "act_as_me",
    "repo_authority": "relationship_context",
    "release_ownership": "work_context",
    "jira_leadership": "work_context",
    "architecture_material": "work_context",
    "agent_collaboration": "act_as_me",
    "portfolio_cases": "project_context",
    "personal_identity": "personal_context",
    "learning_trajectory": "self_knowledge",
    "full_stack": "work_context",
}

SKIP_TOPIC_PACKS = {"frontend", "product", "quality", "delivery", "leadership"}

ANSWER_MATERIAL_REQUIRED = {
    "headline",
    "talking_points",
    "evidence_summary",
    "caveats",
    "suggested_followups",
}

BANNED_ANSWER_PHRASES = (
    "use this topic pack",
    "common implementation surfaces",
    "raw source evidence",
    "declared profile should",
    "release ownership layer",
    "my release ownership layer",
    "he likely",
    "this supports",
    "this gives him",
    "the useful memory is",
    "context pack",
    "private_trace_refs",
)

SOURCE_LEAK_PATTERN = re.compile(
    r"\b(?:git_commit|jira_ticket|source_id|private_trace_refs|trace):|"
    r"\b[a-f0-9]{40}\b|"
    r"\b[A-Z][A-Z0-9]+-\d+\b"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def compact_list(values: Iterable[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        if "`profiles/" in text or "`reports/" in text or "`case-studies/" in text:
            continue
        seen.add(text)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def clean_answer_text(value: str) -> str:
    text = " ".join(str(value).replace("\n", " ").split()).strip()
    lowered = text.lower()
    if not text:
        return ""
    if any(phrase in lowered for phrase in BANNED_ANSWER_PHRASES):
        return ""
    if SOURCE_LEAK_PATTERN.search(text):
        return ""
    return text


def compact_answer_list(values: Iterable[str], limit: int = 6) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = clean_answer_text(str(value))
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def topic_phrase(topics: list[str]) -> str:
    clean_topics = [topic.replace("_", " ") for topic in topics if topic]
    if not clean_topics:
        return "this area"
    return ", ".join(clean_topics[:3])


def answer_material(
    *,
    headline: str,
    talking_points: Iterable[str],
    evidence_summary: Iterable[str],
    caveats: Iterable[str],
    topics: list[str],
    memory_count: int,
    unknown_gap: bool = False,
) -> dict[str, Any]:
    clean_headline = clean_answer_text(headline)
    clean_talking_points = compact_answer_list(talking_points, 6)
    clean_evidence = compact_answer_list(evidence_summary, 4)
    clean_caveats = compact_answer_list(caveats, 3)

    if not clean_headline:
        clean_headline = clean_talking_points[0] if clean_talking_points else f"This context covers {topic_phrase(topics)}."
    if not clean_talking_points:
        clean_talking_points = [clean_headline]
    if not clean_evidence:
        if unknown_gap:
            clean_evidence = ["Dedicated source material for this area has not been imported yet."]
        elif memory_count > 1:
            clean_evidence = [f"Supported by multiple distilled work signals around {topic_phrase(topics)}."]
        elif memory_count == 1:
            clean_evidence = [f"Supported by a distilled work signal around {topic_phrase(topics)}."]
        else:
            clean_evidence = ["This is synthesized from the current self-model section, with proof available only on explicit request."]

    return {
        "headline": clean_headline,
        "talking_points": clean_talking_points[:6],
        "evidence_summary": clean_evidence[:4],
        "caveats": clean_caveats[:3],
        "suggested_followups": compact_answer_list(
            [
                "Ask for proof if you need audit-ready evidence.",
                "Ask for project examples if you want this turned into an interview story.",
                "Ask for limits if the role requires formal ownership claims.",
            ],
            3,
        ),
    }


def pack_for_atom(atom: dict[str, Any], generated_at: str) -> dict[str, Any]:
    memory_type = str(atom.get("memory_type", "self_knowledge"))
    intent = INTENT_BY_MEMORY_TYPE.get(memory_type, "self_knowledge")
    topics = [str(item) for item in atom.get("topics", [])]
    useful_context = compact_answer_list([str(item) for item in atom.get("useful_context", [])], 10)
    guardrails = compact_answer_list([str(item) for item in atom.get("guardrails", [])], 8)
    statement = str(atom.get("statement", ""))
    behavioral_use = clean_answer_text(str(atom.get("behavioral_use", "Use this memory as useful personal context.")))
    trace_refs = [str(item) for item in atom.get("provenance_refs", [])]
    material = answer_material(
        headline=statement,
        talking_points=useful_context or [statement],
        evidence_summary=[],
        caveats=guardrails,
        topics=topics,
        memory_count=1,
        unknown_gap=memory_type == "unknown_gap",
    )

    return {
        "id": atom["id"].replace("memory:", "context:", 1),
        "intent": intent,
        "title": statement[:120],
        "direct_answer": material["headline"],
        "answer_material": material,
        "useful_context": useful_context or [statement],
        "behavioral_guidance": compact_answer_list([behavioral_use], 5),
        "known_limits": guardrails,
        "memory_atoms": [atom["id"]],
        "private_trace_refs": trace_refs,
        "topics": topics,
        "updated_at": generated_at,
        "retrieval_text": "\n".join(
            [
                f"Intent: {intent}",
                f"Topics: {', '.join(topics)}",
                f"Direct answer: {statement}",
                "Useful context:",
                *[f"- {item}" for item in useful_context],
                "Behavioral guidance:",
                f"- {behavioral_use}",
                "Known limits:",
                *[f"- {item}" for item in guardrails],
            ]
        ).strip(),
    }


def pack_for_section(section: dict[str, Any], atom_by_id: dict[str, dict[str, Any]], generated_at: str) -> dict[str, Any] | None:
    atom_ids = [item for item in section.get("memory_atoms", []) if item in atom_by_id]
    atoms = [atom_by_id[item] for item in atom_ids]
    section_type = str(section.get("section_type", "self_knowledge"))
    intent = str(section.get("intent") or INTENT_BY_MEMORY_TYPE.get(section_type, "self_knowledge"))
    topics = compact_list(
        [str(topic) for topic in section.get("topics", [])]
        or [str(topic) for atom in atoms for topic in atom.get("topics", [])],
        24,
    )
    contexts = compact_answer_list([str(item) for item in section.get("practical_guidance", [])], 12)
    guardrails = compact_answer_list([str(item) for item in section.get("known_limits", [])], 10)
    trace_refs = compact_list([str(item) for atom in atoms for item in atom.get("provenance_refs", [])], 20)
    title = str(section.get("title") or section_type.replace("_", " ").title())
    behavioral_guidance = compact_answer_list([str(item) for item in section.get("decision_biases", [])], 8)
    summary = str(section.get("summary") or "")
    material = answer_material(
        headline=summary,
        talking_points=[*contexts, *behavioral_guidance],
        evidence_summary=[],
        caveats=guardrails,
        topics=topics,
        memory_count=len(atom_ids),
        unknown_gap=section_type == "unknown_gap" or "unknown" in section_type,
    )

    return {
        "id": str(section.get("id", f"self_model:{section_type}")).replace("self_model:", "context:self_model.", 1),
        "intent": intent,
        "title": title,
        "direct_answer": material["headline"],
        "answer_material": material,
        "useful_context": contexts,
        "behavioral_guidance": behavioral_guidance
        or [
            "Prioritize practical context before audit detail.",
            "Apply known limits before suggesting actions.",
        ],
        "known_limits": guardrails,
        "memory_atoms": atom_ids,
        "private_trace_refs": trace_refs,
        "topics": topics,
        "updated_at": generated_at,
        "retrieval_text": "\n".join(
            [
                f"Intent: {intent}",
                f"Section: {title}",
                f"Topics: {', '.join(topics)}",
                f"Summary: {section.get('summary', '')}",
                "Practical guidance:",
                *[f"- {item}" for item in section.get("practical_guidance", [])],
                "Decision biases:",
                *[f"- {item}" for item in section.get("decision_biases", [])],
                "Useful context:",
                *[f"- {item}" for item in contexts],
                "Known limits:",
                *[f"- {item}" for item in guardrails],
            ]
        ).strip(),
    }


def should_pack_atom(atom: dict[str, Any]) -> bool:
    memory_type = str(atom.get("memory_type", ""))
    if memory_type in TARGETED_ATOM_MEMORY_TYPES:
        return True
    topics = {str(item) for item in atom.get("topics", [])}
    return bool(topics & TARGETED_ATOM_TOPICS)


def pack_for_topic(topic: str, atoms: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    atom_ids = [atom["id"] for atom in atoms]
    statements = compact_answer_list((str(atom.get("statement", "")) for atom in atoms), 8)
    contexts = compact_answer_list((item for atom in atoms for item in atom.get("useful_context", [])), 12)
    guardrails = compact_answer_list((item for atom in atoms for item in atom.get("guardrails", [])), 10)
    trace_refs = compact_list((item for atom in atoms for item in atom.get("provenance_refs", [])), 20)
    memory_types = {str(atom.get("memory_type", "")) for atom in atoms}
    intent = TOPIC_INTENT.get(topic, "coding_style" if "coding_style" in memory_types else "self_knowledge")

    material = answer_material(
        headline=" ".join(statements[:2]),
        talking_points=contexts or statements,
        evidence_summary=[f"Supported by multiple distilled memories around {topic.replace('_', ' ')}."],
        caveats=guardrails,
        topics=[topic],
        memory_count=len(atom_ids),
    )

    return {
        "id": f"context:topic.{topic}",
        "intent": intent,
        "title": topic.replace("_", " ").title(),
        "direct_answer": material["headline"],
        "answer_material": material,
        "useful_context": contexts or statements,
        "behavioral_guidance": [
            "Answer this area with practical examples and clear limits.",
            "Keep audit detail separate unless explicitly requested.",
        ],
        "known_limits": guardrails,
        "memory_atoms": atom_ids,
        "private_trace_refs": trace_refs,
        "topics": [topic],
        "updated_at": generated_at,
        "retrieval_text": "\n".join(
            [
                f"Topic: {topic}",
                f"Intent: {intent}",
                "Statements:",
                *[f"- {item}" for item in statements],
                "Useful context:",
                *[f"- {item}" for item in contexts],
                "Known limits:",
                *[f"- {item}" for item in guardrails],
            ]
        ).strip(),
    }


def raw_excerpt(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("raw_excerpt")
    return value if isinstance(value, dict) else {}


def project_source_pack(row: dict[str, Any], generated_at: str) -> dict[str, Any] | None:
    raw = raw_excerpt(row)
    repo = raw.get("repo") if isinstance(raw.get("repo"), dict) else {}
    repo_name = str(repo.get("name") or row.get("title") or "").strip()
    repo_slug = str(repo.get("slug") or repo_name).strip()
    source_id = str(row.get("id") or row.get("source_id") or "").strip()
    if not repo_name or not source_id:
        return None

    source_type = str(row.get("source_type") or "")
    stack = [str(item) for item in raw.get("stack", []) if item]
    domains = [str(item) for item in raw.get("domains", []) if item]
    guardrails = [str(item) for item in raw.get("guardrails", []) if item]
    project_kind = str(raw.get("project_kind") or "project context")
    row_topics = [str(item) for item in row.get("topics") or row.get("tags") or [] if item]
    topics = compact_list([repo_name, repo_slug, source_type, project_kind, *row_topics, *stack, *domains], 32)

    if source_id.startswith("project_coding_contract:"):
        intent = "coding_style"
        title = f"Project coding contract: {repo_name}"
        primary_points = [str(item) for item in raw.get("coding_contract", []) if item]
    elif source_type == "project_symbol_graph":
        intent = "coding_style"
        title = f"Project symbol graph: {repo_name}"
        primary_points = [str(item) for item in raw.get("symbol_guidance", []) if item]
    elif source_type == "project_feature_surface":
        intent = "project_context"
        title = f"Project feature surfaces: {repo_name}"
        primary_points = [str(item) for item in raw.get("feature_guidance", []) if item]
    elif source_type == "project_dependency_graph":
        intent = "project_context"
        title = f"Project dependency graph: {repo_name}"
        primary_points = [str(item) for item in raw.get("dependency_guidance", []) if item]
    elif source_type == "project_api_contract_surface":
        intent = "coding_style"
        title = f"Project API contract surface: {repo_name}"
        primary_points = [str(item) for item in raw.get("api_contract_guidance", []) if item]
    elif source_type == "project_quality_surface":
        intent = "work_context"
        title = f"Project quality surface: {repo_name}"
        primary_points = [str(item) for item in raw.get("quality_guidance", []) if item]
    elif source_type == "project_documentation_surface":
        intent = "work_context"
        title = f"Project documentation surface: {repo_name}"
        primary_points = [str(item) for item in raw.get("documentation_guidance", []) if item]
    elif source_type == "project_route_navigation":
        intent = "project_context"
        title = f"Project route and navigation surface: {repo_name}"
        primary_points = [str(item) for item in raw.get("route_navigation_guidance", []) if item]
    elif source_type == "release_activity":
        intent = "work_context"
        title = f"Project release context: {repo_name}"
        primary_points = [str(item) for item in raw.get("release_guidance", []) if item]
    elif source_type == "portfolio_case":
        intent = "project_context"
        title = f"Project case context: {repo_name}"
        primary_points = [str(item) for item in raw.get("case_study_angles", []) if item]
    else:
        intent = "project_context"
        title = f"Project architecture context: {repo_name}"
        primary_points = [str(item) for item in raw.get("practical_guidance", []) if item]

    stack_point = f"Stack signals: {', '.join(stack[:10])}." if stack else ""
    domain_point = f"Domain signals: {', '.join(domains[:10])}." if domains else ""
    headline = str(row.get("summary") or f"{repo_name} is {project_kind}.")
    material = answer_material(
        headline=headline,
        talking_points=[
            f"{repo_name} is classified as {project_kind}.",
            stack_point,
            domain_point,
            *primary_points,
        ],
        evidence_summary=[
            "Distilled from local project structure, package metadata, workflows, and code-pattern signals.",
        ],
        caveats=guardrails,
        topics=topics,
        memory_count=1,
    )

    important_files = [str(item) for item in raw.get("important_files", []) if item]
    top_level_areas = raw.get("top_level_areas", [])
    area_text = []
    if isinstance(top_level_areas, list):
        for item in top_level_areas[:12]:
            if isinstance(item, dict) and item.get("name"):
                area_text.append(f"{item.get('name')} ({item.get('files', 0)} files)")
    representative_symbols = raw.get("representative_symbols", [])
    symbol_text = []
    if isinstance(representative_symbols, list):
        for item in representative_symbols[:30]:
            if not isinstance(item, dict):
                continue
            signals = ", ".join(str(signal) for signal in item.get("signals", [])[:4])
            symbol_text.append(
                " ".join(
                    part
                    for part in [
                        str(item.get("kind", "")),
                        str(item.get("name", "")),
                        f"at {item.get('path')}" if item.get("path") else "",
                        f"signals={signals}" if signals else "",
                    ]
                    if part
                )
            )
    feature_surfaces = raw.get("feature_surfaces", [])
    feature_text = []
    if isinstance(feature_surfaces, list):
        for item in feature_surfaces[:24]:
            if not isinstance(item, dict):
                continue
            signals = item.get("signals", {})
            signal_text = ", ".join(f"{key}:{value}" for key, value in list(signals.items())[:5]) if isinstance(signals, dict) else ""
            feature_text.append(
                " ".join(
                    part
                    for part in [
                        str(item.get("name", "")),
                        f"files={item.get('files')}" if item.get("files") is not None else "",
                        f"signals={signal_text}" if signal_text else "",
                    ]
                    if part
                )
            )
    dependency_edges = raw.get("internal_dependency_edges", [])
    dependency_text = []
    if isinstance(dependency_edges, list):
        for item in dependency_edges[:30]:
            if isinstance(item, dict) and item.get("from") and item.get("to"):
                dependency_text.append(f"{item.get('from')} -> {item.get('to')} imports={item.get('imports', 0)}")
    dependency_counts = raw.get("external_dependency_counts", {})
    dependency_count_text = []
    if isinstance(dependency_counts, dict):
        dependency_count_text = [f"{key}:{value}" for key, value in list(dependency_counts.items())[:30]]
    api_surfaces = raw.get("api_contract_surfaces", [])
    api_text = []
    if isinstance(api_surfaces, list):
        for item in api_surfaces[:24]:
            if not isinstance(item, dict):
                continue
            methods = item.get("method_counts", {})
            method_text = ", ".join(f"{key}:{value}" for key, value in list(methods.items())[:5]) if isinstance(methods, dict) else ""
            api_text.append(
                " ".join(
                    part
                    for part in [
                        str(item.get("surface", "")),
                        f"api_files={item.get('api_files')}" if item.get("api_files") is not None else "",
                        f"type_contracts={item.get('type_contracts')}" if item.get("type_contracts") is not None else "",
                        f"methods={method_text}" if method_text else "",
                    ]
                    if part
                )
            )
    quality_surfaces = raw.get("quality_surfaces", [])
    quality_text = []
    if isinstance(quality_surfaces, list):
        for item in quality_surfaces[:24]:
            if not isinstance(item, dict):
                continue
            quality_text.append(
                " ".join(
                    part
                    for part in [
                        str(item.get("surface", "")),
                        f"tests={item.get('test_files')}" if item.get("test_files") is not None else "",
                        f"workflows={item.get('workflow_files')}" if item.get("workflow_files") is not None else "",
                        f"configs={item.get('quality_config_files')}" if item.get("quality_config_files") is not None else "",
                    ]
                    if part
                )
            )
    route_surfaces = raw.get("route_navigation_surfaces", [])
    route_text = []
    if isinstance(route_surfaces, list):
        for item in route_surfaces[:24]:
            if not isinstance(item, dict):
                continue
            route_text.append(
                " ".join(
                    part
                    for part in [
                        str(item.get("surface", "")),
                        f"routes={item.get('route_count')}" if item.get("route_count") is not None else "",
                        f"route_files={item.get('route_files')}" if item.get("route_files") is not None else "",
                        f"navigation_files={item.get('navigation_files')}" if item.get("navigation_files") is not None else "",
                        f"guard_files={item.get('guard_files')}" if item.get("guard_files") is not None else "",
                        f"guards={item.get('guard_count')}" if item.get("guard_count") is not None else "",
                        f"lazy={item.get('lazy_boundary_count')}" if item.get("lazy_boundary_count") is not None else "",
                        f"redirects={item.get('redirect_count')}" if item.get("redirect_count") is not None else "",
                    ]
                    if part
                )
            )
    documentation_surfaces = raw.get("documentation_surfaces", [])
    documentation_text = []
    if isinstance(documentation_surfaces, list):
        for item in documentation_surfaces[:24]:
            if not isinstance(item, dict):
                continue
            docs = item.get("representative_docs", [])
            doc_titles = []
            if isinstance(docs, list):
                for doc in docs[:4]:
                    if isinstance(doc, dict):
                        headings = doc.get("headings", [])
                        heading_text = "; ".join(str(heading) for heading in headings[:3]) if isinstance(headings, list) else ""
                        doc_titles.append(f"{doc.get('path')}: {heading_text}".strip(": "))
            documentation_text.append(
                " ".join(
                    part
                    for part in [
                        str(item.get("surface", "")),
                        f"docs={item.get('doc_files')}" if item.get("doc_files") is not None else "",
                        f"headings={item.get('heading_count')}" if item.get("heading_count") is not None else "",
                        f"examples={' | '.join(doc_titles[:3])}" if doc_titles else "",
                    ]
                    if part
                )
            )

    return {
        "id": f"context:project.{source_id.replace(':', '.')}",
        "intent": intent,
        "title": title,
        "direct_answer": material["headline"],
        "answer_material": material,
        "useful_context": material["talking_points"],
        "behavioral_guidance": compact_answer_list(primary_points, 6)
        or ["Use this as project-specific context before falling back to broad persona sections."],
        "known_limits": compact_answer_list(guardrails, 8),
        "memory_atoms": [],
        "private_trace_refs": [source_id],
        "topics": topics,
        "updated_at": generated_at,
        "retrieval_text": "\n".join(
            [
                f"Intent: {intent}",
                f"Project: {repo_name}",
                f"Repository: {repo_slug}",
                f"Source type: {source_type}",
                f"Project kind: {project_kind}",
                f"Topics: {', '.join(topics)}",
                f"Summary: {row.get('summary', '')}",
                f"Stack: {', '.join(stack)}",
                f"Domains: {', '.join(domains)}",
                "Important files:",
                *[f"- {item}" for item in important_files[:30]],
                "Top-level areas:",
                *[f"- {item}" for item in area_text],
                "Representative symbols:",
                *[f"- {item}" for item in symbol_text],
                "Feature surfaces:",
                *[f"- {item}" for item in feature_text],
                "Dependency graph:",
                *[f"- {item}" for item in dependency_text],
                "External dependencies:",
                *[f"- {item}" for item in dependency_count_text],
                "API contract surfaces:",
                *[f"- {item}" for item in api_text],
                "Quality surfaces:",
                *[f"- {item}" for item in quality_text],
                "Quality scripts:",
                *[f"- {item}" for item in raw.get("quality_scripts", [])[:20]],
                "Documentation surfaces:",
                *[f"- {item}" for item in documentation_text],
                "Route and navigation surfaces:",
                *[f"- {item}" for item in route_text],
                "Practical guidance:",
                *[f"- {item}" for item in primary_points],
                "Known limits:",
                *[f"- {item}" for item in guardrails],
            ]
        ).strip(),
    }


def source_context_suffix(row: dict[str, Any]) -> str:
    raw_id = str(row.get("id") or row.get("source_id") or "source").strip()
    if ":" in raw_id:
        raw_id = raw_id.split(":", 1)[1]
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_id).strip("_") or "source"


def personal_material_pack(row: dict[str, Any], generated_at: str) -> dict[str, Any] | None:
    raw = raw_excerpt(row)
    source_id = str(row.get("id") or row.get("source_id") or "").strip()
    if not source_id:
        return None
    topics = compact_list([str(item) for item in row.get("topics") or row.get("tags") or [] if item], 24)
    declared_preference = clean_answer_text(str(raw.get("declared_preference") or ""))
    guidance = compact_answer_list([str(item) for item in raw.get("behavioral_guidance", [])], 6)
    guardrails = compact_answer_list([str(item) for item in raw.get("guardrails", [])], 5)
    headline = str(row.get("summary") or row.get("title") or declared_preference)
    material = answer_material(
        headline=headline,
        talking_points=[declared_preference, *guidance],
        evidence_summary=["Declared by the user as local personal material."],
        caveats=guardrails,
        topics=topics,
        memory_count=0,
    )
    return {
        "id": f"context:personal_material.{source_context_suffix(row)}",
        "intent": "personal_context",
        "title": str(row.get("title") or "Declared personal material")[:160],
        "direct_answer": material["headline"],
        "answer_material": material,
        "useful_context": material["talking_points"],
        "behavioral_guidance": guidance,
        "known_limits": guardrails,
        "memory_atoms": [],
        "private_trace_refs": [source_id],
        "topics": topics,
        "updated_at": generated_at,
        "retrieval_text": "\n".join(
            [
                "Intent: personal_context",
                f"Title: {row.get('title', '')}",
                f"Topics: {', '.join(topics)}",
                f"Summary: {row.get('summary', '')}",
                f"Declared preference: {declared_preference}",
                "Behavioral guidance:",
                *[f"- {item}" for item in guidance],
                "Known limits:",
                *[f"- {item}" for item in guardrails],
            ]
        ).strip(),
    }


def agent_sessions_pack(rows: list[dict[str, Any]], generated_at: str) -> dict[str, Any] | None:
    if not rows:
        return None
    signal_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    guidance_counts: Counter[str] = Counter()
    prompt_count = 0
    trace_refs = []
    for row in rows:
        raw = raw_excerpt(row)
        provider = str(raw.get("provider") or row.get("url_or_path") or "agent")
        provider_counts[provider] += 1
        prompt_count += int(raw.get("prompt_count") or 0)
        signal_value = raw.get("signal_counts", {})
        if isinstance(signal_value, dict):
            for key, value in signal_value.items():
                signal_counts[str(key)] += int(value or 0)
        for item in raw.get("collaboration_guidance", []):
            text = clean_answer_text(str(item))
            if text:
                guidance_counts[text] += 1
        if row.get("id") and len(trace_refs) < 40:
            trace_refs.append(str(row["id"]))

    topics = compact_list(["agent_collaboration", "agent_sessions", "work_style", *signal_counts.keys()], 24)
    dominant_signals = ", ".join(name.replace("_", " ") for name, _ in signal_counts.most_common(5)) or "agent collaboration"
    provider_text = ", ".join(f"{name}:{count}" for name, count in provider_counts.most_common())
    guidance = [item for item, _ in guidance_counts.most_common(6)]
    material = answer_material(
        headline=f"Redacted agent-session history shows a collaboration style centered on {dominant_signals}.",
        talking_points=[
            f"Session coverage spans {sum(provider_counts.values())} redacted sessions and {prompt_count} user prompts.",
            f"Provider mix: {provider_text}.",
            *guidance,
        ],
        evidence_summary=["Distilled from redacted Codex and Claude session metadata, not raw transcript dumps."],
        caveats=[
            "Do not expose raw prompts, session ids, local paths, tokens, or private third-party content by default.",
            "Do not infer personal-life preferences from work-agent sessions.",
        ],
        topics=topics,
        memory_count=0,
    )
    signal_text = [f"{name}:{count}" for name, count in signal_counts.most_common(20)]
    return {
        "id": "context:agent_sessions.collaboration_patterns",
        "intent": "act_as_me",
        "title": "Agent Session Collaboration Patterns",
        "direct_answer": material["headline"],
        "answer_material": material,
        "useful_context": material["talking_points"],
        "behavioral_guidance": guidance,
        "known_limits": material["caveats"],
        "memory_atoms": [],
        "private_trace_refs": trace_refs,
        "topics": topics,
        "updated_at": generated_at,
        "retrieval_text": "\n".join(
            [
                "Intent: act_as_me",
                "Section: Agent Session Collaboration Patterns",
                f"Topics: {', '.join(topics)}",
                f"Provider mix: {provider_text}",
                "Signal counts:",
                *[f"- {item}" for item in signal_text],
                "Collaboration guidance:",
                *[f"- {item}" for item in guidance],
                "Known limits:",
                *[f"- {item}" for item in material["caveats"]],
            ]
        ).strip(),
    }


def dedupe_packs(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted({pack["id"]: pack for pack in packs}.values(), key=lambda row: (row["intent"], row["id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    generated_at = now_iso()
    derived = ledger / "derived"
    atoms = read_jsonl(derived / "memory_atoms.jsonl")
    self_model = read_json(derived / "self_model.json")
    atom_by_id = {atom["id"]: atom for atom in atoms}

    packs = []

    for source_file in ["architecture_material.jsonl", "release_activity.jsonl", "portfolio_cases.jsonl"]:
        for row in read_jsonl(ledger / "sources" / source_file):
            pack = project_source_pack(row, generated_at)
            if pack:
                packs.append(pack)

    for row in read_jsonl(ledger / "sources" / "personal_material.jsonl"):
        pack = personal_material_pack(row, generated_at)
        if pack:
            packs.append(pack)

    agent_pack = agent_sessions_pack(read_jsonl(ledger / "sources" / "agent_sessions.jsonl"), generated_at)
    if agent_pack:
        packs.append(agent_pack)

    sections = self_model.get("sections", []) if isinstance(self_model.get("sections"), list) else []
    section_order = {section_id: index for index, section_id in enumerate(CANONICAL_SECTION_IDS)}
    sections = sorted(
        sections,
        key=lambda section: (
            section_order.get(str(section.get("id", "")), 999),
            str(section.get("id", "")),
        ),
    )
    for section in sections:
        pack = pack_for_section(section, atom_by_id, generated_at)
        if pack:
            packs.append(pack)

    for atom in atoms:
        if should_pack_atom(atom):
            packs.append(pack_for_atom(atom, generated_at))

    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for atom in atoms:
        for topic in atom.get("topics", []):
            by_topic[str(topic)].append(atom)
    for topic, topic_atoms in sorted(by_topic.items()):
        if topic in SKIP_TOPIC_PACKS:
            continue
        if len(topic_atoms) >= 2:
            packs.append(pack_for_topic(topic, topic_atoms, generated_at))

    packs = dedupe_packs(packs)
    write_jsonl(derived / "context_packs.jsonl", packs)
    manifest = {
        "generated_at": generated_at,
        "ledger": str(ledger),
        "architecture": "self-context-v2.8",
        "memory_atoms": len(atoms),
        "context_packs": len(packs),
        "memory_graph_edges": len(self_model.get("memory_graph_edges", [])),
        "persona_sections": len(sections),
        "intent_counts": dict(sorted({intent: sum(1 for pack in packs if pack["intent"] == intent) for intent in {pack["intent"] for pack in packs}}.items())),
    }
    write_json(derived / "context_packs_manifest.json", manifest)

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"context_packs={len(packs)} memory_atoms={len(atoms)} ledger={ledger}")


if __name__ == "__main__":
    main()
