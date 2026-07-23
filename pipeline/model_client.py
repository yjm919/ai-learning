from __future__ import annotations

import json
import logging
import os
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Usage:
    """LLM Token usage statistics.

    Attributes:
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        total_tokens: Total tokens consumed.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Unified LLM response container.

    Attributes:
        content: The text content of the model's reply.
        model: Name of the model that generated the response.
        usage: Token usage statistics for this call.
        finish_reason: Reason the model stopped generating.
        raw: The raw response payload from the provider.
    """

    content: str
    model: str = ""
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

ProviderConfig = dict[str, str]

PROVIDER_CONFIGS: dict[str, ProviderConfig] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-turbo",
        "env_key": "DASHSCOPE_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
}

# Pricing in CNY per 1M tokens (prompt, completion).
PRICING_CNY_PER_1M: dict[str, tuple[float, float]] = {
    "deepseek": (1, 2),
    "qwen": (4, 12),
    "openai": (150, 600),
}


class CostTracker:
    """Track LLM API token consumption and estimated cost across calls.

    Records every successful chat completion's token usage and computes
    cumulative cost per provider based on :data:`PRICING_CNY_PER_1M`.

    A module-level singleton ``tracker`` is created at import time.
    """

    def __init__(self) -> None:
        """Initialize an empty tracker."""
        self._records: list[dict[str, Any]] = []
        self._prompt_tokens: dict[str, int] = {}
        self._completion_tokens: dict[str, int] = {}

    def record(self, usage: Usage, provider: str) -> None:
        """Record one API call's token consumption.

        Args:
            usage: Token usage statistics from the API response.
            provider: Provider identifier (``deepseek``, ``qwen``, ``openai``).
        """
        self._records.append({
            "provider": provider,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        })
        self._prompt_tokens[provider] = (
            self._prompt_tokens.get(provider, 0) + usage.prompt_tokens
        )
        self._completion_tokens[provider] = (
            self._completion_tokens.get(provider, 0) + usage.completion_tokens
        )
        logger.debug(
            "CostTracker recorded %s: +%d prompt +%d completion tokens",
            provider,
            usage.prompt_tokens,
            usage.completion_tokens,
        )

    def estimated_cost(self, provider: str) -> float:
        """Return the estimated cumulative cost for a provider in CNY.

        Args:
            provider: Provider identifier.

        Returns:
            Estimated cost in 元 (CNY).  Returns 0.0 for unknown providers or
            when no calls have been recorded.
        """
        if provider not in PRICING_CNY_PER_1M:
            return 0.0
        input_price, output_price = PRICING_CNY_PER_1M[provider]
        prompt = self._prompt_tokens.get(provider, 0) / 1_000_000
        completion = self._completion_tokens.get(provider, 0) / 1_000_000
        return round(prompt * input_price + completion * output_price, 6)

    def report(self, provider: Optional[str] = None) -> str:
        """Generate a cost summary report.

        Args:
            provider: If given, report for a single provider only.
                If None, report for all recorded providers.

        Returns:
            Human-readable multi-line report string.
        """
        providers = [provider] if provider else list(self._prompt_tokens.keys())
        if not providers:
            return "CostTracker: no API calls recorded."

        lines: list[str] = [
            "═══════════════════════════════════════════",
            "  LLM Cost Report (CNY)",
            "═══════════════════════════════════════════",
        ]
        total_cost = 0.0
        for p in sorted(providers):
            prompt_k = self._prompt_tokens.get(p, 0) / 1000
            completion_k = self._completion_tokens.get(p, 0) / 1000
            cost = self.estimated_cost(p)
            total_cost += cost
            calls = sum(1 for r in self._records if r["provider"] == p)
            lines.append(
                f"  {p:12s}  {calls:3d} calls  "
                f"{prompt_k:8.1f}K in / {completion_k:8.1f}K out  "
                f"¥{cost:.4f}"
            )
        lines.append("───────────────────────────────────────────")
        lines.append(f"  {'TOTAL':12s}  {'':3s}  {'':>8s}   {'':>8s}   ¥{total_cost:.4f}")
        lines.append("═══════════════════════════════════════════")
        return "\n".join(lines)


# Module-level singleton — auto-wired into OpenAICompatibleProvider.chat()
tracker = CostTracker()


class ProviderName(str, Enum):
    """Supported LLM provider identifiers."""

    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    OPENAI = "openai"


# ---------------------------------------------------------------------------
# Abstract base provider
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All provider implementations must subclass this and provide concrete
    ``chat`` and ``stream`` methods.
    """

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a non-streaming chat completion request.

        Args:
            messages: List of message dicts with ``role`` and ``content`` keys.
            model: Model name override. Provider default is used if None.
            temperature: Sampling temperature (0–2).
            max_tokens: Maximum completion tokens to generate.
            **kwargs: Additional parameters forwarded to the API.

        Returns:
            LLMResponse with content, model, usage, and finish reason.

        Raises:
            httpx.HTTPError: On transport or HTTP-level failures.
        """
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> Any:
        """Send a streaming chat completion request.

        Args:
            messages: List of message dicts with ``role`` and ``content`` keys.
            model: Model name override.
            temperature: Sampling temperature (0–2).
            max_tokens: Maximum completion tokens to generate.
            **kwargs: Additional parameters forwarded to the API.

        Returns:
            An iterator yielding delta chunks.

        Raises:
            httpx.HTTPError: On transport or HTTP-level failures.
        """
        ...


