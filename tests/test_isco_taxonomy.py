import json

from dataset_profiler.profile_models import DatasetProfile


def test_isco_taxonomy():
    profile = DatasetProfile(
        dataset_specifications_path="tests/assets/isco_taxonomy/specification.json",
    )
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    with open("generated_profiles/isco_taxonomy.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
