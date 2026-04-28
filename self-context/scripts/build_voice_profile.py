#!/usr/bin/env python3
"""Build a deterministic work-voice profile and evaluate voice-native self-context output."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


VOICE_BANNED_PHRASES = [
    "raw source evidence supports",
    "raw work evidence supports",
    "this supports",
    "this gives him",
    "common implementation surfaces",
    "the useful memory is",
]

LOW_SIGNAL_EXACT = {
    "lgtm",
    "should be",
}

SOURCE_ID_PATTERNS = [
    re.compile(r"\b[A-Z]{2,}-\d+\b"),
    re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE),
    re.compile(r"\b(?:git_commit|pull_request|pull_request_review|jira_[a-z_]+|github_[a-z_]+|code_style_signal):[^\s]+"),
]

MENTION_PATTERN = re.compile(r"@[A-Za-z0-9._-]+")
TOKEN_PATTERN = re.compile(r"[a-z][a-z0-9_+-]*", re.IGNORECASE)
PUNCT_PATTERN = re.compile(r"[^a-z0-9\s]+", re.IGNORECASE)

DIRECTIVE_STARTS = (
    "start by",
    "state",
    "call out",
    "keep",
    "ask before",
    "prefer",
    "choose",
    "treat",
    "frame",
    "model",
    "carry",
    "reproduce",
    "match",
    "preserve",
    "bias",
    "leave",
    "use",
    "answer",
)

LIMIT_STARTS = (
    "do not",
    "don't",
    "never",
    "avoid",
)

ASK_STARTS = (
    "ask before",
    "ask",
    "confirm",
)

EVIDENCE_STYLE_STARTS = (
    "this ",
    "these ",
    "this supports",
    "this gives",
    "this memory",
    "common implementation surfaces",
    "the useful memory",
    "he is not only",
    "his ",
    "he ",
)

IDENTITY_STARTS = (
    "example user is",
    "example user writes",
    "example user makes",
    "example user behaves",
    "example user shows",
    "example user's ",
)

DOMAIN_HINTS = {
    "recruiting",
    "candidate",
    "assessment",
    "employee",
    "learning",
    "analytics",
    "reporting",
    "workflow",
    "admin",
    "product",
    "role",
}


def compact_list(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = normalize_sentence(value)
        if not text:
            continue
        key = sentence_key(text)
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


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


def normalize_sentence(text: Any) -> str:
    value = "" if text is None else str(text)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = MENTION_PATTERN.sub("", value)
    value = re.sub(r"`+", "", value)
    value = re.sub(r"\s+", " ", value).strip(" -:;,./\n\t")
    return value.strip()


def sentence_key(text: str) -> str:
    cleaned = PUNCT_PATTERN.sub(" ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def sentence_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in TOKEN_PATTERN.finditer(text):
        token = match.group(0).lower()
        for suffix in ["ing", "ed", "es", "s"]:
            if len(token) > len(suffix) + 3 and token.endswith(suffix):
                token = token[: -len(suffix)]
                break
        tokens.add(token)
    return tokens


def is_source_identifier(text: str) -> bool:
    return any(pattern.search(text) for pattern in SOURCE_ID_PATTERNS)


def looks_low_signal(text: str) -> bool:
    lowered = sentence_key(text)
    if not lowered or lowered in LOW_SIGNAL_EXACT:
        return True
    tokens = list(sentence_tokens(lowered))
    if len(tokens) < 4:
        return True
    if all(token in {"qa", "fix", "update", "updated", "follow", "up"} for token in tokens):
        return True
    return False


def looks_long_form(text: str) -> bool:
    lowered = text.lower()
    return len(text) >= 140 or any(
        phrase in lowered
        for phrase in [
            "impact assessment",
            "qa impact",
            "affected routes",
            "recommended test scenarios",
            "manual deploy",
            "feature flag",
            "risk areas",
            "impact analysis report",
            "migration",
        ]
    )


def classify_sentence(text: str) -> str:
    lowered = sentence_key(text)
    if any(lowered.startswith(prefix) for prefix in LIMIT_STARTS):
        return "limit"
    if any(lowered.startswith(prefix) for prefix in ASK_STARTS):
        return "ask"
    if any(lowered.startswith(prefix) for prefix in EVIDENCE_STYLE_STARTS):
        return "evidence"
    if any(lowered.startswith(prefix) for prefix in IDENTITY_STARTS):
        return "identity"
    if lowered.startswith("i "):
        return "rule"
    if any(lowered.startswith(prefix) for prefix in DIRECTIVE_STARTS):
        return "rule"
    if sentence_tokens(lowered) & DOMAIN_HINTS:
        return "domain"
    if lowered.startswith(("when ", "for ", "in ")):
        return "rule"
    return "rule"


def is_banned_sentence(text: str) -> bool:
    lowered = sentence_key(text)
    if not lowered or looks_low_signal(lowered):
        return True
    if is_source_identifier(text):
        return True
    if any(phrase in lowered for phrase in VOICE_BANNED_PHRASES):
        return True
    if lowered.startswith("description ") or lowered.startswith("branch ") or lowered.startswith("commit "):
        return True
    return False


def is_near_duplicate(left: str, right: str) -> bool:
    left_key = sentence_key(left)
    right_key = sentence_key(right)
    if left_key == right_key:
        return True
    left_tokens = sentence_tokens(left_key)
    right_tokens = sentence_tokens(right_key)
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens) / max(1, min(len(left_tokens), len(right_tokens)))
    return overlap >= 0.7


def filter_sentences(
    values: list[str],
    *,
    limit: int,
    allowed_types: set[str] | None = None,
    ban_third_person: bool = False,
) -> list[str]:
    output: list[str] = []
    for raw in values:
        text = normalize_sentence(raw)
        if is_banned_sentence(text):
            continue
        sentence_type = classify_sentence(text)
        if allowed_types and sentence_type not in allowed_types:
            continue
        lowered = sentence_key(text)
        if ban_third_person and (
            lowered.startswith(("he ", "his ", "example user ", "example user's "))
            or " for him " in f" {lowered} "
            or " his " in f" {lowered} "
            or sentence_type == "evidence"
        ):
            continue
        if any(is_near_duplicate(text, existing) for existing in output):
            continue
        output.append(text)
        if len(output) >= limit:
            break
    return output


def is_first_person_or_directive(text: str) -> bool:
    lowered = sentence_key(text)
    return lowered.startswith("i ") or any(lowered.startswith(prefix) for prefix in DIRECTIVE_STARTS)


def build_voice_profile(ledger: Path, generated_at: str) -> dict[str, Any]:
    rows = read_jsonl(ledger / "sources" / "jira_comments.jsonl")
    authored_rows = 0
    retained_rows = 0
    long_form_rows = 0
    retained_samples: list[str] = []
    long_form_samples: list[str] = []

    for row in rows:
        raw = row.get("raw_excerpt") if isinstance(row.get("raw_excerpt"), dict) else {}
        if not raw.get("authored_by_user"):
            continue
        authored_rows += 1
        source_text = normalize_sentence(raw.get("body_excerpt") or row.get("summary"))
        if is_banned_sentence(source_text):
            continue
        retained_rows += 1
        retained_samples.append(source_text)
        if looks_long_form(source_text):
            long_form_rows += 1
            long_form_samples.append(source_text)

    corpus = " ".join(retained_samples).lower()
    preferred_constraints = [
        "Call out standards explicitly when something should follow an existing pattern.",
        "State QA impact, affected surface, and verification needs before closing the loop.",
        "Say when manual deploy, feature flag, or rollout coordination is required.",
        "Keep updates scoped to impact, next action, and readiness.",
    ]
    if "manual deploy" not in corpus and "feature flag" not in corpus:
        preferred_constraints = preferred_constraints[:-1]

    profile = {
        "generated_at": generated_at,
        "architecture": "self-context-v2.8",
        "tone_rules": [
            "Use direct, execution-oriented engineering language.",
            "Lead with impact, constraints, and the next required action.",
            "Keep sentences short, scoped, and easy for QA or the next actor to apply.",
        ],
        "directive_patterns": [
            "Start by stating the affected workflow, contract edge, or release surface.",
            "Call out standards, blockers, and rollout requirements explicitly.",
            "Ask before acting when deploy, QA, feature flag, or approval context is unclear.",
        ],
        "preferred_openings": ["Start by", "State", "Call out", "Keep", "Ask before"],
        "preferred_constraints": preferred_constraints,
        "banned_phrases": VOICE_BANNED_PHRASES,
        "source_stats": {
            "authored_rows": authored_rows,
            "retained_rows": retained_rows,
            "long_form_rows": long_form_rows,
            "discarded_rows": max(0, authored_rows - retained_rows),
        },
        "retained_examples": compact_list(retained_samples, 5),
        "long_form_examples": compact_list(long_form_samples, 3),
    }
    return profile


def build_voice_style_eval(
    sections: list[dict[str, Any]],
    agent_operating_context: dict[str, Any],
    voice_profile: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    list_fields = [
        "preferred_work_style",
        "decision_rules",
        "quality_non_negotiables",
        "domain_biases",
        "unsafe_assumptions",
        "ask_before_acting",
        "proof_policy",
        "topics",
        "source_sections",
    ]
    content_list_fields = [
        "preferred_work_style",
        "decision_rules",
        "quality_non_negotiables",
        "domain_biases",
        "unsafe_assumptions",
        "ask_before_acting",
        "proof_policy",
    ]
    agent_text_fields = [str(agent_operating_context.get("operating_summary", ""))]
    for field in list_fields:
        value = agent_operating_context.get(field, [])
        if isinstance(value, list):
            agent_text_fields.extend(str(item) for item in value)

    banned_hits = [
        phrase
        for phrase in VOICE_BANNED_PHRASES
        if any(phrase in sentence_key(text) for text in agent_text_fields)
    ]
    duplicates: list[str] = []
    seen: list[str] = []
    duplicate_candidates = [str(agent_operating_context.get("operating_summary", ""))]
    for field in content_list_fields:
        duplicate_candidates.extend(str(item) for item in agent_operating_context.get(field, []))
    for text in duplicate_candidates:
        normalized = normalize_sentence(text)
        if not normalized:
            continue
        if any(is_near_duplicate(normalized, prior) for prior in seen):
            duplicates.append(normalized)
        else:
            seen.append(normalized)

    summary = str(agent_operating_context.get("operating_summary", ""))
    summary_sentences = [segment.strip() for segment in re.split(r"[.!?]+", summary) if segment.strip()]
    master_section = next((section for section in sections if section.get("id") == "self_model:master_persona"), {})
    master_summary = str(master_section.get("summary", ""))
    section_texts = [
        str(section.get("summary", ""))
        for section in sections
        if str(section.get("id", "")) != "self_model:agent_operating_context"
    ]
    section_texts.extend(
        str(item)
        for section in sections
        if str(section.get("id", "")) != "self_model:agent_operating_context"
        for field in ["practical_guidance", "decision_biases", "known_limits"]
        for item in section.get(field, [])
    )

    checks = {
        "authored_rows_present": {
            "passes": int(voice_profile.get("source_stats", {}).get("authored_rows", 0) or 0) > 0,
            "count": int(voice_profile.get("source_stats", {}).get("authored_rows", 0) or 0),
        },
        "voice_profile_seed_present": {
            "passes": bool(voice_profile.get("preferred_openings")) and bool(voice_profile.get("preferred_constraints")),
        },
        "agent_summary_short": {
            "passes": 1 <= len(summary_sentences) <= 2,
            "count": len(summary_sentences),
        },
        "agent_summary_directive": {
            "passes": is_first_person_or_directive(summary),
            "summary": summary,
        },
        "agent_lists_short": {
            "passes": all(3 <= len(agent_operating_context.get(field, [])) <= 5 for field in list_fields),
            "details": {
                field: len(agent_operating_context.get(field, [])) if isinstance(agent_operating_context.get(field), list) else 0
                for field in list_fields
            },
        },
        "agent_banned_phrases_removed": {
            "passes": not banned_hits,
            "hits": banned_hits,
        },
        "agent_duplicates_removed": {
            "passes": not duplicates,
            "hits": compact_list(duplicates, 12),
        },
        "master_persona_third_person": {
            "passes": sentence_key(master_summary).startswith("example user "),
            "summary": master_summary,
        },
        "sections_decontaminated": {
            "passes": not any(any(phrase in sentence_key(text) for phrase in VOICE_BANNED_PHRASES) for text in section_texts),
        },
    }
    passes = all(bool(item.get("passes")) for item in checks.values())
    return {
        "generated_at": generated_at,
        "architecture": "self-context-v2.8",
        "voiceProfileReady": checks["authored_rows_present"]["passes"] and checks["voice_profile_seed_present"]["passes"],
        "voiceStyleReady": passes,
        "source_stats": voice_profile.get("source_stats", {}),
        "checks": checks,
        "passes": passes,
    }
