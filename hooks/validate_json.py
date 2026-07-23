#!/usr/bin/env python3
"""Validate knowledge article JSON files.

Usage:
    python hooks/validate_json.py <path> [path ...]

Each path can be a single JSON file, a directory, or a glob pattern (e.g. "knowledge/articles/*.json").
Exit 0 if all files pass validation, exit 1 with error details otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REQUIRED_FIELDS: Dict[str, type] = {
    "id": str,
    "title": str,
    "source": str,
    "source_url": str,
    "summary": str,
    "tags": list,
    "status": str,
    "fetched_at": str,
}

ID_PATTERN = re.compile(r"^(github|rss|hackernews)-\d{8}-[\w-]+$")

VALID_STATUSES = frozenset({"draft", "review", "published", "archived", "error"})

URL_PATTERN = re.compile(r"^https?://")

VALID_AUDIENCES = frozenset({"beginner", "intermediate", "advanced"})

SUMMARY_MIN_LEN = 20
TAGS_MIN_COUNT = 2
SCORE_MIN = 1
SCORE_MAX = 10


def resolve_paths(args: List[str]) -> List[Path]:
    paths: List[Path] = []
    for arg in args:
        p = Path(arg)
        if "*" in arg or "?" in arg or "[" in arg:
            matched = sorted(Path(".").glob(arg))
            if not matched:
                print(f"Warning: glob pattern '{arg}' matched no files", file=sys.stderr)
            paths.extend(matched)
        elif p.is_dir():
            paths.extend(sorted(p.glob("*.json")))
        elif p.is_file():
            paths.append(p)
        else:
            print(f"Warning: '{arg}' not found, skipping", file=sys.stderr)
    return paths


def check_field_type(value: Any, expected: type, field: str) -> List[str]:
    errors: List[str] = []
    if not isinstance(value, expected):
        errors.append(f"  Field '{field}': expected {expected.__name__}, got {type(value).__name__}")
    elif expected is list and isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            errors.append(f"  Field '{field}': list must contain only strings")
    return errors


def validate_file(filepath: Path) -> List[str]:
    file_errors: List[str] = []
    label = f"[{filepath}]"

    try:
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [f"{label} File is not valid UTF-8"]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return [f"{label} Invalid JSON: {exc}"]

    if not isinstance(data, dict):
        return [f"{label} Root must be a JSON object, got {type(data).__name__}"]

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in data:
            file_errors.append(f"  Missing required field: '{field}'")
        elif data[field] is None:
            file_errors.append(f"  Field '{field}' is null, expected {expected_type.__name__}")
        else:
            file_errors.extend(check_field_type(data[field], expected_type, field))

    if "id" in data and isinstance(data.get("id"), str):
        if not ID_PATTERN.match(data["id"]):
            file_errors.append(
                f"  Field 'id': invalid format '{data['id']}', "
                f"expected {{source}}-{{YYYYMMDD}}-{{slug}}"
            )

    if "status" in data and isinstance(data.get("status"), str) and data["status"] not in VALID_STATUSES:
        file_errors.append(
            f"  Field 'status': invalid value '{data['status']}', "
            f"must be one of {sorted(VALID_STATUSES)}"
        )

    if "source_url" in data and isinstance(data.get("source_url"), str):
        if not URL_PATTERN.search(data["source_url"]):
            file_errors.append(f"  Field 'source_url': invalid URL '{data['source_url']}'")

    if "summary" in data and isinstance(data.get("summary"), str):
        if len(data.get("summary", "").strip()) < SUMMARY_MIN_LEN:
            file_errors.append(
                f"  Field 'summary': too short ({len(data['summary'])} chars), "
                f"minimum {SUMMARY_MIN_LEN}"
            )

    if "tags" in data and isinstance(data.get("tags"), list):
        if len(data["tags"]) < TAGS_MIN_COUNT:
            file_errors.append(f"  Field 'tags': must have at least {TAGS_MIN_COUNT} tag(s)")

    if "score" in data and data["score"] is not None:
        score = data["score"]
        if isinstance(score, (int, float)):
            if not (SCORE_MIN <= score <= SCORE_MAX):
                file_errors.append(f"  Field 'score': value {score} out of range [{SCORE_MIN}, {SCORE_MAX}]")
        else:
            file_errors.append(f"  Field 'score': expected number, got {type(score).__name__}")

    if "audience" in data and data.get("audience") is not None:
        audience = data["audience"]
        if isinstance(audience, str) and audience not in VALID_AUDIENCES:
            file_errors.append(
                f"  Field 'audience': invalid value '{audience}', "
                f"must be one of {sorted(VALID_AUDIENCES)}"
            )

    if "published_at" in data and data.get("published_at") is not None:
        if not isinstance(data["published_at"], str):
            file_errors.append(
                f"  Field 'published_at': expected string, got {type(data['published_at']).__name__}"
            )

    if "analyzed_at" in data and data.get("analyzed_at") is not None:
        if not isinstance(data["analyzed_at"], str):
            file_errors.append(
                f"  Field 'analyzed_at': expected string, got {type(data['analyzed_at']).__name__}"
            )

    if "metrics" in data and data.get("metrics") is not None and not isinstance(data["metrics"], dict):
        file_errors.append(f"  Field 'metrics': expected object, got {type(data['metrics']).__name__}")

    if file_errors:
        file_errors.insert(0, label)

    return file_errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python hooks/validate_json.py <path> [path ...]", file=sys.stderr)
        return 1

    filepaths = resolve_paths(sys.argv[1:])
    if not filepaths:
        print("No JSON files found to validate.")
        return 1

    total_errors = 0
    passed = 0
    failed = 0

    for filepath in filepaths:
        errors = validate_file(filepath)
        if errors:
            for line in errors:
                print(line)
            total_errors += len([e for e in errors if e.startswith("  ")])
            failed += 1
        else:
            passed += 1

    print()
    print(f"Files checked: {len(filepaths)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Errors: {total_errors}")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
