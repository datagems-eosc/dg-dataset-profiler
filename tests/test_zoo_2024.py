import json

from dataset_profiler.profile_models import DatasetProfile


def test_profiler_zoo_2024():
    with open("tests/assets/zoo_24/specifications.json") as json_file:
        spec = json.load(json_file)
    profile = DatasetProfile(spec)
    print(profile.to_json_str())
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    with open("generated_profiles/zoo_2024.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
