import json
from dataset_profiler.profile_models import DatasetProfile


def profiler_dummy_data():
    with open("tests/assets/dummy_data/specifications.json") as json_file:
        spec = json.load(json_file)

    profile = DatasetProfile(spec)
    print(profile.to_json_str())

    with open("generated_profiles/mix_of_datasets_profile.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created


if __name__ == "__main__":
    profiler_dummy_data()
