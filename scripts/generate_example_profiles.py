"""Regenerate the example profiles shared with the MoMa team.

Run with the SCAYLE VPN up, otherwise semantic type annotation and data quality
detection fail silently and their fields come out empty:

    ENABLE_DATA_QUALITY=1 python scripts/generate_example_profiles.py
"""

import json
import os
import sys
from pathlib import Path

from dataset_profiler.profile_models import DatasetProfile

OUT = Path("moma-issues/example-profiles")

# Write profiles even when the LLM-backed fields came back empty.
ALLOW_DEGRADED = "--allow-degraded" in sys.argv

# Minimum share of columns that must carry a semanticType for a profile to be
# considered good enough to publish.
MIN_COVERAGE = 0.95


def _previous_coverage(path: Path) -> float:
    """How well annotated the file already on disk is, or 0.0 if there isn't one."""
    if not path.exists():
        return 0.0
    try:
        existing = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return 0.0
    report = audit(existing)
    return report["with_semanticType"] / report["fields"] if report["fields"] else 0.0

# Datasets mirroring the fixtures under moma-management/assets/profiles.
# meteo_era5land is omitted: it profiles a live Postgres, not files on disk.
DATASETS = {
    "mathe": "tests/assets/mathe_assessment/specifications.json",
    "isco_taxonomy": "tests/assets/isco_taxonomy/specification.json",
    "esco": "tests/assets/esco/specifications.json",
}


def audit(profile: dict) -> dict:
    """Report the fields that differ from the older MoMa fixtures."""
    fields, annotated, stats_ok, with_dq = 0, 0, 0, 0
    for rs in profile.get("recordSet", []):
        if "dataQuality" in rs:
            with_dq += 1
        for f in rs.get("field", []):
            fields += 1
            if f.get("semanticType"):
                annotated += 1
            if "variance" in (f.get("statistics") or {}):
                stats_ok += 1
    return {
        "prefixed_keys_present": any(k.startswith(("dg:", "sc:")) for k in profile),
        "fields": fields,
        "with_semanticType": annotated,
        "with_new_statistics": stats_ok,
        "recordSets_with_dataQuality": with_dq,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # Optional positional args select a subset. ESCO alone takes ~45 minutes
    # (144 annotations plus detection on 16 record sets), so it is often worth
    # running on its own.
    wanted = [a for a in sys.argv[1:] if not a.startswith("-")]
    datasets = {k: v for k, v in DATASETS.items() if not wanted or k in wanted}
    if wanted and not datasets:
        print(f"  no such dataset(s): {wanted}. known: {sorted(DATASETS)}")
        return 1

    failures = 0
    for name, spec_path in datasets.items():
        if not Path(spec_path).exists():
            print(f"  {name}: spec not found at {spec_path}, skipping")
            continue
        spec = json.loads(Path(spec_path).read_text())
        try:
            profile = DatasetProfile(spec)
        except Exception as e:                      # noqa: BLE001 - reported, not raised
            print(f"  {name}: FAILED {type(e).__name__}: {e}")
            failures += 1
            continue

        heavy = profile.to_dict()
        report = audit(heavy)
        target = OUT / f"{name}_heavy.json"

        # Both LLM-backed features fail silently by design, so an unreachable
        # endpoint yields a profile that looks complete but has no semanticType
        # and no dataQuality. Writing that over a good file loses real output and
        # is invisible afterwards, so refuse unless explicitly asked.
        # Annotation failures are per record set, and a single gateway 504 loses
        # every column in that record set. A run can therefore come back mostly
        # annotated and still be worse than the file already on disk, so compare
        # the coverage rather than just checking for zero.
        covered = report["with_semanticType"] / report["fields"] if report["fields"] else 1.0
        previous = _previous_coverage(target)
        if report["fields"] and covered < min(MIN_COVERAGE, previous) and not ALLOW_DEGRADED:
            print(f"  {name}_heavy.json  SKIPPED - only {report['with_semanticType']}/"
                  f"{report['fields']} columns annotated ({covered:.0%}); "
                  f"file on disk has {previous:.0%}")
            print(f"     {target} left untouched. Re-run with --allow-degraded to overwrite.")
            failures += 1
            continue

        target.write_text(json.dumps(heavy, indent=2, ensure_ascii=False))
        print(f"  {name}_heavy.json  {report}")
    return failures


if __name__ == "__main__":
    sys.exit(main())