# ---------------------------------------------------------------------------
# OpenAI-compatible provider implementation
# ---------------------------------------------------------------------------


class OpenAICompatibleProvider(LLMProvider):
    """LLM provider using an OpenAI-compatible chat completions endpoint.

    Works with DeepSeek, Qwen (DashScope), OpenAI, and any third-party service
    that exposes the ``/v1/chat/completions`` API.

    Args:
        provider: Provider identifier (``deepseek``, ``qwen``, ``openai``).
        api_key: API key. If None, read from the provider's env var.
        base_url: Base URL override. Derived from provider config if None.
        default_model: Default model override. Derived from provider config if None.
        timeout: HTTP request timeout in seconds.

    Raises:
        ValueError: If the provider is unknown or no API key can be resolved.
    """

    def __init__(
        self,
        provider: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        config = PROVIDER_CONFIGS.get(provider)
        if config is None:
            raise ValueError(
                f"Unknown provider '{provider}'. Must be one of: "
                f"{', '.join(PROVIDER_CONFIGS.keys())}"
            )

        self.provider = provider
        self.base_url = (base_url or config["base_url"]).rstrip("/")
        self.default_model = default_model or config["default_model"]
        self.timeout = timeout
        self.api_key = api_key or os.getenv(config["env_key"])
        if not self.api_key:
            raise ValueError(
                f"No API key found for provider '{provider}'. "
                f"Set the {config['env_key']} environment variable."
            )
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self.timeout),
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a non-streaming chat completion request.

        Args:
            messages: List of message dicts with ``role`` and ``content`` keys.
            model: Model name override. Provider default is used if None.
            temperature: Sampling temperature (0–2).
            max_tokens: Maximum completion tokens to generate.
            **kwargs: Additional parameters forwarded to the API.

        Returns:
            LLMResponse with content, model, usage, and finish reason.

        Raises:
            httpx.HTTPError: On transport or HTTP-level failures.
        """
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        payload.update(kwargs)

        response = self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        usage_raw = data.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
        )
        tracker.record(usage, self.provider)

        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", ""),
            usage=usage,
            finish_reason=choice.get("finish_reason", ""),
            raw=data,
        )

    def stream(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> Any:
        """Send a streaming chat completion request.

        Args:
            messages: List of message dicts with ``role`` and ``content`` keys.
            model: Model name override.
            temperature: Sampling temperature (0–2).
            max_tokens: Maximum completion tokens to generate.
            **kwargs: Additional parameters forwarded to the API.

        Yields:
            Delta chunk strings as they arrive from the API.

        Raises:
            httpx.HTTPError: On transport or HTTP-level failures.
        """
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        payload.update(kwargs)

        with self._client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[len("data: "):]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> OpenAICompatibleProvider:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------


def get_provider(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = 60.0,
) -> OpenAICompatibleProvider:
    """Factory: create an LLM provider from environment or explicit args.

    The provider name is resolved in order:
    1. Explicit ``provider`` argument.
    2. ``LLM_PROVIDER`` environment variable.
    3. Default ``"deepseek"``.

    Args:
        provider: Provider name (``deepseek``, ``qwen``, ``openai``).
        api_key: API key override.
        base_url: Base URL override.
        model: Default model override.
        timeout: Request timeout in seconds.

    Returns:
        Configured OpenAICompatibleProvider instance.

    Raises:
        ValueError: If the provider is unknown or no API key can be resolved.
    """
    resolved = provider or os.getenv("LLM_PROVIDER", "deepseek")
    return OpenAICompatibleProvider(
        provider=resolved,
        api_key=api_key,
        base_url=base_url,
        default_model=model,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def chat_with_retry(
    provider: LLMProvider,
    messages: list[dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    **kwargs: Any,
) -> LLMResponse:
    """Call provider.chat() with exponential-backoff retry.

    Retries on ``httpx.HTTPError``, ``httpx.TimeoutException``, or non-200
    HTTP status.  Waits ``base_delay * backoff_factor ** attempt`` seconds
    between attempts (plus jitter).

    Args:
        provider: A concrete LLMProvider instance.
        messages: List of message dicts with ``role`` and ``content`` keys.
        model: Model name override.
        temperature: Sampling temperature (0–2).
        max_tokens: Maximum completion tokens to generate.
        max_retries: Maximum number of retry attempts (3 by default).
        base_delay: Base delay in seconds for the first retry.
        backoff_factor: Multiplicative factor for each subsequent delay.
        **kwargs: Additional parameters forwarded to the API.

    Returns:
        LLMResponse on success.

    Raises:
        RuntimeError: When all retries are exhausted.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return provider.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = base_delay * (backoff_factor ** attempt)
                jitter = random.uniform(0, delay * 0.5)
                total_delay = delay + jitter
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                    total_delay,
                )
                time.sleep(total_delay)
            else:
                logger.error(
                    "LLM call failed after %d attempts: %s",
                    max_retries + 1,
                    exc,
                )
    raise RuntimeError(
        f"LLM call failed after {max_retries + 1} attempts"
    ) from last_exc


