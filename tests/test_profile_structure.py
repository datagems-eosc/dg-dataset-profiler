"""Structure regression test (handoff 12c, Rule 1 / decision D17).

Many components read the profiler's output, so its structure must not change:
the same key paths, the same nesting, the same kinds of value. The baseline in
``tests/data/profile_structure_baseline.json`` is the structure of the fixed
test dataset (``tests/profile_structure.py``) as profiled by ``main`` at
58ff794, before the statistics fixes.

Allowed differences, and only these:

- under a ``statistics`` node, a number or string becoming null (numeric
  statistics of columns that became ``sc:Text``; ``uniqueCount`` over budget);
- ``sample`` items: missing values are no longer sampled, and samples of
  ``sc:Text`` columns hold strings (``"01234"``), so their kinds may change
  to strings or lose null, and an all-missing column's sample may be empty.

To regenerate the baseline after an intended, agreed structural change, run
``python tests/profile_structure.py tests/data/profile_structure_baseline.json``.
"""

import json
from pathlib import Path

from tests.profile_structure import profile_structure

BASELINE = Path(__file__).parent / "data" / "profile_structure_baseline.json"
PRIMITIVES = {"null", "boolean", "number", "string"}


def _allowed(path: str, old: list, new: list) -> bool:
    if old == new:
        return True
    if path.endswith(".sample[]"):
        return set(new) <= (set(old) | {"string"}) - {"null"} and set(new) <= PRIMITIVES
    if ".statistics." in path:
        return new == ["null"] and set(old) <= PRIMITIVES
    return False


def structure_differences(old: dict, new: dict) -> list:
    problems = []
    for profile in sorted(set(old) | set(new)):
        before, after = old.get(profile, {}), new.get(profile, {})
        for path in sorted(set(before) | set(after)):
            if path not in after:
                if not path.endswith(".sample[]"):
                    problems.append(f"{profile}: {path} is gone (was {before[path]})")
            elif path not in before:
                problems.append(f"{profile}: {path} is new ({after[path]})")
            elif not _allowed(path, before[path], after[path]):
                problems.append(f"{profile}: {path} changed {before[path]} -> {after[path]}")
    return problems


def test_profile_structure_is_unchanged(tmp_path):
    baseline = json.loads(BASELINE.read_text())
    current = profile_structure(tmp_path)
    problems = structure_differences(baseline, current)
    assert not problems, "Profile structure changed (Rule 1):\n" + "\n".join(problems)


def test_the_check_catches_structural_changes():
    old = {"moma": {"$.a": ["object"], "$.a.statistics.mean": ["number"], "$.a.dataType": ["string"]}}
    assert structure_differences(old, old) == []
    assert structure_differences(old, {"moma": {**old["moma"], "$.a.new": ["string"]}})
    assert structure_differences(old, {"moma": {"$.a": ["object"], "$.a.dataType": ["string"]}})
    assert structure_differences(old, {"moma": {**old["moma"], "$.a.dataType": ["null"]}})
    assert not structure_differences(old, {"moma": {**old["moma"], "$.a.statistics.mean": ["null"]}})
    assert structure_differences(old, {"moma": {**old["moma"], "$.a.statistics.mean": ["string"]}})
