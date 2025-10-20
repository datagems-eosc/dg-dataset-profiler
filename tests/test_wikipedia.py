import json

from dataset_profiler.profile_models import DatasetProfile


def test_wikipedia():
    with open("tests/assets/wikipedia/specification.json") as json_file:
        spec = json.load(json_file)
    profile = DatasetProfile(spec)
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    with open("generated_profiles/wikipedia.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
