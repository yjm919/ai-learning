#!/usr/bin/env python3
"""MCP (Model Context Protocol) Server for the AI Knowledge Base.

Provides tools to search, retrieve, and inspect locally stored knowledge articles
via JSON-RPC 2.0 over stdio.  Zero third-party dependencies — stdlib only.

Usage:
    python pipeline/mcp_knowledge_server.py

The server reads JSON-RPC requests from stdin line-by-line and writes responses
to stdout (stderr is reserved for debug logs).
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("mcp-knowledge")
logger.setLevel(logging.DEBUG)
_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
logger.addHandler(_stderr_handler)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARTICLES_DIR = Path(__file__).resolve().parent.parent / "knowledge" / "articles"
SERVER_NAME = "knowledge-base-mcp"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

# ---------------------------------------------------------------------------
# Article loader
# ---------------------------------------------------------------------------


def load_articles() -> list[dict[str, Any]]:
    """Load all knowledge articles from the local filesystem.

    Returns:
        List of article dicts.  Files that fail to parse are silently skipped
        (a warning is logged to stderr).
    """
    articles: list[dict[str, Any]] = []
    if not ARTICLES_DIR.is_dir():
        logger.warning("Articles directory not found: %s", ARTICLES_DIR)
        return articles

    json_files = sorted(ARTICLES_DIR.glob("*.json"))
    logger.info("Loading %d articles from %s ...", len(json_files), ARTICLES_DIR)

    for path in json_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            articles.append(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping %s: %s", path.name, exc)

    logger.info("Loaded %d articles", len(articles))
    return articles


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _tool_search_articles(
    articles: list[dict[str, Any]],
    keyword: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search articles by keyword in title and summary.

    Args:
        articles: Pre-loaded article list.
        keyword: Search keyword (case-insensitive).
        limit: Maximum number of results.

    Returns:
        Matching articles, sorted by score descending.
    """
    kw = keyword.lower()
    matches: list[dict[str, Any]] = []
    for art in articles:
        title = (art.get("title") or "").lower()
        summary = (art.get("summary") or "").lower()
        if kw in title or kw in summary:
            matches.append(art)

    matches.sort(key=lambda a: a.get("score", 0), reverse=True)
    return matches[:limit]


def _tool_get_article(
    articles: list[dict[str, Any]],
    article_id: str,
) -> Optional[dict[str, Any]]:
    """Retrieve a single article by its ID.

    Args:
        articles: Pre-loaded article list.
        article_id: The article ``id`` field to look up.

    Returns:
        The article dict, or None if not found.
    """
    for art in articles:
        if art.get("id") == article_id:
            return art
    return None


