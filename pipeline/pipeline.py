from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from model_client import chat_with_retry, get_provider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "knowledge" / "raw"
ARTICLES_DIR = ROOT / "knowledge" / "articles"

# ---------------------------------------------------------------------------
# RSS feed defaults
# ---------------------------------------------------------------------------

DEFAULT_RSS_FEEDS: list[str] = [
    "https://hnrss.org/frontpage?q=ai+OR+llm+OR+agent+OR+ml+OR+openai+OR+deepseek",
    "https://news.ycombinator.com/rss",
]

# ---------------------------------------------------------------------------
# GitHub Search
# ---------------------------------------------------------------------------

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


def _collect_github(limit: int = 20, timeout: float = 30.0) -> list[dict[str, Any]]:
    """Collect trending AI repositories from the GitHub Search API.

    Args:
        limit: Maximum number of results (per_page parameter).
        timeout: HTTP request timeout in seconds.

    Returns:
        List of repo dicts with ``name``, ``url``, ``description``, ``stars``,
        ``language``, ``topics``.

    Raises:
        httpx.HTTPError: On transport or HTTP-level failures.
    """
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    gh_token = os.getenv("GITHUB_TOKEN")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"

    query = "ai+OR+llm+OR+agent"
    url = (
        f"{GITHUB_SEARCH_URL}?q={query}"
        f"&sort=stars&order=desc&per_page={min(limit, 100)}"
    )

    logger.info("Querying GitHub Search API (limit=%d)", limit)
    with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    items: list[dict[str, Any]] = []
    for repo in data.get("items", []):
        items.append(
            {
                "name": repo.get("full_name", ""),
                "url": repo.get("html_url", ""),
                "description": repo.get("description") or "",
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language") or "",
                "topics": repo.get("topics", []),
            }
        )
    logger.info("GitHub Search returned %d repos (requested %d)", len(items), limit)
    return items


# ---------------------------------------------------------------------------
# RSS collection (simple regex parser)
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"</?[^>]+/?>", re.DOTALL)


def _strip_tags(html: str) -> str:
    """Strip HTML/XML tags from a string."""
    return _TAG_RE.sub("", html).strip()


def _collect_rss(
    feed_urls: Optional[list[str]] = None, limit: int = 20, timeout: float = 30.0
) -> list[dict[str, Any]]:
    """Fetch RSS/Atom feeds and extract AI-related items using simple regex.

    Supports both RSS 2.0 ``<item>`` and Atom ``<entry>`` formats.

    Args:
        feed_urls: List of RSS feed URLs. Uses :data:`DEFAULT_RSS_FEEDS` if None.
        limit: Maximum number of items to return across all feeds.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of item dicts with ``name``, ``url``, ``description``.
    """
    urls = feed_urls or DEFAULT_RSS_FEEDS
    items: list[dict[str, Any]] = []

    with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
        for url in urls:
            logger.info("Fetching RSS feed: %s", url)
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("Failed to fetch RSS feed %s: %s", url, exc)
                continue

            text = resp.text
            # Try Atom entries first
            entries = list(re.finditer(r"<entry[>\s](.*?)</entry>", text, re.DOTALL))
            if not entries:
                # Fall back to RSS items
                entries = list(re.finditer(r"<item[>\s](.*?)</item>", text, re.DOTALL))

            for match in entries:
                block = match.group(1)
                title_match = re.search(r"<title[^>]*>(.*?)</title>", block, re.DOTALL)
                link_match = re.search(r'<link[^>]*href="([^"]*)"', block)
                if not link_match:
                    link_match = re.search(r"<link[^>]*>(.*?)</link>", block, re.DOTALL)
                desc_match = re.search(
                    r"<(?:description|summary|content)[^>]*>(.*?)</(?:description|summary|content)>",
                    block,
                    re.DOTALL,
                )

                title = _strip_tags(title_match.group(1)) if title_match else ""
                link = (link_match.group(1) or link_match.group(0)) if link_match else ""
                link = _strip_tags(link)
                description = _strip_tags(desc_match.group(1)) if desc_match else ""

                if not title or not link:
                    continue

                items.append(
                    {
                        "name": title,
                        "url": link,
                        "description": description,
                    }
                )
                if len(items) >= limit:
                    break
            if len(items) >= limit:
                break

    logger.info("RSS collection returned %d items (requested %d)", len(items), limit)
    return items


