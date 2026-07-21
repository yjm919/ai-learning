import json
import logging
import os
import uuid
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


def _build_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-knowledge-base/0.1",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_repo_info(owner: str, repo: str, trace_id: Optional[str] = None) -> dict[str, Any]:
    """从 GitHub API 获取指定仓库的基本信息。

    Args:
        owner: 仓库所有者（用户名或组织名）。
        repo: 仓库名称。
        trace_id: 可追溯的请求 ID，未提供则自动生成。

    Returns:
        包含以下键的字典：
            - full_name (str): 仓库全名，格式 "owner/repo"
            - stars (int): Star 数量
            - forks (int): Fork 数量
            - description (str): 仓库描述（可能为空字符串）
            - topics (list[str]): 仓库 topic 标签列表

    Raises:
        ValueError: owner 或 repo 为空。
        RuntimeError: API 请求失败（含 404、超时等）。
    """
    if not owner or not repo:
        raise ValueError("owner 和 repo 均不能为空")

    tid = trace_id or str(uuid.uuid4())
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"

    logger.debug("[%s] GET %s", tid, url)

    try:
        request = Request(url, headers=_build_headers())
        with urlopen(request, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        logger.error("[%s] GitHub API 返回 %d: %s", tid, exc.code, exc.reason)
        raise RuntimeError(f"GitHub API 请求失败（{exc.code} {exc.reason}）") from exc
    except URLError as exc:
        logger.error("[%s] GitHub API 网络错误: %s", tid, exc.reason)
        raise RuntimeError(f"GitHub API 网络错误: {exc.reason}") from exc

    result: dict[str, Any] = {
        "full_name": data.get("full_name", f"{owner}/{repo}"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "description": data.get("description") or "",
        "topics": data.get("topics", []),
    }

    logger.info("[%s] %s: %d stars, %d forks", tid, result["full_name"], result["stars"], result["forks"])
    return result