# ---------------------------------------------------------------------------
# Token estimation & cost
# ---------------------------------------------------------------------------

# Approximate ratios: 1 token ≈ 4 characters for English, 1.5–2 chars for Chinese.
TOKEN_CHARS_EN = 4.0
TOKEN_CHARS_ZH = 2.0


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a piece of text.

    Uses a heuristic that distinguishes Latin letters from CJK characters to
    produce a reasonable approximation without pulling in ``tiktoken``.

    Args:
        text: The input text to estimate.

    Returns:
        Estimated token count (always >= 1 for non-empty input).
    """
    if not text:
        return 0
    latin_chars = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    other_chars = max(len(text) - latin_chars, 0)
    return max(1, int(latin_chars / TOKEN_CHARS_EN + other_chars / TOKEN_CHARS_ZH))


def estimate_cost(
    prompt: str,
    completion: str,
    provider: Optional[str] = None,
) -> float:
    """Estimate the CNY cost of an LLM call.

    Uses heuristic token counting and provider-specific pricing tables.

    Args:
        prompt: The prompt text sent to the model.
        completion: The model's response text.
        provider: Provider name. If None, resolved from ``LLM_PROVIDER`` env var
            (default ``deepseek``).

    Returns:
        Estimated cost in CNY (元).
    """
    resolved = provider or os.getenv("LLM_PROVIDER", "deepseek")
    prompt_price, completion_price = PRICING_CNY_PER_1M.get(
        resolved, PRICING_CNY_PER_1M["deepseek"]
    )
    prompt_tokens = estimate_tokens(prompt)
    completion_tokens = estimate_tokens(completion)
    cost = (prompt_tokens / 1_000_000) * prompt_price + (
        completion_tokens / 1_000_000
    ) * completion_price
    logger.debug(
        "Estimated cost for %s: prompt=%d tok, completion=%d tok → ¥%.6f",
        resolved,
        prompt_tokens,
        completion_tokens,
        cost,
    )
    return cost


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def quick_chat(
    prompt: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    max_retries: int = 3,
) -> str:
    """One-shot LLM call from a plain string prompt.

    Wraps :func:`chat_with_retry` with automatic provider creation and
    message assembly.

    Args:
        prompt: The user message text.
        model: Model name override.
        provider: Provider name override. Falls back to ``LLM_PROVIDER`` env var
            or ``deepseek``.
        api_key: API key override.
        system: Optional system message to set the model's behaviour.
        temperature: Sampling temperature (0–2).
        max_tokens: Maximum completion tokens to generate.
        max_retries: Maximum retry attempts.

    Returns:
        The model's response text.

    Raises:
        RuntimeError: When all retries are exhausted.
    """
    prov = get_provider(provider=provider, api_key=api_key, model=model)
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = chat_with_retry(
        provider=prov,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=max_retries,
    )
    return response.content


# ---------------------------------------------------------------------------
# Self-test (only executed when the module is run directly)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    provider_name = os.getenv("LLM_PROVIDER", "deepseek")
    print(f"=== LLM Client Smoke Test (provider={provider_name}) ===\n")

    # 1. Token estimation
    print("--- Token estimation ---")
    en_text = "The quick brown fox jumps over the lazy dog."
    zh_text = "你好，世界！这是一段中文测试文本。"
    print(f"  '{en_text}' → ~{estimate_tokens(en_text)} tokens")
    print(f"  '{zh_text}' → ~{estimate_tokens(zh_text)} tokens")

    # 2. Cost estimation
    print("\n--- Cost estimation ---")
    cost = estimate_cost("Explain AI in 100 words.", "AI stands for Artificial Intelligence. It is...")
    print(f"  Estimated cost: ¥{cost:.6f}")

    # 3. Actual API call
    print("\n--- Quick chat (real API call) ---")
    try:
        reply = quick_chat(
            prompt="Reply with exactly one sentence: What is an LLM?",
            max_tokens=100,
        )
        print(f"  Response: {reply}")
        print("  [PASS] Quick chat succeeded.")
    except Exception as exc:
        print(f"  [WARN] Quick chat failed: {exc}")

    # 4. Provider URL display
    print("\n--- Provider info ---")
    try:
        prov = get_provider()
        print(f"  Base URL: {prov.base_url}")
        print(f"  Default model: {prov.default_model}")
        prov.close()
    except Exception as exc:
        print(f"  [WARN] Could not create provider: {exc}")

    print("\n=== Smoke test complete ===")

    # 5. Tracker report
    print("\n" + tracker.report())
