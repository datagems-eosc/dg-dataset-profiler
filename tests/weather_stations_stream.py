import json

from dataset_profiler.profile_models import DatasetProfile


def profiler_era5land():
    with open("tests/assets/meteo_weather_stations_streaming/specifications.json") as json_file:
        spec = json.load(json_file)

    profile = DatasetProfile(spec)
    print(profile.to_json_str())

    with open("generated_profiles/meteo_weather_stations_streaming.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)


if __name__ == "__main__":
    profiler_era5land()
