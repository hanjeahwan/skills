#!/usr/bin/env python3
"""Export Jira Cloud issues as evidence-ledger source JSONL."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_FIELDS = [
    "summary",
    "status",
    "issuetype",
    "priority",
    "created",
    "updated",
    "resolutiondate",
    "labels",
    "components",
    "fixVersions",
    "assignee",
    "reporter",
    "description",
]


def env_value(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value

    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, _ = winreg.QueryValueEx(key, name)
                if value:
                    return str(value)
        except FileNotFoundError:
            pass
        except OSError:
            pass

    raise RuntimeError(f"{name} is not set")


def jira_auth_header(email: str, token: str) -> str:
    raw = f"{email}:{token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def jsonl_dumps(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def jira_get(base_url: str, auth_header: str, path: str, query: dict[str, str | int]) -> dict[str, Any]:
    url = base_url.rstrip("/") + path + "?" + urlencode(query)
    request = Request(url, headers={"Authorization": auth_header, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jira request failed with HTTP {exc.code}: {body}") from exc


def existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()

    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        row_id = row.get("id")
        if isinstance(row_id, str):
            ids.add(row_id)
    return ids


def adf_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""

    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "text" and isinstance(node.get("text"), str):
                parts.append(node["text"])
            for child in node.get("content") or []:
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return " ".join(part.strip() for part in parts if part.strip())


def names(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str):
                result.append(name)
    return result


def user_display(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        "displayName": value.get("displayName") or "",
        "emailAddress": value.get("emailAddress") or "",
        "accountId": value.get("accountId") or "",
    }


def issue_to_raw_evidence(issue: dict[str, Any], base_url: str, now: str) -> dict[str, Any]:
    fields = issue.get("fields") or {}
    key = issue.get("key") or issue.get("id") or ""
    summary = fields.get("summary") or ""
    status = fields.get("status") or {}
    issue_type = fields.get("issuetype") or {}
    priority = fields.get("priority") or {}
    description = adf_text(fields.get("description"))
    labels = fields.get("labels") if isinstance(fields.get("labels"), list) else []
    components = names(fields.get("components"))
    fix_versions = names(fields.get("fixVersions"))

    return {
        "id": f"jira_ticket:{key}",
        "source_type": "jira_ticket",
        "source_id": key,
        "occurred_at": fields.get("created") or fields.get("updated") or "",
        "title": f"{key}: {summary}",
        "summary": summary,
        "url_or_path": f"{base_url.rstrip('/')}/browse/{key}",
        "raw_excerpt": {
            "key": key,
            "issue_id": issue.get("id") or "",
            "status": status.get("name") if isinstance(status, dict) else "",
            "issue_type": issue_type.get("name") if isinstance(issue_type, dict) else "",
            "priority": priority.get("name") if isinstance(priority, dict) else "",
            "created": fields.get("created") or "",
            "updated": fields.get("updated") or "",
            "resolutiondate": fields.get("resolutiondate") or "",
            "labels": labels,
            "components": components,
            "fixVersions": fix_versions,
            "assignee": user_display(fields.get("assignee")),
            "reporter": user_display(fields.get("reporter")),
            "description_excerpt": description[:4000],
        },
        "tags": ["jira", *labels, *components],
        "ingested_at": now,
    }


def export(args: argparse.Namespace) -> None:
    base_url = (args.base_url or env_value("JIRA_BASE_URL")).rstrip("/")
    email = args.email or env_value("JIRA_EMAIL")
    token = env_value("JIRA_API_TOKEN")
    auth_header = jira_auth_header(email, token)

    output_path = Path(args.out).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.replace and output_path.exists():
        output_path.unlink()

    seen = existing_ids(output_path)
    next_page_token = args.next_page_token
    exported = 0
    searched_pages = 0
    now = datetime.now(timezone.utc).isoformat()

    with output_path.open("a", encoding="utf-8") as handle:
        while True:
            query: dict[str, str | int] = {
                "jql": args.jql,
                "maxResults": min(args.page_size, 100),
                "fields": ",".join(args.fields),
            }
            if next_page_token:
                query["nextPageToken"] = next_page_token

            response = jira_get(base_url, auth_header, "/rest/api/3/search/jql", query)
            searched_pages += 1
            issues = response.get("issues") or []
            if not isinstance(issues, list):
                raise RuntimeError("unexpected Jira issues response")

            for issue in issues:
                row = issue_to_raw_evidence(issue, base_url, now)
                if row["id"] in seen:
                    continue
                if args.max_count is not None and exported >= args.max_count:
                    break
                handle.write(jsonl_dumps(row) + "\n")
                handle.flush()
                seen.add(row["id"])
                exported += 1

            if args.max_count is not None and exported >= args.max_count:
                break
            if response.get("isLast") is True:
                break
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

    print(f"exported {exported} new Jira issues to {output_path}")
    print(f"searched {searched_pages} Jira page(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jql", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--base-url", help="Defaults to JIRA_BASE_URL")
    parser.add_argument("--email", help="Defaults to JIRA_EMAIL")
    parser.add_argument("--field", dest="fields", action="append", help="Jira field to request. Can be repeated.")
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--max-count", type=int)
    parser.add_argument("--next-page-token")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if not args.fields:
        args.fields = DEFAULT_FIELDS
    export(args)


if __name__ == "__main__":
    main()
