import os
import time
import logging
import requests
from typing import Optional, List, Dict, Union, Any
from pydantic import BaseModel, field_validator
import litellm
from litellm import completion
from litellm.types.utils import ModelResponse, Choices, Message, Usage
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.integrations.custom_logger import CustomLogger
from litellm.exceptions import APIError, AuthenticationError, RateLimitError
from dataset_profiler.common_llm.config_handler import load_config
from dataset_profiler.common_llm.scayle_auth import ScayleAuthClient


def load_llm_config(
    config_file: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    aws_credentials: Optional[Dict[str, str]] = None,
    scayle_username: Optional[str] = None,
    scayle_password: Optional[str] = None,
    scayle_verify_ssl: Optional[bool] = None,
    scayle_timeout: Optional[float] = None,
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
        "scayle_username": scayle_username,
        "scayle_password": scayle_password,
        "scayle_verify_ssl": scayle_verify_ssl,
        "scayle_timeout": scayle_timeout,
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
                        "scayle_username": prov_cfg.get(
                            "username", config["scayle_username"]
                        ),
                        "scayle_password": prov_cfg.get(
                            "password", config["scayle_password"]
                        ),
                        "scayle_verify_ssl": prov_cfg.get(
                            "verify_ssl", config["scayle_verify_ssl"]
                        ),
                        "scayle_timeout": prov_cfg.get(
                            "timeout", config["scayle_timeout"]
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
                    model
                    if provider in ["openai", "ollama", "scayle-llm"]
                    else f"{provider}/{model}"
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
        model
        if provider in ["openai", "ollama", "scayle-llm"]
        else f"{provider}/{model}"
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
    scayle_username: Optional[str] = None
    scayle_password: Optional[str] = None
    scayle_verify_ssl: Optional[bool] = None
    scayle_timeout: Optional[float] = None
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
        scayle_username: Optional[str] = None,
        scayle_password: Optional[str] = None,
        scayle_verify_ssl: Optional[bool] = None,
        scayle_timeout: Optional[float] = None,
        log_config: Optional[Dict] = None,
        track_tokens: bool = True,
        track_cost: bool = True,
        enable_logging: bool = True,
        **extra_config,
    ):
        """
        Initialize the LLM connector with provider, model, and configuration.

        Args:
            provider: The LLM provider name (e.g., 'openai', 'ollama', 'scayle-llm').
            model: The model name (e.g., 'gpt-3.5-turbo').
            config_file: Path to configuration file.
            api_key: API key for the provider.
            api_base: Base URL for the provider's API.
            aws_credentials: AWS credentials for providers like Bedrock.
            scayle_username: Scayle username for authentication.
            scayle_password: Scayle password for authentication.
            scayle_verify_ssl: Whether to verify SSL certificates when using Scayle.
            scayle_timeout: Timeout in seconds for Scayle authentication requests.
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
                scayle_username=scayle_username,
                scayle_password=scayle_password,
                scayle_verify_ssl=scayle_verify_ssl,
                scayle_timeout=scayle_timeout,
                track_tokens=track_tokens,
                track_cost=track_cost,
                log_config=log_config,
            )
        ).model_dump()

        self.provider = config["provider"]
        self.model = (
            model
            if self.provider in ["openai", "ollama", "scayle-llm"]
            else f"{self.provider}/{model}"
        )
        self.request_model = self.model
        self.api_key = config.get("api_key", None)
        self.api_base = config.get("api_base", None)
        self.aws_credentials = config.get("aws_credentials", None)
        self.scayle_username = config.get("scayle_username")
        self.scayle_password = config.get("scayle_password")
        self.scayle_verify_ssl = config.get("scayle_verify_ssl")
        self.scayle_timeout = config.get("scayle_timeout")
        self.scayle_auth_client: Optional[ScayleAuthClient] = None
        self.track_tokens = config.get("track_tokens", True)
        self.track_cost = config.get("track_cost", True)
        self.input_cost_per_token = config.get("input_cost_per_token", None)
        self.output_cost_per_token = config.get("output_cost_per_token", None)
        self.max_input_tokens = config.get("max_input_tokens", None)
        self.max_output_tokens = config.get("max_output_tokens", None)
        self.max_tokens = config.get("max_tokens", None)
        self.extra_config = extra_config.copy()

        if self.provider == "scayle-llm":
            if not self.api_base:
                self.api_base = os.getenv("SCAYLE_BASE_URL")
            if not self.scayle_username:
                self.scayle_username = os.getenv("SCAYLE_USERNAME")
            if not self.scayle_password:
                self.scayle_password = os.getenv("SCAYLE_PASSWORD")
            if self.scayle_verify_ssl is None:
                verify_ssl_env = os.getenv("SCAYLE_VERIFY_SSL", "true").lower()
                self.scayle_verify_ssl = verify_ssl_env in ["1", "true", "yes", "on"]
            if not self.scayle_timeout:
                timeout_env = os.getenv("SCAYLE_TIMEOUT", "120")
                self.scayle_timeout = float(timeout_env)

            if not self.api_base:
                raise ValueError(
                    "SCAYLE_BASE_URL or api_base must be provided for scayle-llm"
                )
            if not self.scayle_username or not self.scayle_password:
                raise ValueError(
                    "SCAYLE_USERNAME and SCAYLE_PASSWORD (or explicit scayle_username/scayle_password) are required for scayle-llm"
                )

            self.scayle_auth_client = ScayleAuthClient(
                username=self.scayle_username,
                password=self.scayle_password,
                base_url=self.api_base,
                verify_ssl=bool(self.scayle_verify_ssl),
                timeout=float(self.scayle_timeout),
            )
            self.api_key = self.scayle_auth_client.authenticate()
            self.request_model = f"openai/{self.model}"

        self.logging_obj = CommonLLMLogging(
            log_config=config["log_config"],
            track_tokens=self.track_tokens,
            track_cost=self.track_cost,
            provider=self.provider,
            model=self.model,
        )
        self.logging_obj.input_cost_per_token = self.input_cost_per_token
        self.logging_obj.output_cost_per_token = self.output_cost_per_token

        if self.api_key:
            env_provider = (
                "OPENAI" if self.provider == "scayle-llm" else self.provider.upper()
            )
            os.environ[f"{env_provider}_API_KEY"] = self.api_key
            self.logging_obj.logger.debug(f"Set {env_provider}_API_KEY")
        if self.aws_credentials:
            os.environ["AWS_ACCESS_KEY_ID"] = self.aws_credentials.get(
                "access_key_id", ""
            )
            os.environ["AWS_SECRET_ACCESS_KEY"] = self.aws_credentials.get(
                "secret_access_key", ""
            )
            os.environ["AWS_REGION_NAME"] = self.aws_credentials.get("region", "")
            self.logging_obj.logger.debug("Set AWS env vars")

        self.enable_logging = enable_logging
        if self.enable_logging:
            litellm.callbacks = [self.logging_obj]

        self.logging_obj.logger.debug(
            f"Connector initialized: provider={self.provider}, model={self.model}, "
            f"request_model={self.request_model}, track_tokens={self.track_tokens}, track_cost={self.track_cost}"
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

    def _scayle_chat_direct(
        self,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Direct HTTP call to Scayle chat completions endpoint.
        This bypasses litellm to handle Scayle's non-standard OpenAI-like API path.
        Supports both text-only and vision (VLM) requests with images.

        For VLM requests, message content can be:
        - String: Simple text content
        - List: Mixed content with text and images, e.g.:
          [{"type": "text", "text": "..."},
           {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]
        """
        if not self.scayle_auth_client:
            raise ValueError("Scayle auth client not initialized")

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")
        top_p = kwargs.get("top_p")

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            data["max_tokens"] = max_tokens
        if top_p is not None:
            data["top_p"] = top_p

        data = {k: v for k, v in data.items() if v is not None}

        verify_ssl = (
            self.scayle_verify_ssl if self.scayle_verify_ssl is not None else True
        )
        timeout = self.scayle_timeout if self.scayle_timeout is not None else 120.0

        self.logging_obj.logger.debug(
            f"Scayle API request: model={self.model}, messages={len(messages)} message(s)"
        )

        response = requests.post(
            url,
            headers=headers,
            json=data,
            verify=verify_ssl,
            timeout=timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Scayle chat completion failed with status {response.status_code}: {response.text}"
            )

        return response.json()

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

        if self.provider == "scayle-llm":
            if stream:
                raise NotImplementedError(
                    "Streaming is not yet supported for scayle-llm provider"
                )

            try:
                scayle_response = self._scayle_chat_direct(message, **kwargs)
                # Convert Scayle response dict to ModelResponse object
                self.logging_obj.logger.debug(
                    f"Scayle chat completion response received for {self.provider}/{self.model}."
                )

                # Scayle returns OpenAI-compatible JSON, convert to ModelResponse
                model_response = ModelResponse(
                    id=scayle_response.get("id", ""),
                    choices=[
                        Choices(
                            finish_reason=choice.get("finish_reason", "stop"),
                            index=choice.get("index", 0),
                            message=Message(
                                content=choice["message"].get("content", ""),
                                role=choice["message"].get("role", "assistant"),
                            ),
                        )
                        for choice in scayle_response.get("choices", [])
                    ],
                    created=scayle_response.get("created", int(time.time())),
                    model=scayle_response.get("model", self.model),
                    object=scayle_response.get("object", "chat.completion"),
                    usage=Usage(
                        prompt_tokens=scayle_response.get("usage", {}).get(
                            "prompt_tokens", 0
                        ),
                        completion_tokens=scayle_response.get("usage", {}).get(
                            "completion_tokens", 0
                        ),
                        total_tokens=scayle_response.get("usage", {}).get(
                            "total_tokens", 0
                        ),
                    ),
                )
                return model_response
            except Exception as e:
                self.logging_obj.logger.error(
                    f"Scayle chat completion error for {self.provider}/{self.model}: {str(e)}"
                )
                raise RuntimeError(f"Scayle chat error: {str(e)}")

        try:
            config = {**self.extra_config, **kwargs}
            if self.api_base:
                config["api_base"] = self.api_base
            response = completion(
                model=self.request_model, messages=message, stream=stream, **config
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
    # Example usage with Scayle-LLM
    connector = CommonLLMConnector(
        provider="scayle-llm",
        model="llama-3.3",
        config_file="dataset_profiler/common_llm/configs/llm_config.yaml",
    )
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2 + 2?"},
    ]
    response = connector.chat(messages, stream=False)
    if isinstance(response, ModelResponse):
        if response.choices and hasattr(response.choices[0], 'message'):
            content = response.choices[0].message.content  # type: ignore
            print("Chat Response:", content)
        else:
            print("Chat Response: No content in response")
    else:
        print("Chat Response:", response)
