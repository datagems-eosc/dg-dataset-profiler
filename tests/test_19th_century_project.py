import json

from dataset_profiler.profile_models import DatasetProfile


def test_19th_century_project():
    with open("tests/assets/britannica_text/specifications.json") as json_file:
        spec = json.load(json_file)

    profile = DatasetProfile(spec)
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    with open("generated_profiles/19th_century_project.json", "w") as f:
        json.dump(profile.to_dict(), f, indent=2)
    assert isinstance(profile, DatasetProfile)
