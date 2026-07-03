import os
from typing import List

from litellm.types.utils import ModelResponse

from dataset_profiler.common_llm.connector import CommonLLMConnector

# Default models per provider. Overridable with DATA_QUALITY_LLM_MODEL.
DEFAULT_SCAYLE_MODEL = "qwen3"
DEFAULT_BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-6"

# Generating a detection script is a long completion; the shared llm_config.yaml
# timeout (30s) is far too short for it, so data quality uses its own timeout.
DEFAULT_TIMEOUT_SECONDS = 300.0


def get_llm_connector() -> CommonLLMConnector:
    """Build the LLM connector for data quality detection.

    The provider is selected with the ``DATA_QUALITY_LLM_PROVIDER`` env var
    ("scayle" or "bedrock", defaults to "scayle") and the model can be
    overridden with ``DATA_QUALITY_LLM_MODEL``.
    """
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
    response = connector.chat(
        messages, stream=False, temperature=temperature, max_tokens=max_tokens
    )
    if isinstance(response, ModelResponse) and response.choices:
        content = response.choices[0].message.content  # type: ignore[union-attr]
        if content:
            return content
    raise RuntimeError(f"LLM returned an empty or unexpected response: {response}")
