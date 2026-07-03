import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Union

# Hard limit on how long an LLM-generated detection script may run.
SCRIPT_TIMEOUT_SECONDS = 120


def _extract_code(raw: str) -> str:
    """Strip markdown code fences if the LLM included them."""
    match = re.search(r"```(?:python)?\n(.*?)```", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw.strip()


def execute_detection_script(
    script_code: str, file_path: Union[Path, str]
) -> List[dict]:
    """Write the LLM-generated script to a temp file, run it, and parse JSON output."""
    clean_code = _extract_code(script_code)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(clean_code)
        script_path = Path(f.name)

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), str(file_path)],
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Detection script exited with code {result.returncode}.\n"
                f"stderr:\n{result.stderr}"
            )

        stdout = result.stdout.strip()
        if not stdout:
            return []

        return json.loads(stdout)

    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Detection script produced invalid JSON.\nOutput:\n{result.stdout}\nError: {e}"
        )
    finally:
        script_path.unlink(missing_ok=True)
