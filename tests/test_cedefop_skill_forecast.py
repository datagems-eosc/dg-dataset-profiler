import json

from dataset_profiler.profile_models import DatasetProfile


def cedefop_skill_forecast():
    profile = DatasetProfile(
        dataset_specifications_path="tests/assets/cedefop-skill-forecast-2025/specification.json",
    )
    assert isinstance(
        profile, DatasetProfile
    )  # Not an actual test, just to check if the profile is created

    with open("generated_profiles/cedefop_skill_forecast_2025.json", "w") as f:
        json.dump(profile.to_dict(), f)
    assert isinstance(profile, DatasetProfile)


if __name__ == "__main__":
    cedefop_skill_forecast()