# ---------------------------------------------------------------------------
# Step 1: Collect
# ---------------------------------------------------------------------------


def collect(
    sources: list[str],
    limit: int = 20,
    dry_run: bool = False,
) -> tuple[list[dict[str, Any]], Optional[Path]]:
    """Collect raw items from specified sources.

    Args:
        sources: List of source identifiers (``github`` and/or ``rss``).
        limit: Maximum items per source.
        dry_run: If True, skip writing raw JSON to disk.

    Returns:
        Tuple of (collected_items, raw_file_path). raw_file_path is None when
        dry_run is True or no items were collected.
    """
    raw_items: list[dict[str, Any]] = []

    if "github" in sources:
        logger.info("Step 1 — Collecting from GitHub...")
        try:
            raw_items.extend(_collect_github(limit=limit))
        except Exception as exc:
            logger.error("GitHub collection failed: %s", exc)

    if "rss" in sources:
        logger.info("Step 1 — Collecting from RSS...")
        try:
            raw_items.extend(_collect_rss(limit=limit))
        except Exception as exc:
            logger.error("RSS collection failed: %s", exc)

    if not raw_items:
        logger.warning("No items collected from sources: %s", sources)
        return raw_items, None

    if dry_run:
        logger.info("[dry-run] Would save %d raw items", len(raw_items))
        return raw_items, None

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw_path = RAW_DIR / f"pipeline-collected-{today}.json"

    payload = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "count": len(raw_items),
        "items": raw_items,
    }
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %d raw items to %s", len(raw_items), raw_path)
    return raw_items, raw_path


# ---------------------------------------------------------------------------
# Step 2: Analyze
# ---------------------------------------------------------------------------


ANALYSIS_SYSTEM_PROMPT = """你是一个技术情报分析助手。对输入的每条 AI/LLM/Agent 相关的技术条目进行分析，返回 JSON。

要求：
1. summary: 中文摘要，≤ 200 字
2. summary_en: 英文摘要
3. tags: 至少 2 个英文标签（小写，用数组表示）
4. score: 0-100 综合评分，基于技术价值与 AI 相关性

仅返回合法 JSON 对象，不要包含任何其他文字。"""


def _build_analysis_prompt(item: dict[str, Any]) -> str:
    """Build a prompt string for a single item to be analyzed."""
    parts = []
    if item.get("name"):
        parts.append(f"项目名称: {item['name']}")
    if item.get("url"):
        parts.append(f"链接: {item['url']}")
    if item.get("description"):
        parts.append(f"描述: {item['description']}")
    if item.get("stars"):
        parts.append(f"Star 数: {item['stars']}")
    if item.get("topics"):
        parts.append(f"Topics: {', '.join(item['topics'])}")
    return "\n".join(parts)


def _normalize_score(raw_score: int) -> int:
    """Normalize a 0–100 score to 1–10.

    Args:
        raw_score: Raw score (typically 0–100 from LLM).

    Returns:
        Normalized score clamped to [1, 10].
    """
    return max(1, min(10, round(raw_score / 10)))


