#!/usr/bin/env python3
"""Build MCP-ready self-context packs from memory atoms."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
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


def pack_for_atom(atom: dict[str, Any], generated_at: str) -> dict[str, Any]:
    memory_type = str(atom.get("memory_type", "self_knowledge"))
    intent = INTENT_BY_MEMORY_TYPE.get(memory_type, "self_knowledge")
    topics = [str(item) for item in atom.get("topics", [])]
    useful_context = [str(item) for item in atom.get("useful_context", [])]
    guardrails = [str(item) for item in atom.get("guardrails", [])]
    statement = str(atom.get("statement", ""))
    behavioral_use = str(atom.get("behavioral_use", "Use this memory as useful personal context."))
    trace_refs = [str(item) for item in atom.get("provenance_refs", [])]

    return {
        "id": atom["id"].replace("memory:", "context:", 1),
        "intent": intent,
        "title": statement[:120],
        "direct_answer": statement,
        "useful_context": compact_list(useful_context or [statement], 10),
        "behavioral_guidance": compact_list([behavioral_use], 5),
        "known_limits": compact_list(guardrails, 8),
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
    contexts = compact_list([str(item) for item in section.get("practical_guidance", [])], 12)
    guardrails = compact_list([str(item) for item in section.get("known_limits", [])], 10)
    trace_refs = compact_list([str(item) for atom in atoms for item in atom.get("provenance_refs", [])], 20)
    title = str(section.get("title") or section_type.replace("_", " ").title())
    behavioral_guidance = compact_list([str(item) for item in section.get("decision_biases", [])], 8)

    return {
        "id": str(section.get("id", f"self_model:{section_type}")).replace("self_model:", "context:self_model.", 1),
        "intent": intent,
        "title": title,
        "direct_answer": str(section.get("summary") or ""),
        "useful_context": contexts,
        "behavioral_guidance": behavioral_guidance
        or [
            "Use this as a high-level self-context summary. Answer with practical context first, not source ids.",
            "If the caller may act for the user, apply the known limits before suggesting actions.",
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
    statements = compact_list((str(atom.get("statement", "")) for atom in atoms), 8)
    contexts = compact_list((item for atom in atoms for item in atom.get("useful_context", [])), 12)
    guardrails = compact_list((item for atom in atoms for item in atom.get("guardrails", [])), 10)
    trace_refs = compact_list((item for atom in atoms for item in atom.get("provenance_refs", [])), 20)
    memory_types = {str(atom.get("memory_type", "")) for atom in atoms}
    intent = TOPIC_INTENT.get(topic, "coding_style" if "coding_style" in memory_types else "self_knowledge")

    return {
        "id": f"context:topic.{topic}",
        "intent": intent,
        "title": topic.replace("_", " ").title(),
        "direct_answer": " ".join(statements[:3]),
        "useful_context": contexts or statements,
        "behavioral_guidance": [
            "Use this topic pack when the query asks about this area of the user's knowledge, behavior, or preference.",
            "Keep evidence and source ids hidden unless proof is explicitly requested.",
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
