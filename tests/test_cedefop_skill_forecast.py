import json

from dataset_profiler.profile_models import DatasetProfile


def test_cedefop_skill_forecast():
    with open("tests/assets/cedefop-skill-forecast-2025/specification.json") as json_file:
        spec = json.load(json_file)

    profile = DatasetProfile(spec)
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    with open("generated_profiles/cedefop_skill_forecast_2025.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)


if __name__ == "__main__":
    test_cedefop_skill_forecast()
