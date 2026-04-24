import json

from dataset_profiler.profile_models import DatasetProfile


def test_cedefop_skill_forecast():
    with open("tests/assets/cedefop-skill-forecast-2025/specification.json") as json_file:
        spec = json.load(json_file)

    profile = DatasetProfile(spec)
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    light_profile = profile.to_dict_light()
    heavy_profile = profile.to_dict()
    with open("generated_profiles/cedefop_skill_forecast_2025.json", "w") as f:
        json.dump(heavy_profile, f)
    assert isinstance(profile, DatasetProfile)


if __name__ == "__main__":
    test_cedefop_skill_forecast()
