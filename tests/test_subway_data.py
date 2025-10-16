import json

from dataset_profiler.profile_models import DatasetProfile


def test_profiler_subway_data():
    with open("tests/assets/subway_data/specifications.json") as json_file:
        spec = json.load(json_file)
    profile = DatasetProfile(spec)
    print(profile.to_json_str())
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    import json

    with open("generated_profiles/subway_data.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
