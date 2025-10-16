import json
from dataset_profiler.profile_models import DatasetProfile


def test_profiler_weather_stations():
    with open("tests/assets/meteo_weather_stations_climpact/specifications.json") as json_file:
        spec = json.load(json_file)

    profile = DatasetProfile(spec)
    print(profile.to_json_str())
    import json

    with open("generated_profiles/weather_stations_climpact.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
