import json

from dataset_profiler.profile_models import DatasetProfile


def test_profiler_mathe_integration_techniques():
    with open("tests/assets/mathe_integration_techniques/specifications.json") as json_file:
        spec = json.load(json_file)

    profile = DatasetProfile(spec)
    print(profile.to_json_str())
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    with open("generated_profiles/mathe_integration_techniques.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
