import json

import pytest

from dataset_profiler.profile_models import DatasetProfile

# Profiles a full dataset kept only locally under tests/assets (git-ignored); not run in CI.
pytestmark = pytest.mark.local_dataset


def test_diderot():
    with open("tests/assets/diderot/specification.json") as json_file:
        spec = json.load(json_file)

    profile = DatasetProfile(spec)
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    with open("generated_profiles/diderot.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
