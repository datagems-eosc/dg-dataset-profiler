"""End-to-end profiling tests against the running Dataset Profiler API.

Each test submits a real profiling job for a configured dataset and asserts on
the light and heavy profiles returned by the API. The job is dispatched to the
Ray cluster, so the first submission after a cold start can take a while
(handled by the generous JOB_TIMEOUT_SECONDS in config).
"""
import pytest

from integration_tests import config

# Reuse a single completed job per dataset across the assertions below instead of
# re-profiling for every test, since profiling is the expensive part.
_COMPLETED_JOBS: dict[str, dict] = {}


def _profile_dataset(client, dataset: dict) -> dict:
    """Submit (once per dataset) and return the full profile response."""
    if dataset["id"] in _COMPLETED_JOBS:
        return _COMPLETED_JOBS[dataset["id"]]

    job_id = client.trigger_profile(config.build_request(dataset))
    status = client.wait_for_completion(job_id)
    assert status == "heavy_profile_ready", (
        f"{dataset['id']} ended in status {status!r}, expected heavy_profile_ready"
    )

    profile = client.get_profile(job_id)
    result = {"job_id": job_id, "profile": profile}
    _COMPLETED_JOBS[dataset["id"]] = result
    return result


@pytest.fixture(params=config.DATASETS, ids=[d["id"] for d in config.DATASETS])
def dataset(request):
    return request.param


def test_dataset_path_exists_locally(dataset):
    """Sanity check that the configured data path points at a real dataset.

    Guards against config drift: the path sent to the API (relative to
    tests/assets) must correspond to a directory that actually contains files.
    """
    local_path = config.LOCAL_ASSETS_ROOT / dataset["data_path"]
    assert local_path.is_dir(), f"Dataset directory does not exist: {local_path}"
    assert any(local_path.iterdir()), f"Dataset directory is empty: {local_path}"


def test_light_profile(client, dataset):
    """The light profile lists the expected distribution files."""
    profile = _profile_dataset(client, dataset)["profile"]
    light = profile["moma_profile_light"]

    assert light.get("name") == dataset["name"]
    assert light["@type"] == "sc:Dataset"

    file_names = {dist.get("name") for dist in light.get("distribution", [])}
    for expected_file in dataset["expected_files"]:
        assert expected_file in file_names, (
            f"{dataset['id']}: expected file {expected_file!r} not in {file_names}"
        )


def test_heavy_profile_record_set(client, dataset):
    """The heavy profile contains the expected record set and fields."""
    profile = _profile_dataset(client, dataset)["profile"]
    heavy = profile["moma_profile_heavy"]

    record_sets = {rs["name"]: rs for rs in heavy.get("recordSet", [])}
    assert dataset["expected_record_set"] in record_sets, (
        f"{dataset['id']}: record set {dataset['expected_record_set']!r} "
        f"not in {list(record_sets)}"
    )

    rs = record_sets[dataset["expected_record_set"]]
    field_names = {field["name"] for field in rs.get("field", [])}
    for expected_field in dataset["expected_fields_contain"]:
        assert expected_field in field_names, (
            f"{dataset['id']}: expected field {expected_field!r} not in {field_names}"
        )


def test_cdd_profile_path_available(client, dataset):
    """Once the heavy profile is ready, the CDD profile path is retrievable."""
    _profile_dataset(client, dataset)  # ensure the job has completed
    cdd_path = client.cdd_profile_path(dataset["dataset_id"])
    assert cdd_path is not None, f"{dataset['id']}: CDD profile path not available"
    assert cdd_path.endswith(f"{dataset['dataset_id']}.json")
