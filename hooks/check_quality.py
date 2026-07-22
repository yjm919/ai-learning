#!/usr/bin/env python3
"""Score knowledge articles across 5 quality dimensions.

Usage:
    python hooks/check_quality.py <path> [path ...]

Each path can be a single JSON file, a directory, or a glob pattern
(e.g. "knowledge/articles/*.json").

Dimensions (weighted total 100):
    summary_quality : 25  — length, tech keyword density
    tech_depth      : 25  — mapped from article "score" field (1–10 → 0–25)
    format_spec     : 20  — id, title, source_url, status, timestamps (4 pts each)
    tag_precision   : 15  — count in range, well-known tag vocabulary
    filler_penalty  : 15  — absence of hollow buzzwords (CN + EN blacklists)

Grade cutoffs: A ≥ 80, B ≥ 60, C < 60.  Exit 1 if any file scores C.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Blacklists
# ---------------------------------------------------------------------------

CN_FILLER: List[str] = [
    "赋能", "抓手", "闭环", "打通", "全链路",
    "底层逻辑", "颗粒度", "对齐", "拉通", "沉淀",
    "强大的", "革命性的",
]

EN_FILLER: List[str] = [
    "groundbreaking", "revolutionary", "game-changing", "cutting-edge",
    "best-in-class", "world-class", "state-of-the-art", "unprecedented",
    "paradigm-shifting", "disruptive",
]

FILLER_PATTERN = re.compile(
    "|".join(re.escape(w) for w in CN_FILLER + EN_FILLER),
    re.IGNORECASE,
)

# Well-known, legitimate tags to reward precision.
STANDARD_TAGS: frozenset[str] = frozenset({
    "llm", "agent", "rag", "workflow", "multi-agent", "tool-calling",
    "mcp", "fine-tuning", "python", "typescript", "rust", "go",
    "self-hosted", "cloud", "cli", "web", "api", "open-source",
    "chatbot", "embedding", "vector-db", "prompt-engineering",
    "evaluation", "observability", "security", "vision",
    "speech", "code-generation", "search", "crawler", "gateway",
    "ai", "ai-agent", "ai-coding", "machine-learning",
})

TECH_KEYWORDS_PATTERN = re.compile(
    r"(?i)\b(?:"
    r"llm|agent|rag|fine.?tun|model|transformer|embedding|vector|"
    r"prompt|chain|graph|workflow|langchain|langgraph|mcp|tool|"
    r"openai|claude|gemini|deepseek|llama|qwen|"
    r"retrieval|generation|inference|training|deploy|"
    r"token|context|benchmark|evaluation|"
    r"python|rust|typescript|golang"
    r")\b",
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DimensionScore:
    name: str
    max_points: int
    earned: int = 0
    detail: str = ""


@dataclass
class QualityReport:
    filepath: Path
    title: str = ""
    dimensions: List[DimensionScore] = field(default_factory=list)
    total: int = 0
    grade: str = "C"
    error: Optional[str] = None

    @property
    def max_total(self) -> int:
        return sum(d.max_points for d in self.dimensions)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def bar(earned: int, max_pts: int, width: int = 20) -> str:
    filled = round(earned / max_pts * width) if max_pts else 0
    return "█" * filled + "░" * (width - filled)


def grade_label(total: int) -> str:
    if total >= 80:
        return "A"
    if total >= 60:
        return "B"
    return "C"


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------

def score_summary_quality(data: Dict[str, Any]) -> DimensionScore:
    d = DimensionScore(name="摘要质量", max_points=25)
    summary = data.get("summary", "")
    if not isinstance(summary, str):
        d.detail = "summary 非字符串"
        return d
    length = len(summary.strip())
    if length >= 50:
        d.earned = 25
        d.detail = f"{length} 字 (满分)"
    elif length >= 20:
        d.earned = 15
        d.detail = f"{length} 字 (基本及格)"
    else:
        d.earned = 5
        d.detail = f"{length} 字 (过短)"

    tech_matches = TECH_KEYWORDS_PATTERN.findall(summary)
    if tech_matches:
        bonus = min(len(tech_matches), 5)
        d.earned = min(d.earned + bonus, d.max_points)
        d.detail += f", 技术词 x{len(tech_matches)} (+{bonus})"
    return d


def score_tech_depth(data: Dict[str, Any]) -> DimensionScore:
    d = DimensionScore(name="技术深度", max_points=25)
    score = data.get("score")
    if score is None:
        d.detail = "无 score 字段"
        return d
    if not isinstance(score, (int, float)):
        d.detail = "score 非数值"
        return d
    clamped = max(1, min(10, int(score)))
    d.earned = round((clamped - 1) / 9 * 25)
    d.detail = f"score={clamped} → {d.earned}/{d.max_points}"
    return d


def score_format_spec(data: Dict[str, Any]) -> DimensionScore:
    d = DimensionScore(name="格式规范", max_points=20, detail="")
    checks: List[tuple[str, bool]] = [
        ("id", isinstance(data.get("id"), str) and bool(data["id"].strip())),
        ("title", isinstance(data.get("title"), str) and bool(data["title"].strip())),
        ("source_url", isinstance(data.get("source_url"), str) and data["source_url"].startswith("http")),
        ("status", data.get("status") in {"draft", "review", "published", "archived"}),
        ("timestamps", isinstance(data.get("fetched_at"), str) and bool(data["fetched_at"].strip())),
    ]
    pts_each = d.max_points // len(checks)
    for name, ok in checks:
        if ok:
            d.earned += pts_each
        else:
            part = f"  ✗ {name}" if not d.detail else f", {name}"
            d.detail += part
    if d.earned == d.max_points:
        d.detail = "全部通过"
    elif d.detail:
        d.detail = "缺失:" + d.detail
    return d


def score_tag_precision(data: Dict[str, Any]) -> DimensionScore:
    d = DimensionScore(name="标签精度", max_points=15)
    tags = data.get("tags")
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        d.detail = "tags 格式错误"
        return d
    count = len(tags)
    if 2 <= count <= 5:
        d.earned += 10
    elif count == 1:
        d.earned += 5
        d.detail = "仅 1 个标签"
    elif count > 5:
        d.earned += 8
    else:
        d.detail = "无标签"

    known = sum(1 for t in tags if t.lower() in STANDARD_TAGS)
    if known:
        d.earned += known * 1
    d.earned = min(d.earned, d.max_points)
    if not d.detail:
        d.detail = f"{count} 个标签, {known} 个标准词"
    else:
        d.detail += f", {known} 个标准词"
    return d


def score_filler_penalty(data: Dict[str, Any]) -> DimensionScore:
    d = DimensionScore(name="空洞词检测", max_points=15, earned=15)
    fields_to_scan = [
        str(data.get("title", "")),
        str(data.get("summary", "")),
        str(data.get("summary_en", "")),
    ]
    hits: List[str] = []
    for field_text in fields_to_scan:
        for m in FILLER_PATTERN.finditer(field_text):
            hits.append(m.group())
    if hits:
        penalty = min(len(hits) * 3, d.max_points)
        d.earned = d.max_points - penalty
        d.detail = f"命中 {len(hits)} 个空洞词: {', '.join(set(hits))}"
    else:
        d.detail = "未命中空洞词"
    return d


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def assess_quality(filepath: Path) -> QualityReport:
    report = QualityReport(filepath=filepath)

    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        report.error = f"文件无法解析: {exc}"
        return report

    if not isinstance(data, dict):
        report.error = "根元素不是 JSON 对象"
        return report

    report.title = str(data.get("title", filepath.name))

    scorers = [
        score_summary_quality,
        score_tech_depth,
        score_format_spec,
        score_tag_precision,
        score_filler_penalty,
    ]
    for scorer in scorers:
        report.dimensions.append(scorer(data))

    report.total = sum(d.earned for d in report.dimensions)
    report.grade = grade_label(report.total)
    return report


def print_report(report: QualityReport) -> None:
    title = report.title or report.filepath.name
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print(f"  {report.filepath}")
    print(f"{'=' * 62}")

    if report.error:
        print(f"  ERROR: {report.error}")
        print(f"{'=' * 62}")
        return

    for d in report.dimensions:
        b = bar(d.earned, d.max_points)
        print(f"  {d.name:　<6s}  {b}  {d.earned:>2d}/{d.max_points}  {d.detail}")

    grade_color = {"A": "A", "B": "B", "C": "C"}
    overall_bar = bar(report.total, report.max_total)
    print(f"  {'─' * 54}")
    print(f"  {'总计':　<6s}  {overall_bar}  {report.total:>2d}/{report.max_total}  等级 {report.grade}")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python hooks/check_quality.py <path> [path ...]", file=sys.stderr)
        return 1

    filepaths = resolve_paths(sys.argv[1:])
    if not filepaths:
        print("No JSON files found.", file=sys.stderr)
        return 1

    reports: List[QualityReport] = []
    for i, fp in enumerate(filepaths, 1):
        print(f"\r处理中... [{i}/{len(filepaths)}]", end="", flush=True)
        reports.append(assess_quality(fp))
    print()

    totals: Dict[str, int] = {"A": 0, "B": 0, "C": 0}
    has_c = False
    for report in reports:
        print_report(report)
        totals[report.grade] += 1
        if report.grade == "C":
            has_c = True

    print(f"\n{'=' * 62}")
    print(f"  汇总: {len(reports)} 篇   A: {totals['A']}   B: {totals['B']}   C: {totals['C']}")
    print(f"{'=' * 62}")

    return 1 if has_c else 0


if __name__ == "__main__":
    sys.exit(main())
