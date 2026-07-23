#!/usr/bin/env python3
"""One-shot migration: fix existing article IDs and scores to match new schema.

- ID: {YYYYMMDD}-{source}-{slug}  →  {source}-{YYYYMMDD}-{slug}
- score: 0–100  →  clamp to 1–10
- Rename JSON file to match new ID.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ARTICLES_DIR = Path(__file__).resolve().parent.parent / "knowledge" / "articles"


def normalize_score(raw: int) -> int:
    return max(1, min(10, round(raw / 10)))


def migrate_file(path: Path) -> bool:
    """Fix a single article file in-place. Returns True if changed."""
    data = json.loads(path.read_text(encoding="utf-8"))

    old_id = data.get("id", "")
    changed = False

    # Fix ID: "20260722-github-foo" → "github-20260722-foo"
    parts = old_id.split("-", 2)
    if len(parts) == 3 and parts[0].isdigit() and len(parts[0]) == 8:
        new_id = f"{parts[1]}-{parts[0]}-{parts[2]}"
        data["id"] = new_id
        changed = True

    # Fix score: 0–100 → 1–10
    raw_score = data.get("score")
    if isinstance(raw_score, (int, float)):
        normalized = normalize_score(int(raw_score))
        if normalized != raw_score:
            data["score"] = normalized
            changed = True

    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # Rename file if ID changed
        new_path = path.parent / f"{data['id']}.json"
        if new_path != path:
            path.rename(new_path)
            print(f"  {path.name}  →  {new_path.name}  (score: {data['score']})")
        else:
            print(f"  {path.name}  score → {data['score']}")
    return changed


def main() -> int:
    if not ARTICLES_DIR.is_dir():
        print(f"Articles dir not found: {ARTICLES_DIR}", file=sys.stderr)
        return 1

    files = sorted(ARTICLES_DIR.glob("*.json"))
    if not files:
        print("No article files found.")
        return 0

    migrated = 0
    for f in files:
        try:
            if migrate_file(f):
                migrated += 1
        except Exception as exc:
            print(f"  SKIP {f.name}: {exc}")

    print(f"\nMigrated {migrated}/{len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
