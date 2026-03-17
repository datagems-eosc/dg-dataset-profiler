import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv, find_dotenv

from dataset_profiler.common_llm.connector import CommonLLMConnector
from dataset_profiler.common_llm.scayle_auth import ScayleAuthClient


def _read_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    if value is None:
        return None
    return value.strip('"').strip("'")


def main() -> None:
    load_dotenv(find_dotenv())

    base_url = _read_env("SCAYLE_BASE_URL")
    username = _read_env("SCAYLE_USERNAME")
    password = _read_env("SCAYLE_PASSWORD")
    verify_ssl_raw = (_read_env("SCAYLE_VERIFY_SSL", "true") or "true").lower()
    verify_ssl = verify_ssl_raw in {"1", "true", "yes", "on"}

    if not base_url or not username or not password:
        raise RuntimeError(
            "Missing SCAYLE_BASE_URL, SCAYLE_USERNAME, or SCAYLE_PASSWORD in environment"
        )

    print("=== Scayle Connection Test ===")
    print(f"Base URL: {base_url}")
    print(f"Username: {username}")
    print(f"Verify SSL: {verify_ssl}")
    print()

    auth_client = ScayleAuthClient(
        username=username,
        password=password,
        base_url=base_url,
        verify_ssl=verify_ssl,
        timeout=30.0,
    )

    print("1. Checking connection...")
    if not auth_client.check_connection():
        print("   ⚠️ SKIPPED: Scayle endpoint is not reachable (VPN/network issue).")
        print(
            "   The test will continue to demonstrate the auth and connector API design."
        )
        print()
    else:
        print("   ✓ Connection successful")
        print()

    print("2. Authenticating...")
    try:
        api_key = auth_client.authenticate()
        print(f"   ✓ Authenticated. Token prefix: {api_key[:12]}...")
    except Exception as e:
        print(f"   ✗ Authentication failed: {e}")
        print()
        print("This is expected if the endpoint is not reachable.")
        return
    print()

    print("3. Fetching available models...")
    try:
        models = auth_client.list_models()
        if not models:
            print("  ⚠  No models returned by Scayle API")
            return
        print(f"   ✓ Found {len(models)} model(s)")
        for model_id in models[:5]:
            print(f"     - {model_id}")
    except Exception as e:
        print(f"   ✗ Failed to list models: {e}")
        return
    print()

    test_model = models[0]
    print(f"4. Running chat completion with model: {test_model}")

    try:
        connector = CommonLLMConnector(
            provider="scayle-llm",
            model=test_model,
            api_base=base_url,
            scayle_username=username,
            scayle_password=password,
            scayle_verify_ssl=verify_ssl,
            track_tokens=True,
            track_cost=False,
        )

        messages = [
            {"role": "system", "content": "You are a concise assistant."},
            {
                "role": "user",
                "content": "Reply with one short sentence proving the connection works.",
            },
        ]

        response = connector.chat(messages, stream=False)
        # Scayle returns raw dict with OpenAI-compatible structure
        content_val: str = ""
        usage_val: Dict[str, Any] = {}

        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices and isinstance(choices, list):
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    message_data = first_choice.get("message", {})
                    if isinstance(message_data, dict):
                        content_val = message_data.get("content", "")
            usage_data = response.get("usage", {})
            if isinstance(usage_data, dict):
                usage_val = usage_data
        else:
            content_val = response.choices[0].message["content"]  # type: ignore[index, union-attr]
            usage_obj = getattr(response, "usage", None)
            if usage_obj and hasattr(usage_obj, "model_dump"):
                usage_val = usage_obj.model_dump()  # type: ignore[union-attr]

        print("   ✓ Response:")
        print(f"     {content_val}")
        print()
        print("   Usage:")
        print(f"     {json.dumps(usage_val, indent=2)}")
    except Exception as e:
        print(f"   ✗ Chat completion failed: {e}")
        print()
        print("This is expected if the endpoint is not reachable.")
        return


if __name__ == "__main__":
    main()
