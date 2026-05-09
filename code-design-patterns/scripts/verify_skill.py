#!/usr/bin/env python3
"""Verify code-design-patterns skill coverage and source alignment."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PATTERNS = [
    "Factory Method",
    "Abstract Factory",
    "Builder",
    "Prototype",
    "Singleton",
    "Adapter",
    "Bridge",
    "Composite",
    "Decorator",
    "Facade",
    "Flyweight",
    "Proxy",
    "Chain of Responsibility",
    "Command",
    "Iterator",
    "Mediator",
    "Memento",
    "Observer",
    "State",
    "Strategy",
    "Template Method",
    "Visitor",
]

FOUNDATION_TERMS = [
    "Abstraction",
    "Encapsulation",
    "Inheritance",
    "Polymorphism",
    "Encapsulate What Varies",
    "Program To An Interface",
    "Favor Composition Over Inheritance",
    "Single Responsibility",
    "Open/Closed",
    "Liskov",
    "Interface Segregation",
    "Dependency Inversion",
    "Dependency",
    "Association",
    "Aggregation",
    "Composition",
    "Implementation",
]

EXPECTED_PDF_OUTLINE = [
    "Introduction to OOP",
    "Relations Between Objects",
    "Introduction to Design Patterns",
    "Software Design Principles",
    "Design Principles",
    "SOLID Principles",
    "Catalog of Design Patterns",
    "Creational Design Patterns",
    "Structural Design Patterns",
    "Behavioral Design Patterns",
    *PATTERNS,
]

PRIVATE_PATTERNS = [
    ("purchase marker", re.compile(r"Purchased\s+by", re.I)),
    ("purchase id marker", re.compile(r"#\d{5,}")),
    ("email marker", re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")),
]


def normalize(text: str) -> str:
    return text.replace(" Of ", " of ")


def load_texts(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8-sig")
        for path in root.rglob("*.md")
    }


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_skill_files(root: Path, errors: list[str], skip_evals: bool = False) -> None:
    texts = load_texts(root)

    skill = texts.get("SKILL.md", "")
    require(skill.startswith("---\n"), "SKILL.md missing frontmatter", errors)
    require(len(skill.splitlines()) < 500, "SKILL.md should stay under 500 lines", errors)

    required_files = [
        "references/selection-guide.md",
        "references/pattern-catalog.md",
        "references/pattern-anatomy.md",
        "references/code-reference.md",
        "references/pattern-code-sketches.md",
        "references/refactor-playbooks.md",
        "references/design-foundations.md",
        "references/enterprise-review-checklist.md",
        "references/source-alignment.md",
        "evals/evals.json",
    ]
    for filename in required_files:
        require((root / filename).exists(), f"missing {filename}", errors)

    for filename in [
        "references/selection-guide.md",
        "references/pattern-catalog.md",
        "references/pattern-anatomy.md",
    ]:
        text = normalize(texts.get(filename, ""))
        missing = [pattern for pattern in PATTERNS if normalize(pattern) not in text]
        require(not missing, f"{filename} missing patterns: {missing}", errors)

    code_map = normalize(texts.get("references/pattern-code-sketches.md", ""))
    missing_code = [pattern for pattern in PATTERNS if f"| {normalize(pattern)} |" not in code_map]
    require(not missing_code, f"pattern-code-sketches.md missing code routes: {missing_code}", errors)

    foundation = texts.get("references/design-foundations.md", "")
    missing_terms = [term for term in FOUNDATION_TERMS if term not in foundation]
    require(not missing_terms, f"design-foundations.md missing terms: {missing_terms}", errors)

    for filename, text in texts.items():
        if filename == "SKILL.md":
            continue
        if len(text.splitlines()) > 100:
            require("Table Of Contents" in text, f"{filename} over 100 lines without Table Of Contents", errors)

    combined = "\n".join(
        text
        for filename, text in texts.items()
        if filename != "scripts/verify_skill.py"
    )
    leaked = [label for label, pattern in PRIVATE_PATTERNS if pattern.search(combined)]
    require(not leaked, f"private PDF markers leaked into skill: {leaked}", errors)

    evals_path = root / "evals" / "evals.json"
    if skip_evals:
        print("evals/evals.json check skipped by --skip-evals")
    elif evals_path.exists():
        with evals_path.open(encoding="utf-8") as handle:
            evals = json.load(handle)
        require(evals.get("skill_name") == "code-design-patterns", "evals skill_name mismatch", errors)
        require(len(evals.get("evals", [])) >= 12, "expected at least 12 evals", errors)

    ts_violations: list[str] = []
    for filename, text in texts.items():
        for match in re.finditer(r"```ts\n(.*?)\n```", text, re.S):
            code = match.group(1)
            if re.search(r"\bas\s+[A-Z][A-Za-z0-9_<>]*(\b|\[)", code):
                ts_violations.append(f"{filename}: type assertion")
            if re.search(r"[^=!<>]!\.", code):
                ts_violations.append(f"{filename}: non-null property access")
            if "@ts-ignore" in code or re.search(r"\bany\b", code):
                ts_violations.append(f"{filename}: any or ts-ignore")
    require(not ts_violations, f"TypeScript sketch violations: {ts_violations}", errors)


def extract_outline_titles(pdf_path: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise RuntimeError("pypdf is required for --pdf checks") from exc

    reader = PdfReader(str(pdf_path))
    titles: list[str] = []

    def walk(items: list[object]) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item)
            else:
                title = getattr(item, "title", str(item))
                titles.append(title)

    walk(reader.outline)
    return titles


def check_pdf(pdf_path: Path, errors: list[str]) -> None:
    titles = extract_outline_titles(pdf_path)
    title_text = "\n".join(titles)
    missing = [title for title in EXPECTED_PDF_OUTLINE if title not in title_text]
    require(not missing, f"PDF outline missing expected sections: {missing}", errors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--skip-evals", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    check_skill_files(args.root, errors, skip_evals=args.skip_evals)

    if args.pdf:
        check_pdf(args.pdf, errors)

    if errors:
        print("verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
