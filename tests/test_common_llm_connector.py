import pytest
import logging
import pydantic
from unittest.mock import patch, MagicMock
from typing import Dict, List, Optional
from litellm.types.utils import ModelResponse, Choices, Delta, Usage
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.exceptions import AuthenticationError, RateLimitError
from common_llm.connector import (
    CommonLLMConnector,
    LLMConfig,
    load_llm_config,
    setup_logger,
    CommonLLMLogging,
)




@pytest.fixture
def sample_config():
    """Fixture for a sample configuration dictionary."""
    return {
        "ollama": {
            "api_key": "ollama-key",
            "api_base": "http://localhost:11434",
            "tracking": {"track_tokens": True, "track_cost": True},
            "ollama/gpt-oss:120b": {
                "cost_per_token": {
                    "prompt_cost_per_1M_tokens": 1000,
                    "completion_cost_per_1M_tokens": 2000,
                }
            },
        },
        "openai": {
            "api_key": "openai-key",
            "tracking": {"track_tokens": True, "track_cost": True},
            "gpt-3.5-turbo": {
                "cost_per_token": {
                    "prompt_cost_per_1M_tokens": 1500,
                    "completion_cost_per_1M_tokens": 3000,
                }
            },
        },
        "bedrock": {
            "aws_credentials": {
                "access_key_id": "aws-access-key",
                "secret_access_key": "aws-secret-key",
                "region": "us-west-2",
            },
            "tracking": {"track_tokens": True, "track_cost": True},
        },
        "logging": {"level": "DEBUG", "log_path": "/tmp/logs"},
    }


@pytest.fixture
def mock_load_config(sample_config):
    """Mock load_config to return sample_config."""
    with patch("common_llm.connector.load_config", return_value=sample_config) as mock:
        yield mock


@pytest.fixture
def mock_completion():
    """Mock litellm.completion for non-streaming and streaming responses."""
    with patch("common_llm.connector.completion") as mock:
        # Mock non-streaming response
        non_stream_response = ModelResponse(
            choices=[Choices(message={"content": "Hello, I'm a helpful assistant!"})],
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        # Mock streaming response
        stream_chunks = [
            ModelResponse(choices=[Choices(delta=Delta(content="Hello, "))]),
            ModelResponse(choices=[Choices(delta=Delta(content="I'm a "))]),
            ModelResponse(choices=[Choices(delta=Delta(content="helpful assistant!"))]),
        ]

        def stream_gen():
            for chunk in stream_chunks:
                yield chunk

        stream_response = CustomStreamWrapper(
            completion_stream=stream_gen(),
            model="ollama/gpt-oss:120b",
            logging_obj=MagicMock(),
        )
        mock.side_effect = lambda *args, **kwargs: (
            stream_response if kwargs.get("stream") else non_stream_response
        )
        yield mock


def test_ollama_initialization(mock_load_config, sample_config, tmp_path):
    """Test initialization of CommonLLMConnector with ollama provider."""
    connector = CommonLLMConnector(
        provider="ollama", model="ollama/gpt-oss:120b", config_file="config.yaml"
    )
    assert connector.provider == "ollama"
    assert connector.model == "ollama/gpt-oss:120b"
    assert connector.api_key == "ollama-key"
    assert connector.api_base == "http://localhost:11434"
    assert connector.track_tokens is True
    assert connector.track_cost is True
    assert connector.input_cost_per_token == 1000 / 1e6
    assert connector.output_cost_per_token == 2000 / 1e6


def test_openai_initialization(mock_load_config, sample_config):
    """Test initialization with mocked openai provider."""
    with patch("os.environ", {}) as mock_env:
        connector = CommonLLMConnector(
            provider="openai", model="gpt-3.5-turbo", config_file="config.yaml"
        )
        assert connector.provider == "openai"
        assert connector.model == "gpt-3.5-turbo"  # openai does not prefix provider
        assert connector.api_key == "openai-key"
        assert mock_env["OPENAI_API_KEY"] == "openai-key"
        assert connector.input_cost_per_token == 1500 / 1e6
        assert connector.output_cost_per_token == 3000 / 1e6


def test_bedrock_initialization(mock_load_config, sample_config):
    """Test initialization with mocked AWS Bedrock provider."""
    with patch("os.environ", {}) as mock_env:
        connector = CommonLLMConnector(
            provider="bedrock", model="some-model", config_file="config.yaml"
        )
        assert connector.provider == "bedrock"
        assert connector.model == "bedrock/some-model"
        assert connector.aws_credentials == {
            "access_key_id": "aws-access-key",
            "secret_access_key": "aws-secret-key",
            "region": "us-west-2",
        }
        assert mock_env["AWS_ACCESS_KEY_ID"] == "aws-access-key"
        assert mock_env["AWS_SECRET_ACCESS_KEY"] == "aws-secret-key"
        assert mock_env["AWS_REGION_NAME"] == "us-west-2"


def test_ollama_chat_non_streaming(
    mock_completion, mock_load_config, sample_config, caplog
):
    """Test non-streaming chat completion with ollama."""
    caplog.set_level(logging.DEBUG)
    connector = CommonLLMConnector(
        provider="ollama", model="ollama/gpt-oss:120b", config_file="config.yaml"
    )
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me about yourself."},
    ]
    response = connector.chat(messages, stream=False)
    assert isinstance(response, ModelResponse)

    assert response.choices[0].message["content"] == "Hello, I'm a helpful assistant!" # type: ignore
    assert response.usage.prompt_tokens == 10 # type: ignore
    assert response.usage.completion_tokens == 20 # type: ignore
    assert response.usage.total_tokens == 30 # type: ignore
    assert (
        "Starting chat completion for ollama/ollama/gpt-oss:120b with stream=False"
        in caplog.text
    )
    assert (
        "Chat completion response Hello, I'm a helpful assistant! received"
        in caplog.text
    )


