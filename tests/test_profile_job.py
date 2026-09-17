"""The profiling job must extract record sets once, not once per profile shape."""

import json

import pandas as pd

from dataset_profiler import profile_models
from dataset_profiler.job_manager import profile_job as job_module
from dataset_profiler.profile_components import dateset_top_level, distribution


def test_record_sets_are_extracted_exactly_once(tmp_path, monkeypatch):
    """extract_record_sets() returns its result without storing it. The job used to
    call it and discard the result, then to_dict() extracted all over again --
    every job ran semantic annotation and data quality detection twice."""
    data = tmp_path / "data"
    data.mkdir()
    pd.DataFrame({"id": range(20), "city": ["Athens", "Patras"] * 10}).to_csv(
        data / "t.csv", index=False
    )

    # Resolve the connector path as given, independent of the developer's .env.
    for module in (profile_models, distribution, dateset_top_level):
        monkeypatch.setattr(module, "DATASET_ROOT_PATH", "", raising=False)
    monkeypatch.setenv("CDD_PROFILE_PATH", f"{tmp_path}/")
    for name in ("store_job_status", "store_job_response", "store_cdd_profile_path"):
        monkeypatch.setattr(job_module, name, lambda *a, **k: None)

    calls = []
    original = profile_models.DatasetProfile.extract_record_sets

    def counting(self):
        calls.append(1)
        return original(self)

    monkeypatch.setattr(profile_models.DatasetProfile, "extract_record_sets", counting)

    spec = {
        "id": "11111111-1111-4111-8111-111111111111",
        "name": "t", "description": "", "headline": "", "citeAs": "", "country": "GR",
        "datePublished": "2026-09-16", "fieldOfScience": [], "inLanguage": ["en"],
        "keywords": [], "license": "CC0", "url": "", "access": "", "uploadedBy": "ADMIN",
        "data_connectors": [{"type": "RawDataPath", "dataset_id": f"{data}/"}],
    }
    # The remote wrapper needs a Ray cluster; the plain function does not.
    job_module.profile_job._function("job", spec)

    assert len(calls) == 1
    cdd = json.loads((tmp_path / f"{spec['id']}.json").read_text())
    assert cdd  # both profile shapes were still produced from the single extraction
