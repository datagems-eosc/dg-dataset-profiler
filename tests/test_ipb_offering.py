import json

import pytest

from dataset_profiler.profile_models import DatasetProfile


@pytest.mark.live_llm
def test_profiler_ipb_offering():
    """Profiles the IPB course offering PDF against the real SCAYLE LLM (needs VPN).

    Also writes the heavy and CDD profiles to generated_profiles/, which serve
    as the example of PDF keywords and summaries for the LLL use case.
    """
    with open("tests/assets/ipb_offering/specifications.json") as json_file:
        spec = json.load(json_file)
    profile = DatasetProfile(spec)

    heavy = profile.to_dict()
    with open("generated_profiles/ipb_offering.json", "w") as f:
        json.dump(heavy, f, indent=2, ensure_ascii=False)
    with open("generated_profiles/ipb_offering_cdd.json", "w") as f:
        json.dump(profile.to_dict_cdd(), f, indent=2, ensure_ascii=False)

    (record_set,) = heavy["recordSet"]
    assert record_set["keywords"], "no keywords: is SCAYLE reachable and DOCUMENT_LLM_MODEL served?"
    assert record_set["summary"], "no summary: is SCAYLE reachable and DOCUMENT_LLM_MODEL served?"