def test_ollama_chat_streaming(
    mock_completion, mock_load_config, sample_config, caplog
):
    """Test streaming chat completion with ollama."""
    caplog.set_level(logging.DEBUG)
    connector = CommonLLMConnector(
        provider="ollama", model="gpt-oss:120b", config_file="config.yaml"
    )
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me about yourself."},
    ]
    response = connector.chat(messages, stream=True)
    assert isinstance(response, CustomStreamWrapper)
    content = connector.process_streaming_response(response)
    assert content == "Hello, I'm a helpful assistant!"
    assert (
        "Starting chat completion for ollama/gpt-oss:120b with stream=True"
        in caplog.text
    )
    assert "Streaming chat completion response received" in caplog.text


def test_invalid_provider(mock_load_config):
    """Test initialization with invalid provider."""
    with pytest.raises(ValueError, match="Provider must be a non-empty string"):
        CommonLLMConnector(provider="", model="gpt-oss:120b")


def test_chat_authentication_error(
    mock_completion, mock_load_config, sample_config, caplog
):
    """Test handling of AuthenticationError in chat method."""
    mock_completion.side_effect = AuthenticationError(
        message="Invalid API key", llm_provider="ollama", model="gpt-oss:120b"
    )
    connector = CommonLLMConnector(
        provider="ollama", model="gpt-oss:120b", config_file="config.yaml"
    )
    messages = [{"role": "user", "content": "Hello"}]
    with pytest.raises(ValueError, match="Invalid credentials for ollama"):
        connector.chat(messages)
    assert "Authentication failed for ollama/gpt-oss:120b" in caplog.text


def test_chat_rate_limit_error(
    mock_completion, mock_load_config, sample_config, caplog
):
    """Test handling of RateLimitError in chat method."""
    mock_completion.side_effect = RateLimitError(
        message="Rate limit exceeded", llm_provider="ollama", model="gpt-oss:120b"
    )
    connector = CommonLLMConnector(
        provider="ollama", model="gpt-oss:120b", config_file="config.yaml"
    )
    messages = [{"role": "user", "content": "Hello"}]
    with pytest.raises(RuntimeError, match="Rate limit exceeded"):
        connector.chat(messages)
    assert "Rate limit exceeded for ollama/gpt-oss:120b" in caplog.text


def test_process_streaming_response(mock_completion, mock_load_config, sample_config):
    """Test process_streaming_response with mocked streaming response."""
    connector = CommonLLMConnector(
        provider="ollama", model="gpt-oss:120b", config_file="config.yaml"
    )
    stream_chunks = [
        ModelResponse(choices=[Choices(delta=Delta(content="Hello, "))]),
        ModelResponse(choices=[Choices(delta=Delta(content="world!"))]),
    ]

    def stream_gen():
        for chunk in stream_chunks:
            yield chunk

    stream_response = CustomStreamWrapper(
        completion_stream=stream_gen(),
        model="ollama/gpt-oss:120b",
        logging_obj=MagicMock(),
    )
    content = connector.process_streaming_response(stream_response)
    assert content == "Hello, world!"


def test_logging_without_config(mock_completion, caplog):
    """Test logging behavior without config file."""
    caplog.set_level(logging.DEBUG)
    connector = CommonLLMConnector(
        provider="ollama",
        model="ollama/gpt-oss:120b",
        track_tokens=True,
        track_cost=False,
    )
    messages = [{"role": "user", "content": "Hello"}]
    response = connector.chat(messages, stream=False)
    # since default level is INFO. we should have ""
    assert not (
        "Starting chat completion for ollama/gpt-oss:120b with stream=False"
        in caplog.text
    )
