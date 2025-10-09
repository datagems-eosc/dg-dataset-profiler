import json

from dataset_profiler.profile_models import DatasetProfile


def test_encyc_net():
    profile = DatasetProfile(
        dataset_specifications_path="tests/assets/encyc_net/specification.json",
    )
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    with open("generated_profiles/encyc_net.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