def _tool_knowledge_stats(articles: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate statistics over all articles.

    Args:
        articles: Pre-loaded article list.

    Returns:
        Dict with ``total``, ``by_source``, ``by_status``, ``top_tags``,
        ``avg_score``.
    """
    total = len(articles)
    if total == 0:
        return {"total": 0, "by_source": {}, "by_status": {}, "top_tags": [], "avg_score": 0}

    source_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    score_sum = 0
    score_count = 0

    for art in articles:
        source_counts[art.get("source", "unknown")] += 1
        status_counts[art.get("status", "unknown")] += 1
        for tag in art.get("tags", []):
            tag_counts[tag] += 1
        score = art.get("score")
        if isinstance(score, (int, float)):
            score_sum += score
            score_count += 1

    return {
        "total": total,
        "by_source": dict(source_counts.most_common()),
        "by_status": dict(status_counts.most_common()),
        "top_tags": [{"tag": tag, "count": cnt} for tag, cnt in tag_counts.most_common(10)],
        "avg_score": round(score_sum / score_count, 1) if score_count else 0,
    }


# ---------------------------------------------------------------------------
# Tool registry (MCP tools/list response schema)
# ---------------------------------------------------------------------------


TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "search_articles",
        "description": (
            "Search knowledge articles by keyword (matches title and summary). "
            "Returns matching articles sorted by score descending."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword (case-insensitive)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5,
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "get_article",
        "description": (
            "Retrieve full details of a single knowledge article by its ID."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "article_id": {
                    "type": "string",
                    "description": "The article ID (e.g. 20260722-github-dify)",
                },
            },
            "required": ["article_id"],
        },
    },
    {
        "name": "knowledge_stats",
        "description": (
            "Return aggregate statistics: total articles, source distribution, "
            "status distribution, top 10 tags, and average score."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 server
# ---------------------------------------------------------------------------


def _build_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 error response.

    Args:
        request_id: The ``id`` from the incoming request (may be None for
            notifications, in which case the caller should suppress the response).
        code: JSON-RPC error code.
        message: Human-readable error description.

    Returns:
        A JSON-RPC error response dict.
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _build_result(request_id: Any, result: Any) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 success response.

    Args:
        request_id: The ``id`` from the incoming request.
        result: The method result payload.

    Returns:
        A JSON-RPC success response dict.
    """
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _handle_initialize(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Handle the ``initialize`` method.

    Returns server capabilities and info.
    """
    logger.info(
        "Initialize — client=%s v%s protocol=%s",
        params.get("clientInfo", {}).get("name", "unknown"),
        params.get("clientInfo", {}).get("version", "0"),
        params.get("protocolVersion", "?"),
    )
    return _build_result(
        request_id,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
        },
    )


def _handle_tools_list(request_id: Any) -> dict[str, Any]:
    """Handle the ``tools/list`` method."""
    return _build_result(request_id, {"tools": TOOLS_SCHEMA})


def _handle_tools_call(
    request_id: Any,
    params: dict[str, Any],
    articles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Handle the ``tools/call`` method.

    Args:
        request_id: JSON-RPC request id.
        params: Must contain ``name`` (tool name) and ``arguments`` (dict).
        articles: Pre-loaded article list for the tool implementations.

    Returns:
        JSON-RPC response with ``content`` array of text blocks.
    """
    tool_name = params.get("name", "")
    args = params.get("arguments", {})

    logger.info("Tool call: %s(%s)", tool_name, json.dumps(args, ensure_ascii=False))

    try:
        if tool_name == "search_articles":
            keyword = args.get("keyword", "")
            if not keyword:
                return _build_error(request_id, -32602, "Missing required argument: keyword")
            limit = int(args.get("limit", 5))
            results = _tool_search_articles(articles, keyword, limit)
            text = json.dumps(results, ensure_ascii=False, indent=2)

        elif tool_name == "get_article":
            article_id = args.get("article_id", "")
            if not article_id:
                return _build_error(request_id, -32602, "Missing required argument: article_id")
            result = _tool_get_article(articles, article_id)
            if result is None:
                text = json.dumps({"error": f"Article '{article_id}' not found"}, ensure_ascii=False)
            else:
                text = json.dumps(result, ensure_ascii=False, indent=2)

        elif tool_name == "knowledge_stats":
            stats = _tool_knowledge_stats(articles)
            text = json.dumps(stats, ensure_ascii=False, indent=2)

        else:
            return _build_error(request_id, -32601, f"Unknown tool: {tool_name}")

    except Exception as exc:
        logger.error("Tool error: %s", exc, exc_info=True)
        return _build_error(request_id, -32603, f"Tool execution error: {exc}")

    return _build_result(request_id, {"content": [{"type": "text", "text": text}]})


def _dispatch(
    request: dict[str, Any],
    articles: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Route an incoming JSON-RPC 2.0 message to the appropriate handler.

    Args:
        request: Parsed JSON-RPC request dict.
        articles: Pre-loaded article list.

    Returns:
        A JSON-RPC response dict, or None if the message was a notification
        (no ``id`` field).
    """
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    if "jsonrpc" not in request:
        return _build_error(req_id, -32600, "Invalid Request: missing jsonrpc version")

    # Notifications: no id → no response
    is_notification = req_id is None

    if method == "initialize":
        resp = _handle_initialize(req_id, params)

    elif method == "tools/list":
        resp = _handle_tools_list(req_id)

    elif method == "tools/call":
        resp = _handle_tools_call(req_id, params, articles)

    elif method == "ping":
        resp = _build_result(req_id, {})

    else:
        logger.warning("Unknown method: %s", method)
        resp = _build_error(req_id, -32601, f"Method not found: {method}")

    if is_notification:
        logger.debug("Notification processed: %s", method)
        return None

    return resp


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run_server() -> None:
    """Start the MCP server, reading from stdin and writing to stdout.

    Loads articles once at startup, then enters the JSON-RPC message loop.
    Errors are logged to stderr and returned as JSON-RPC error responses.
    """
    articles = load_articles()
    logger.info("Server ready — %d articles indexed", len(articles))

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON: %s", exc)
            err_resp = _build_error(None, -32700, f"Parse error: {exc}")
            sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        response = _dispatch(request, articles)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_server()
