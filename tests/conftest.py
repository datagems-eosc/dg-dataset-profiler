"""Shared test configuration.

Two code paths in the profiler reach for an LLM over the network, and both are
switched on by whatever happens to sit in the developer's ``.env``:

* semantic type annotation (:class:`ColumnTypeAnnotator`) runs for every CSV
  record set, one request per column. The fixtures under ``tests/assets`` hold
  78 CSVs totalling 1662 columns, which pushed a full run past 25 minutes.
* data quality detection runs whenever ``ENABLE_DATA_QUALITY`` is truthy, which
  the local ``.env`` sets to ``1``.

Both are neutralised here by default, so the suite is fast, deterministic, and
runnable with the VPN down. Tests that genuinely want the real service opt back
in per test with the ``live_llm`` / ``live_data_quality`` markers, and a whole
run can go live with ``TESTS_LIVE_LLM=1``.
"""

import os

import pytest

_LIVE_ENV_FLAG = "TESTS_LIVE_LLM"


def _live_run_requested() -> bool:
    return os.environ.get(_LIVE_ENV_FLAG, "").lower() in ("1", "true", "yes", "on")


@pytest.fixture(autouse=True)
def stub_column_type_annotator(request, monkeypatch):
    """Keep semantic type annotation off the network.

    The annotator's methods are patched on the class, so modules that imported
    ``ColumnTypeAnnotator`` directly are covered too.
    """
    if _live_run_requested() or "live_llm" in request.keywords:
        return

    from dataset_profiler.profile_components import cta

    monkeypatch.setattr(
        cta.ColumnTypeAnnotator, "__init__", lambda self, *args, **kwargs: None
    )
    monkeypatch.setattr(
        cta.ColumnTypeAnnotator, "annotate_columns", lambda self, *args, **kwargs: {}
    )


@pytest.fixture(autouse=True)
def disable_data_quality(request, monkeypatch):
    """Pin data quality detection off regardless of the developer's .env.

    Set explicitly rather than deleted: ``cta.py`` calls ``load_dotenv()`` at
    import time, which would reinstate the variable if it were merely absent.
    Tests that want it on set it themselves, and their own ``setenv`` runs
    after this fixture.
    """
    if _live_run_requested() or "live_data_quality" in request.keywords:
        return

    monkeypatch.setenv("ENABLE_DATA_QUALITY", "false")
