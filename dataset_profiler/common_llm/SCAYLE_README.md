# Scayle-LLM Provider for CommonLLMConnector

This integration adds support for [Scayle Chat API](https://chat.scayle.es) to the `common_llm` module, using LDAP authentication and OpenAI-compatible chat completion endpoints.

## Files Added

- **`scayle_auth.py`**: Handles LDAP authentication, token retrieval, and model listing
- **`scayle_connection_test.py`**: Comprehensive test script to verify connection, authentication, and chat completion
- **`example_scayle_with_config.py`**: Simple example showing config file usage with env var substitution
- **`config_handler.py`** (enhanced): Now supports `${VAR}` environment variable substitution in YAML configs

## Configuration

### Environment Variables

Add these to your `.env` file (root of your dataset-profiler project):

```env
SCAYLE_USERNAME="your-scayle-username"
SCAYLE_PASSWORD="your-scayle-password"
SCAYLE_BASE_URL=https://172.16.59.5:32443/api
SCAYLE_VERIFY_SSL=false
```

### YAML Configuration

The YAML config file uses environment variable substitution with `${VAR}` syntax:

```yaml
scayle-llm:
  api_base: "${SCAYLE_BASE_URL}"
  username: "${SCAYLE_USERNAME}"
  password: "${SCAYLE_PASSWORD}"
  verify_ssl: "${SCAYLE_VERIFY_SSL}"
  timeout: 30
  tracking:
    track_tokens: true
    track_cost: true
```

**Note**: Credentials are automatically loaded from `.env` - no need to duplicate them in YAML! Just ensure the `.env` file is loaded before importing `CommonLLMConnector`. We recommend keeping sensitive credentials in `.env` and using YAML for non-sensitive configuration.

## Usage

### Using Config File (Recommended)

The simplest approach - credentials automatically loaded from `.env`:

```python
from dotenv import load_dotenv, find_dotenv
from dataset_profiler.common_llm import CommonLLMConnector

# Load .env file
load_dotenv(find_dotenv())

# Config file automatically substitutes ${SCAYLE_USERNAME}, ${SCAYLE_PASSWORD}, etc.
connector = CommonLLMConnector(
    provider="scayle-llm",
    model="kimi-k2.5",
    config_file="dataset_profiler/common_llm/configs/llm_config.yaml",
)

messages = [{"role": "user", "content": "What is 2+2?"}]
response = connector.chat(messages)
print(response["choices"][0]["message"]["content"])
```

See [example_scayle_with_config.py](example_scayle_with_config.py) for a complete working example.

### Programmatic (Without Config File)

If you prefer to pass credentials directly:

```python
import os
from dataset_profiler.common_llm import CommonLLMConnector

connector = CommonLLMConnector(
    provider="scayle-llm",
    model="kimi-k2.5",
    api_base=os.getenv("SCAYLE_BASE_URL"),
    scayle_username=os.getenv("SCAYLE_USERNAME"),
    scayle_password=os.getenv("SCAYLE_PASSWORD"),
    scayle_verify_ssl=False,
    track_tokens=True,
)

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"},
]

response = connector.chat(messages, stream=False)
print(response["choices"][0]["message"]["content"])
```

### Running the Connection Test

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Run the comprehensive test script
python -m dataset_profiler.common_llm.scayle_connection_test

# Or run the simple config file example
python -m dataset_profiler.common_llm.example_scayle_with_config
```

Expected output:

```text
=== Scayle Connection Test ===
Base URL: https://172.16.59.5:32443/api
Username: your-username
Verify SSL: False

1. Checking connection...
   ✓ Connection successful

2. Authenticating...
   ✓ Authenticated. Token prefix: eyJhbGciOiJI...

3. Fetching available models...
   ✓ Found 4 model(s)
     - kimi-k2.5
     - llama-3.3
     - qwen3
     - glm-flash

4. Running chat completion with model: kimi-k2.5
   ✓ Response:
     The connection works.

   Usage:
     {
       "completion_tokens": 124,
       "prompt_tokens": 28,
       "total_tokens": 152
     }
```

## Implementation Details

### Authentication Flow

1. Credentials are loaded from environment variables or config file
2. `ScayleAuthClient` sends a POST request to `/v1/auths/ldap` with username/password
3. Bearer token is retrieved and cached
4. Token is used in subsequent API calls (`/models` and `/chat/completions`)

### Direct HTTP Chat Calls

Unlike other providers in `CommonLLMConnector` that use `litellm.completion()`, the `scayle-llm` provider bypasses litellm for chat completions. This is because:

- Scayle's chat endpoint is at `{base_url}/chat/completions` (not `/v1/chat/completions`)
- Direct requests.post ensures compatibility with Scayle's specific OpenAI-compatible structure

### Streaming Support

Streaming is not yet implemented for `scayle-llm`. Calling `chat(stream=True)` will raise a `NotImplementedError`.

## Differences from langchain-scayle

This integration is **not** dependent on LangChain. It:

- Uses the same authentication pattern as `langchain-scayle`
- Works directly with `litellm` (for most providers) and raw `requests` (for Scayle)
- Returns raw dict responses for Scayle (OpenAI-compatible JSON structure)
- Integrates seamlessly with existing `CommonLLMConnector` tracking/logging features

## Troubleshooting

### SSL Certificate Errors

If you see `[SSL: CERTIFICATE_VERIFY_FAILED]`, set `SCAYLE_VERIFY_SSL=false` in your `.env` file.

### Connection Timeouts

Ensure you are connected to the required VPN if Scayle is behind an internal network.

### Model Not Available

Check available models by running the connection test script. Some models may be temporarily unavailable.

## Future Enhancements

- [ ] Add streaming support for scayle-llm
- [ ] Add retry logic for authentication token expiration
- [ ] Support tool calling for compatible Scayle models
- [ ] Add cost tracking for Scayle models
