from dataset_profiler.profile_models import DatasetProfile


def test_profiler_weather_stations():
    profile = DatasetProfile(
        dataset_specifications_path="tests/assets/meteo_weather_stations_climpact/specifications.json",
    )
    print(profile.to_json_str())
    import json

    with open("generated_profiles/weather_stations_climpact.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
