"""
Example: Using scayle-llm provider with config file (environment variable substitution).

This demonstrates how credentials from .env are automatically substituted
into the YAML config using ${VAR} syntax.
"""

import os
from dotenv import load_dotenv, find_dotenv
from dataset_profiler.common_llm import CommonLLMConnector

# Load environment variables from .env
load_dotenv(find_dotenv())

# Initialize connector with config file
# Credentials will be loaded from llm_config.yaml which references ${SCAYLE_USERNAME}, etc.
connector = CommonLLMConnector(
    provider="scayle-llm",
    model="kimi-k2.5",
    config_file="dataset_profiler/common_llm/configs/llm_config.yaml",
    track_tokens=True,
)

messages = [
    {"role": "system", "content": "You are a concise assistant."},
    {"role": "user", "content": "What is 2+2?"},
]

print("Sending chat request using config file with env var substitution...")
response = connector.chat(messages, stream=False)

content = ""
usage = {}

if isinstance(response, dict):
    choices = response.get("choices", [])
    if choices and isinstance(choices, list):
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message_dict = first_choice.get("message", {})
            if isinstance(message_dict, dict):
                content = message_dict.get("content", "")
    usage_dict = response.get("usage", {})
    if isinstance(usage_dict, dict):
        usage = usage_dict
else:
    content = response.choices[0].message["content"]  # type: ignore

print(f"\nResponse: {content}")
print(f"Tokens used: {usage}")
