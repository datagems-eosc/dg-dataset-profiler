from dataset_profiler.profile_models import DatasetProfile


def test_profiler_era5land():
    profile = DatasetProfile(
        dataset_specifications_path="tests/assets/meteo_era5land/specifications.json",
    )
    print(profile.to_json_str())
    import json

    with open("generated_profiles/meteo_era5land.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)