def analyze(
    items: list[dict[str, Any]],
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Analyze collected items using LLM for summary, tags, and scoring.

    Each item is sent to the LLM configured via :mod:`model_client`.
    Retries up to 3 times on failure.

    Args:
        items: Raw items from the collect step.
        dry_run: If True, return mock analysis without calling the LLM.

    Returns:
        List of analyzed article dicts with fields matching the knowledge
        article JSON schema (id, title, source, source_url, summary,
        summary_en, tags, status, score, metrics, fetched_at, analyzed_at).
    """
    if dry_run:
        logger.info("[dry-run] Would analyze %d items via LLM", len(items))
        ts_now = datetime.now(timezone.utc).isoformat()
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return [
            {
                "id": f"{_safe_source(a)}-{date_str}-{_slugify(a.get('name', 'unknown'))}",
                "title": a.get("name", ""),
                "source": _safe_source(a),
                "source_url": a.get("url", ""),
                "summary": f"[dry-run] 模拟摘要: {a.get('description', '')[:100]}",
                "summary_en": f"[dry-run] mock summary for {a.get('name', '')}",
                "tags": ["ai", "dry-run"],
                "status": "draft",
                "score": _normalize_score(int(a.get("stars", 0)) % 100 or 50),
                "metrics": {"stars": a.get("stars", 0)},
                "fetched_at": ts_now,
                "analyzed_at": ts_now,
            }
            for a in items
        ]

    if not items:
        logger.info("No items to analyze")
        return []

    provider = get_provider()
    analyzed: list[dict[str, Any]] = []
    ts_now = datetime.now(timezone.utc)

    for idx, item in enumerate(items):
        name = item.get("name", f"item-{idx}")
        logger.info("Analyzing %d/%d: %s", idx + 1, len(items), name)
        prompt = _build_analysis_prompt(item)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            response = chat_with_retry(
                provider=provider,
                messages=messages,
                temperature=0.5,
                max_tokens=1024,
            )
            result = json.loads(response.content)
        except Exception as exc:
            logger.error("Analysis failed for %s: %s", name, exc)
            analyzed.append(
                {
                    "id": "",
                    "title": name,
                    "source": _safe_source(item),
                    "source_url": item.get("url", ""),
                    "summary": f"分析失败: {exc}",
                    "summary_en": "",
                    "tags": [],
                    "status": "error",
                    "score": 1,
                    "metrics": {},
                    "fetched_at": ts_now.isoformat(),
                    "analyzed_at": ts_now.isoformat(),
                    "error": str(exc),
                }
            )
            continue

        source = _safe_source(item)
        slug = _slugify(name)
        date_str = ts_now.strftime("%Y%m%d")
        article_id = f"{source}-{date_str}-{slug}"

        article: dict[str, Any] = {
            "id": article_id,
            "title": name,
            "source": source,
            "source_url": item.get("url", ""),
            "summary": result.get("summary", ""),
            "summary_en": result.get("summary_en", ""),
            "tags": result.get("tags", []),
            "status": "draft",
            "score": _normalize_score(result.get("score", 0)),
            "metrics": {"stars": item.get("stars", 0)},
            "fetched_at": ts_now.isoformat(),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        analyzed.append(article)
        logger.debug("Analyzed: id=%s score=%d tags=%s", article_id, article["score"], article["tags"])

    provider.close()
    logger.info("Analyzed %d/%d items successfully", sum(1 for a in analyzed if a["status"] != "error"), len(analyzed))
    return analyzed


# ---------------------------------------------------------------------------
# Step 3: Organize
# ---------------------------------------------------------------------------


def organize(articles: list[dict[str, Any]], dry_run: bool = False) -> list[dict[str, Any]]:
    """Organize analyzed articles: deduplicate, validate, sort by score.

    Deduplication rule: same ``source_url`` → keep the one with higher score.

    Args:
        articles: Analyzed article dicts from the analyze step.
        dry_run: If True, skip validation and just report what would be done.

    Returns:
        Deduplicated, validated list of articles sorted by score descending.
    """
    if dry_run:
        logger.info("[dry-run] Would deduplicate & validate %d articles", len(articles))
        return articles

    if not articles:
        logger.info("No articles to organize")
        return []

    # Dedup by source_url, keep highest score
    seen: dict[str, dict[str, Any]] = {}
    for art in articles:
        url = art.get("source_url", "")
        if url not in seen or art.get("score", 0) > seen[url].get("score", 0):
            seen[url] = art

    deduped = list(seen.values())
    logger.info(
        "Organize: %d articles → %d after dedup (removed %d)",
        len(articles),
        len(deduped),
        len(articles) - len(deduped),
    )

    # Validate required fields, mark invalid as error
    required_fields = {"id", "title", "source", "source_url", "summary", "tags", "status", "fetched_at"}
    valid: list[dict[str, Any]] = []
    for art in deduped:
        missing = required_fields - set(art.keys())
        if missing:
            logger.warning("Article %s missing required fields: %s — marking as error", art.get("id", "?"), missing)
            art["status"] = "error"
        if art.get("status") == "error":
            valid.append(art)
            continue
        if not isinstance(art.get("tags"), list) or len(art.get("tags", [])) < 2:
            logger.warning("Article %s has < 2 tags — marking as error", art.get("id", "?"))
            art["status"] = "error"
        valid.append(art)

    valid.sort(key=lambda a: a.get("score", 0), reverse=True)
    logger.info("Organize complete: %d valid articles", len(valid))
    return valid


# ---------------------------------------------------------------------------
# Step 4: Save
# ---------------------------------------------------------------------------


def save(articles: list[dict[str, Any]], dry_run: bool = False) -> list[Path]:
    """Save articles as individual JSON files to ``knowledge/articles/``.

    Args:
        articles: Validated article dicts from the organize step.
        dry_run: If True, skip writing to disk.

    Returns:
        List of Path objects written (empty in dry-run mode).
    """
    if dry_run:
        logger.info("[dry-run] Would save %d articles", len(articles))
        return []

    if not articles:
        logger.info("No articles to save")
        return []

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    for art in articles:
        art_id = art.get("id", str(uuid.uuid4()))
        if not art_id:
            art_id = str(uuid.uuid4())
        path = ARTICLES_DIR / f"{art_id}.json"
        art["published_at"] = None
        path.write_text(json.dumps(art, ensure_ascii=False, indent=2), encoding="utf-8")
        saved.append(path)
        logger.info("Saved: %s (score=%d, status=%s)", path.name, art.get("score", 0), art.get("status", "draft"))

    logger.info("Saved %d articles to %s", len(saved), ARTICLES_DIR)
    return saved


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Turn a repo name or title into a URL-safe slug.

    Args:
        text: Input string like ``"langgenius/dify"`` or ``"My Great Title"``.

    Returns:
        Lowercase hyphenated slug.
    """
    if "/" in text:
        text = text.split("/")[-1]
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-") or "unknown"


def _safe_source(item: dict[str, Any]) -> str:
    """Infer a source label from item data.

    Args:
        item: Raw item dict.

    Returns:
        ``"github"`` if the item has stars, ``"rss"`` otherwise.
    """
    return "github" if item.get("stars") else "rss"


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def run_pipeline(
    sources: list[str],
    limit: int = 20,
    dry_run: bool = False,
) -> int:
    """Execute the full 4-step knowledge pipeline: collect → analyze → organize → save.

    Args:
        sources: Source identifiers (``github``, ``rss``).
        limit: Max items to collect per source.
        dry_run: If True, simulate without persistence or LLM calls.

    Returns:
        0 on success, 1 on failure.
    """
    logger.info(
        "Pipeline START — sources=%s limit=%d dry_run=%s",
        sources,
        limit,
        dry_run,
    )

    try:
        raw_items, raw_path = collect(sources=sources, limit=limit, dry_run=dry_run)
        if not raw_items:
            logger.warning("Pipeline HALTED: no items collected")
            return 1

        articles = analyze(raw_items, dry_run=dry_run)
        organized = organize(articles, dry_run=dry_run)
        saved = save(organized, dry_run=dry_run)

        if dry_run:
            logger.info("Pipeline DRY-RUN complete — would produce %d articles", len(organized))
        else:
            logger.info(
                "Pipeline DONE — collected=%d analyzed=%d organized=%d saved=%d",
                len(raw_items),
                len(articles),
                len(organized),
                len(saved),
            )
        return 0
    except Exception as exc:
        logger.error("Pipeline FAILED: %s", exc, exc_info=True)
        return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="AI Knowledge Base Pipeline — collect, analyze, organize, save",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline/pipeline.py --sources github,rss --limit 20
  python pipeline/pipeline.py --sources github --limit 5
  python pipeline/pipeline.py --sources rss --limit 10
  python pipeline/pipeline.py --sources github --limit 5 --dry-run
  python pipeline/pipeline.py --verbose
        """.strip(),
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="github",
        help="Comma-separated source identifiers: github, rss (default: github)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max items to collect per source (default: 20)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the pipeline without persistence or LLM calls",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for the pipeline CLI.

    Args:
        argv: Command-line arguments. Uses ``sys.argv`` if None.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    valid_sources = {"github", "rss"}
    for src in sources:
        if src not in valid_sources:
            logger.error("Unknown source '%s'. Valid: %s", src, ", ".join(sorted(valid_sources)))
            return 1

    return run_pipeline(sources=sources, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
