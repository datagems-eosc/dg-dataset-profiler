from dataset_profiler.profile_models import DatasetProfile


def test_profiler_esco():
    profile = DatasetProfile(
        dataset_specifications_path="tests/assets/esco/specifications.json",
    )
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    import json

    with open("generated_profiles/esco.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
