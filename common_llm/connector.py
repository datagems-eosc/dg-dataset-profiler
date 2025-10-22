import os
import time
import logging
from typing import Optional, List, Dict, Union, Any
from pydantic import BaseModel, field_validator
import litellm
from litellm import completion
from litellm.types.utils import ModelResponse
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.integrations.custom_logger import CustomLogger
from litellm.exceptions import APIError, AuthenticationError, RateLimitError
from common_llm.config_handler import load_config


def load_llm_config(
    config_file: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    aws_credentials: Optional[Dict[str, str]] = None,
    track_tokens: Optional[bool] = None,
    track_cost: Optional[bool] = None,
    log_config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Load and merge configuration from file, parameters, and defaults.

    Args:
        config_file: Path to the configuration file.
        provider: LLM provider name (e.g., 'openai', 'ollama').
        model: Model name (e.g., 'gpt-3.5-turbo').
        api_key: API key for the provider.
        api_base: Base URL for the provider's API.
        aws_credentials: AWS credentials for providers like Bedrock.
        track_tokens: Whether to track token usage.
        track_cost: Whether to track API call costs.
        log_config: Logging configuration dictionary.

    Returns:
        Dict[str, Any]: Unified configuration dictionary.
    """
    config = {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "api_base": api_base,
        "aws_credentials": aws_credentials,
        "track_tokens": track_tokens if track_tokens is not None else False,
        "track_cost": track_cost if track_cost is not None else False,
        "log_config": log_config,
        "input_cost_per_token": None,
        "output_cost_per_token": None,
        "max_input_tokens": None,
        "max_output_tokens": None,
        "max_tokens": None,
    }

    # Load from config file if provided
    if config_file:
        try:
            loaded_config = load_config(config_file)
            if provider in loaded_config:
                prov_cfg = loaded_config[provider]
                config.update(
                    {
                        "api_key": prov_cfg.get("api_key", config["api_key"]),
                        "api_base": prov_cfg.get("api_base", config["api_base"]),
                        "aws_credentials": prov_cfg.get(
                            "aws_credentials", config["aws_credentials"]
                        ),
                        "track_tokens": prov_cfg.get("tracking", {}).get(
                            "track_tokens", config["track_tokens"]
                        ),
                        "track_cost": prov_cfg.get("tracking", {}).get(
                            "track_cost", config["track_cost"]
                        ),
                    }
                )
                # Model-specific cost and token limits
                model_full = (
                    f"{provider}/{model}"
                    if provider not in ["openai", "ollama"]
                    else model
                )
                model_cfg = prov_cfg.get(model_full, {})
                cost_cfg = model_cfg.get("cost_per_token", {})
                config.update(
                    {
                        "input_cost_per_token": (
                            cost_cfg.get("prompt_cost_per_1M_tokens", None) / 1e6
                            if cost_cfg.get("prompt_cost_per_1M_tokens")
                            else None
                        ),
                        "output_cost_per_token": (
                            cost_cfg.get("completion_cost_per_1M_tokens", None) / 1e6
                            if cost_cfg.get("completion_cost_per_1M_tokens")
                            else None
                        ),
                    }
                )
            config["log_config"] = loaded_config.get("logging", log_config)
        except Exception as e:
            logging.getLogger("CommonLLMConnector").error(f"Failed to load config: {e}")

    # Fallback to litellm.model_cost
    model_full = (
        f"{provider}/{model}" if provider not in ["openai", "ollama"] else model
    )
    if model_full in litellm.model_cost:
        mc = litellm.model_cost[model_full]
        config.update(
            {
                "input_cost_per_token": config["input_cost_per_token"]
                or mc["input_cost_per_token"],
                "output_cost_per_token": config["output_cost_per_token"]
                or mc["output_cost_per_token"],
                "max_input_tokens": config["max_input_tokens"]
                or mc["max_input_tokens"],
                "max_output_tokens": config["max_output_tokens"]
                or mc["max_output_tokens"],
                "max_tokens": config["max_tokens"] or mc["max_tokens"],
            }
        )

    return config


def setup_logger(
    name: str = "CommonLLMConnector",
    log_config: Optional[Dict] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.

    Args:
        name: Logger name.
        log_config: Logging configuration dictionary.
        provider: LLM provider name.
        model: Model name.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    if log_config and isinstance(log_config, dict):
        level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    else:
        level = logging.INFO

    logger.setLevel(level)  # Always set the level

    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    if log_config and "log_path" in log_config:
        timestamp = (
            time.strftime("%Y%m%d_%H%M%S") + f"_{int((time.time() % 1) * 1000):03d}"
        )
        model_str = model.replace("/", "_") if model else "unknown"
        filename = (
            f"{provider}_{model_str}_{timestamp}.log"
            if provider
            else f"llm_{timestamp}.log"
        )
        os.makedirs(log_config["log_path"], exist_ok=True)
        fh = logging.FileHandler(os.path.join(log_config["log_path"], filename))
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


class LLMConfig(BaseModel):
    """Configuration model for LLM connector."""

    provider: str
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    aws_credentials: Optional[Dict[str, str]] = None
    track_tokens: bool = False
    track_cost: bool = False
    log_config: Optional[Dict] = None
    input_cost_per_token: Optional[float] = None
    output_cost_per_token: Optional[float] = None
    max_input_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None
    max_tokens: Optional[int] = None

    @field_validator("provider")
    def validate_provider(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Provider must be a non-empty string")
        return v.lower()

    @field_validator("model")
    def validate_model(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Model must be a non-empty string")
        return v


class CommonLLMLogging(CustomLogger):
    """Custom logger for tracking LLM API interactions."""

    MAX_CHARS_TRUNC = 50

    def __init__(
        self,
        log_config: Optional[Dict] = None,
        track_tokens: bool = False,
        track_cost: bool = False,
        track_input_content: bool = True,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the logger with configuration.

        Args:
            log_config: Logging configuration dictionary.
            track_tokens: Whether to track token usage.
            track_cost: Whether to track API call costs.
            track_input_content: Whether to log input content.
            provider: LLM provider name.
            model: Model name.
        """
        super().__init__()
        self.track_tokens = bool(
            log_config.get("track_tokens", track_tokens) if log_config else track_tokens
        )
        self.track_cost = bool(
            log_config.get("track_cost", track_cost) if log_config else track_cost
        )
        self.track_input_content = bool(
            log_config.get("track_input_content", track_input_content)
            if log_config
            else track_input_content
        )
        self.provider = log_config.get("provider", provider) if log_config else provider
        self.model = log_config.get("model", model) if log_config else model
        self.start_time: Optional[float] = None
        self.output_text = ""
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.input_cost_per_token: Optional[float] = None
        self.output_cost_per_token: Optional[float] = None
        self.logger = setup_logger(
            "CommonLLMConnector", log_config, self.provider, self.model
        )

    def calculate_cost(self) -> Dict[str, float]:
        """Calculate cost based on usage and token rates."""
        if (
            self.input_cost_per_token is not None
            and self.output_cost_per_token is not None
        ):
            prompt_cost = self.input_cost_per_token * self.usage["prompt_tokens"]
            completion_cost = (
                self.output_cost_per_token * self.usage["completion_tokens"]
            )
            return {
                "prompt_cost": prompt_cost,
                "completion_cost": completion_cost,
                "total_cost": prompt_cost + completion_cost,
            }
        return {}

    def log_pre_api_call(
        self, model: str, messages: List[Dict[str, str]], kwargs: Dict[str, Any]
    ):
        """Log details before an API call."""
        self.start_time = time.time()
        content = (
            " ".join(m.get("content", "") for m in messages)[: self.MAX_CHARS_TRUNC]
            + "..."
            if self.track_input_content
            else "N/A"
        )
        self.logger.debug(f"Pre-API: model={model}, input={content}, kwargs={kwargs}")

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        """Log details after a successful API response."""
        execution_time = (end_time - start_time).total_seconds()
        log_parts = [
            f"Success: model={self.model}, execution_time={execution_time:.2f}s"
        ]

        if self.track_tokens and hasattr(response_obj, "usage") and response_obj.usage:
            self.usage.update(
                {
                    "prompt_tokens": getattr(response_obj.usage, "prompt_tokens", 0)
                    or 0,
                    "completion_tokens": getattr(
                        response_obj.usage, "completion_tokens", 0
                    )
                    or 0,
                    "total_tokens": (
                        getattr(response_obj.usage, "prompt_tokens", 0) or 0
                    )
                    + (getattr(response_obj.usage, "completion_tokens", 0) or 0),
                }
            )
            log_parts.append(
                f"prompt_tokens={self.usage['prompt_tokens']}, "
                f"completion_tokens={self.usage['completion_tokens']}, "
                f"total_tokens={self.usage['total_tokens']}"
            )

        if (
            self.track_cost
            and self.input_cost_per_token is not None
            and self.output_cost_per_token is not None
        ):
            try:
                cost = self.calculate_cost()
                log_parts.append(
                    f"cost={cost['total_cost']:.6f} (prompt: {cost['prompt_cost']:.6f}, "
                    f"completion: {cost['completion_cost']:.6f})"
                )
            except Exception as e:
                log_parts.append(f"cost tracking failed: {str(e)}")

        self.logger.info(", ".join(log_parts))

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """Log details after a failed API response."""
        self.logger.error(f"Failure: model={self.model}, error={str(response_obj)}")


class CommonLLMConnector:
    """A connector for interacting with various LLM providers using a unified interface.

    This class handles configuration, logging, and communication with LLM APIs,
    supporting both streaming and non-streaming chat completions.

    Attributes:
        provider: The LLM provider (e.g., 'openai', 'ollama').
        model: The full model name (e.g., 'gpt-3.5-turbo').
        api_key: API key for the provider.
        api_base: Base URL for the provider's API.
        aws_credentials: AWS credentials for providers like Bedrock.
        track_tokens: Whether to track token usage.
        track_cost: Whether to track API call costs.
        input_cost_per_token: Cost per input token.
        output_cost_per_token: Cost per output token.
        max_input_tokens: Maximum input tokens allowed.
        max_output_tokens: Maximum output tokens allowed.
        max_tokens: Maximum total tokens allowed.
        extra_config: Additional configuration parameters.
        logging_obj: Logger instance for tracking API interactions.
        enable_logging: Whether logging is enabled.
    """

    def __init__(
        self,
        provider: str,
        model: str,
        config_file: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        aws_credentials: Optional[Dict[str, str]] = None,
        log_config: Optional[Dict] = None,
        track_tokens: bool = True,
        track_cost: bool = True,
        enable_logging: bool = True,
        **extra_config,
    ):
        """
        Initialize the LLM connector with provider, model, and configuration.

        Args:
            provider: The LLM provider name (e.g., 'openai', 'ollama').
            model: The model name (e.g., 'gpt-3.5-turbo').
            config_file: Path to configuration file.
            api_key: API key for the provider.
            api_base: Base URL for the provider's API.
            aws_credentials: AWS credentials for providers like Bedrock.
            log_config: Logging configuration dictionary.
            track_tokens: Whether to track token usage.
            track_cost: Whether to track API call costs.
            enable_logging: Whether to enable logging.
            **extra_config: Additional configuration parameters.
        """
        config = LLMConfig(
            **load_llm_config(
                config_file=config_file,
                provider=provider,
                model=model,
                api_key=api_key,
                api_base=api_base,
                aws_credentials=aws_credentials,
                track_tokens=track_tokens,
                track_cost=track_cost,
                log_config=log_config,
            )
        ).model_dump()

        self.provider = config["provider"]
        self.model = (
            f"{self.provider}/{model}"
            if self.provider not in ["openai", "ollama"]
            else model
        )
        self.api_key = config.get("api_key", None)
        self.api_base = config.get("api_base", None)
        self.aws_credentials = config.get("aws_credentials", None)
        self.track_tokens = config.get("track_tokens", True)
        self.track_cost = config.get("track_cost", True)
        self.input_cost_per_token = config.get("input_cost_per_token", None)
        self.output_cost_per_token = config.get("output_cost_per_token", None)
        self.max_input_tokens = config.get("max_input_tokens", None)
        self.max_output_tokens = config.get("max_output_tokens", None)
        self.max_tokens = config.get("max_tokens", None)
        self.extra_config = extra_config.copy()

        # Initialize logger
        self.logging_obj = CommonLLMLogging(
            log_config=config["log_config"],
            track_tokens=self.track_tokens,
            track_cost=self.track_cost,
            provider=self.provider,
            model=self.model,
        )
        self.logging_obj.input_cost_per_token = self.input_cost_per_token
        self.logging_obj.output_cost_per_token = self.output_cost_per_token

        # Set environment variables
        if self.api_key:
            os.environ[f"{self.provider.upper()}_API_KEY"] = self.api_key
            self.logging_obj.logger.debug(f"Set {self.provider.upper()}_API_KEY")
        if self.aws_credentials:
            os.environ["AWS_ACCESS_KEY_ID"] = self.aws_credentials.get(
                "access_key_id", ""
            )
            os.environ["AWS_SECRET_ACCESS_KEY"] = self.aws_credentials.get(
                "secret_access_key", ""
            )
            os.environ["AWS_REGION_NAME"] = self.aws_credentials.get("region", "")
            self.logging_obj.logger.debug("Set AWS env vars")

        # Enable logging callback
        self.enable_logging = enable_logging
        if self.enable_logging:
            litellm.callbacks = [self.logging_obj]

        self.logging_obj.logger.debug(
            f"Connector initialized: provider={self.provider}, model={self.model}, "
            f"track_tokens={self.track_tokens}, track_cost={self.track_cost}"
        )

    def process_streaming_response(self, response: CustomStreamWrapper) -> str:
        """
        Process a streaming response and return the complete content as a string.

        Args:
            response: The streaming response object from litellm.

        Returns:
            str: The concatenated response content.
        """
        content = ""
        for chunk in response:
            if chunk:
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    _, chunk_obj = chunk
                else:
                    chunk_obj = chunk
                if isinstance(chunk_obj, str):
                    content += chunk_obj
                elif (
                    hasattr(chunk_obj, "choices")
                    and chunk_obj.choices
                    and hasattr(chunk_obj.choices[0], "delta")
                ):
                    delta_content = (
                        getattr(chunk_obj.choices[0].delta, "content", "") or ""
                    )
                    content += delta_content
        return content

    def chat(
        self, message: List, stream: bool = False, **kwargs
    ) -> Union[Dict[str, str], ModelResponse, CustomStreamWrapper]:
        """
        Send a chat message to the LLM provider and get a response.

        Args:
            message: List of messages in the chat format.
            stream: Whether to stream the response.
            **kwargs: Additional configuration parameters.

        Returns:
            Union[Dict[str, str], ModelResponse, CustomStreamWrapper]: The chat response.
                - If stream=True, returns a CustomStreamWrapper for iterative processing.
                - If stream=False, returns a ModelResponse or Dict[str, str].
        """
        self.logging_obj.logger.debug(
            f"Starting chat completion for {self.provider}/{self.model} with stream={stream}"
        )
        try:
            config = {**self.extra_config, **kwargs}
            if self.api_base:
                config["api_base"] = self.api_base
            response = completion(
                model=self.model, messages=message, stream=stream, **config
            )
            if stream:
                self.logging_obj.logger.debug(
                    f"Streaming chat completion response received for {self.provider}/{self.model}."
                )
                return response
            else:
                content = response.choices[0].message["content"]  # type: ignore
                self.logging_obj.logger.debug(
                    f"Chat completion response {content[:self.logging_obj.MAX_CHARS_TRUNC]} received for {self.provider}/{self.model}."
                )
                return response
        except AuthenticationError as e:
            self.logging_obj.logger.error(
                f"Authentication failed for {self.provider}/{self.model}: {str(e)}"
            )
            raise ValueError(f"Invalid credentials for {self.provider}: {str(e)}")
        except RateLimitError as e:
            self.logging_obj.logger.error(
                f"Rate limit exceeded for {self.provider}/{self.model}: {str(e)}"
            )
            raise RuntimeError(f"Rate limit exceeded: {str(e)}")
        except APIError as e:
            self.logging_obj.logger.error(
                f"API error for {self.provider}/{self.model}: {str(e)}"
            )
            raise RuntimeError(f"API error: {str(e)}")
        except Exception as e:
            self.logging_obj.logger.error(
                f"Unexpected error in chat completion for {self.provider}/{self.model}: {str(e)}"
            )
            raise RuntimeError(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    # Example usage
    connector = CommonLLMConnector(
        provider="ollama",
        model="ollama/gpt-oss:120b",
        config_file="common_llm/configs/llm_config.yaml",
    )
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me more about yourself."},
    ]
    response = connector.chat(messages, stream=True)
    if isinstance(response, CustomStreamWrapper):
        print("Chat Response:", connector.process_streaming_response(response))
    else:
        print("Chat Response:", response)
