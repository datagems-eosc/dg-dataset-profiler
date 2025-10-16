import json

from dataset_profiler.profile_models import DatasetProfile


def test_profiler_mathe_material():
    with open("tests/assets/mathe_material/specifications.json") as json_file:
        spec = json.load(json_file)
    profile = DatasetProfile(spec)
    print(profile.to_json_str())
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    import json

    with open("generated_profiles/mathe_material.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
