from dataset_profiler.profile_models import DatasetProfile


def test_profiler_mathe_integration_techniques():
    profile = DatasetProfile(
        dataset_specifications_path="tests/assets/mathe_integration_techniques/specifications.json",
    )
    print(profile.to_json_str())
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    import json

    with open("generated_profiles/mathe_integration_techniques.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
