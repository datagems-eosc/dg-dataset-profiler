import json

from dataset_profiler.profile_models import DatasetProfile


def test_profiler_json_stations():
    with open("tests/assets/json_stations/specifications.json") as json_file:
        spec = json.load(json_file)
    profile = DatasetProfile(spec)
    heavy = profile.to_dict()
    cdd = profile.to_dict_cdd()

    (record_set,) = heavy["recordSet"]
    assert record_set["recordPath"] == "$.stations[*]"
    assert record_set["recordCount"] == 5
    (stations,) = cdd["files"]
    assert stations["json_profile"]["document_metadata"]["$.meta.license"] == "CC BY 4.0"

    with open("generated_profiles/json_stations.json", "w") as f:
        json.dump(heavy, f)
    with open("generated_profiles/json_stations_cdd.json", "w") as f:
        json.dump(cdd, f)
