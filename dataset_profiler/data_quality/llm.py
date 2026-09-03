import os
import random
import time
from typing import Callable, List, Optional, TypeVar

import requests
from litellm.exceptions import (
    APIError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
)
from litellm.types.utils import ModelResponse

from dataset_profiler.common_llm.connector import CommonLLMConnector
from dataset_profiler.configs.config_logging import logger

# Default models per provider. Overridable with DATA_QUALITY_LLM_MODEL.
DEFAULT_SCAYLE_MODEL = "qwen3.6"
DEFAULT_BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-6"

# Generating a detection script is a long completion; the shared llm_config.yaml
# timeout (30s) is far too short for it, so data quality uses its own timeout.
DEFAULT_TIMEOUT_SECONDS = 300.0

# Total attempts (initial try + retries) for each LLM interaction.
DEFAULT_MAX_ATTEMPTS = 3
# Base for the exponential backoff between attempts: 2s, then 4s.
DEFAULT_BACKOFF_SECONDS = 2.0

# Transient faults worth retrying: the network dropped, the gateway is briefly
# unavailable, or we are being rate limited. AuthenticationError is checked
# separately in _is_retryable and never retried — bad credentials never fix
# themselves.
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    APIError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
)

# A dataset can hold many tables. Once the endpoint proves unreachable, having
# every remaining table pay the full retry budget wastes minutes for nothing, so
# further attempts are skipped for this long. Time-based rather than permanent
# because Ray reuses worker processes across jobs, and the network may recover
# between them.
DEFAULT_COOLDOWN_SECONDS = 300.0

T = TypeVar("T")

# Monotonic deadline until which the LLM endpoint is treated as unavailable.
_endpoint_unavailable_until = 0.0


class LLMEndpointUnavailable(RuntimeError):
    """Raised while the LLM endpoint is in its post-failure cool-off."""


def _cooldown_seconds() -> float:
    return float(os.environ.get("DATA_QUALITY_LLM_COOLDOWN", DEFAULT_COOLDOWN_SECONDS))


def reset_endpoint_cooldown() -> None:
    """Clear the cool-off (used on success and by tests)."""
    global _endpoint_unavailable_until
    _endpoint_unavailable_until = 0.0


def _max_attempts() -> int:
    return max(1, int(os.environ.get("DATA_QUALITY_LLM_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)))


def _is_retryable(exc: BaseException) -> bool:
    """Whether ``exc`` — or anything it wraps — is a transient fault.

    The chain has to be walked because ``CommonLLMConnector.chat`` re-raises
    SCAYLE failures as a plain ``RuntimeError``; matching only on the outermost
    type would silently classify every chat timeout as permanent.
    """
    seen = set()
    current: Optional[BaseException] = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, AuthenticationError):
            return False
        if isinstance(current, RETRYABLE_EXCEPTIONS):
            return True
        current = current.__cause__ or current.__context__
    return False


def with_retries(operation: Callable[[], T], description: str) -> T:
    """Run ``operation``, retrying transient LLM/network failures with backoff.

    Retries are jittered so that a dataset of many tables does not resend every
    request to a struggling endpoint in lockstep.
    """
    attempts = _max_attempts()
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as e:
            if not _is_retryable(e):
                raise
            if attempt == attempts:
                logger.error(
                    "Data quality LLM call failed, no attempts left",
                    operation=description,
                    attempts=attempts,
                    error=str(e),
                )
                raise
            delay = DEFAULT_BACKOFF_SECONDS * (2 ** (attempt - 1))
            delay += random.uniform(0, delay / 2)
            logger.warning(
                "Data quality LLM call failed, retrying",
                operation=description,
                attempt=attempt,
                max_attempts=attempts,
                retry_in_seconds=round(delay, 1),
                error=str(e),
            )
            time.sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover


def get_llm_connector() -> CommonLLMConnector:
    """Build the LLM connector for data quality detection.

    The provider is selected with the ``DATA_QUALITY_LLM_PROVIDER`` env var
    ("scayle" or "bedrock", defaults to "scayle") and the model can be
    overridden with ``DATA_QUALITY_LLM_MODEL``.

    Construction is retried: for SCAYLE the connector authenticates against the
    LDAP endpoint in its constructor, so a transient network fault surfaces
    here rather than on the first chat call. If the retries are exhausted, the
    endpoint is put in a cool-off so the rest of the dataset fails fast.
    """
    global _endpoint_unavailable_until

    remaining = _endpoint_unavailable_until - time.monotonic()
    if remaining > 0:
        raise LLMEndpointUnavailable(
            "LLM endpoint marked unavailable by an earlier failure; "
            f"skipping data quality for another {remaining:.0f}s"
        )

    try:
        connector = with_retries(_build_llm_connector, "connector setup")
    except Exception:
        cooldown = _cooldown_seconds()
        if cooldown > 0:
            _endpoint_unavailable_until = time.monotonic() + cooldown
            logger.warning(
                "Pausing data quality LLM calls after connector setup failure",
                cooldown_seconds=cooldown,
            )
        raise

    reset_endpoint_cooldown()
    return connector


def _build_llm_connector() -> CommonLLMConnector:
    provider = os.environ.get("DATA_QUALITY_LLM_PROVIDER", "scayle").lower()

    timeout = float(
        os.environ.get("DATA_QUALITY_LLM_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)
    )

    if provider == "scayle":
        model = os.environ.get("DATA_QUALITY_LLM_MODEL") or DEFAULT_SCAYLE_MODEL
        # No config_file on purpose: llm_config.yaml pins a 30s scayle timeout
        # (tuned for short PDF formula calls) that would override ours. The
        # connector falls back to the SCAYLE_* env vars for credentials.
        return CommonLLMConnector(
            provider="scayle-llm",
            model=model,
            scayle_timeout=timeout,
        )
    if provider == "bedrock":
        model = os.environ.get("DATA_QUALITY_LLM_MODEL") or DEFAULT_BEDROCK_MODEL
        # Credentials are passed explicitly from the environment instead of the
        # config file, whose bedrock section only holds placeholders.
        return CommonLLMConnector(
            provider="bedrock",
            model=model,
            aws_credentials={
                "access_key_id": os.environ.get("AWS_ACCESS_KEY_ID", ""),
                "secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
                "region": os.environ.get("AWS_REGION", "us-east-1"),
            },
        )
    raise ValueError(
        f"Unsupported DATA_QUALITY_LLM_PROVIDER '{provider}'. "
        "Supported providers: 'scayle', 'bedrock'."
    )


def chat_completion(
    connector: CommonLLMConnector,
    messages: List[dict],
    temperature: float = 0.0,
    max_tokens: int = 8192,
) -> str:
    """Send a chat request and return the assistant message content."""
    response = with_retries(
        lambda: connector.chat(
            messages, stream=False, temperature=temperature, max_tokens=max_tokens
        ),
        "chat completion",
    )
    if isinstance(response, ModelResponse) and response.choices:
        content = response.choices[0].message.content  # type: ignore[union-attr]
        if content:
            return content
    raise RuntimeError(f"LLM returned an empty or unexpected response: {response}")
