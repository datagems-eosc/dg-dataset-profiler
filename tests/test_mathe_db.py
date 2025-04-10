from dataset_profiler.profile_models import DatasetProfile


def test_profiler_weather_stations():
    profile = DatasetProfile(
        dataset_specifications_path="tests/assets/mathe_relational_db/specifications.json",
    )
    # print(profile.to_json_str())
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created
