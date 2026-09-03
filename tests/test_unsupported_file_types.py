"""Files the profiler cannot read must still be listed in the distribution.

Reported from production: a dataset whose root held .m4a recordings alongside
folders of pdfs profiled to a JSON with no trace of the audio at all -- the
files, and any folder holding only such files, were dropped rather than listed.
The distribution is the dataset's inventory, so a consumer reading the profile
has to be able to see that those files exist and where they are; what it must
not contain is a record set for them.
"""

import json

import pytest

from dataset_profiler.profile_models import DatasetProfile


@pytest.fixture
def audio_dataset(tmp_path, monkeypatch):
    """A dataset shaped like the reported one: audio at the root, an
    audio-only folder, and a readable file of each kind for contrast."""
    monkeypatch.setattr("dataset_profiler.profile_models.DATASET_ROOT_PATH", "")

    root = tmp_path / "ds"
    (root / "audio").mkdir(parents=True)
    (root / "tables").mkdir()
    (root / "recording.m4a").write_bytes(b"\x00" * 10)
    (root / "data.csv").write_text("a,b\n1,2\n3,4\n")
    (root / "audio" / "interview.m4a").write_bytes(b"\x00" * 20)
    (root / "tables" / "notes.txt").write_text("Some notes.")
    (root / "tables" / "clip.mp3").write_bytes(b"\x00" * 30)

    return {
        "id": "test-id",
        "citeAs": "",
        "country": "PT",
        "data_connectors": [
            {"type": "RawDataPath", "dataset_id": f"{root}/"}
        ],
        "datePublished": "2025-08-23",
        "description": "d",
        "fieldOfScience": [],
        "headline": "h",
        "inLanguage": ["en"],
        "keywords": [],
        "license": "CC0 1.0",
        "name": "n",
        "url": "",
        "access": "PUBLIC",
        "uploadedBy": "ADMIN",
    }


def _by_name(profile):
    return {entry["name"]: entry for entry in profile["distribution"]}


def test_light_profile_lists_every_file_whatever_its_type(audio_dataset):
    distribution = _by_name(DatasetProfile(audio_dataset).to_dict_light())

    assert set(distribution) == {
        "audio", "tables",                      # file sets
        "recording.m4a", "data.csv",            # root file objects
        "interview.m4a", "notes.txt", "clip.mp3",  # file objects within sets
    }


def test_unsupported_files_carry_their_path_and_type(audio_dataset):
    distribution = _by_name(DatasetProfile(audio_dataset).to_dict_light())

    recording = distribution["recording.m4a"]
    assert recording["@type"] == "cr:FileObject"
    assert recording["contentUrl"].endswith("/ds/recording.m4a")
    assert recording["contentSize"] == "10 B"
    # Guessed from the extension alone -- nothing is read off the disk.
    assert recording["encodingFormat"] == "audio/mp4"


def test_folder_of_only_unsupported_files_is_still_a_file_set(audio_dataset):
    distribution = _by_name(DatasetProfile(audio_dataset).to_dict_light())

    audio_set = distribution["audio"]
    assert audio_set["@type"] == "cr:FileSet"
    assert audio_set["includes"] == "audio/*"
    assert audio_set["encodingFormat"] == "audio/mp4"
    # ... and the files inside it point back at it.
    assert distribution["interview.m4a"]["containedIn"] == {"@id": audio_set["@id"]}


def test_mixed_folder_advertises_the_type_the_profiler_can_read(audio_dataset):
    distribution = _by_name(DatasetProfile(audio_dataset).to_dict_light())

    assert distribution["tables"]["encodingFormat"] == "text/plain"


def test_unsupported_files_get_no_record_set(audio_dataset):
    profile = DatasetProfile(audio_dataset).to_dict()

    assert _by_name(profile).keys() >= {"recording.m4a", "interview.m4a", "clip.mp3"}
    profiled = json.dumps(profile["recordSet"])
    for skipped in (".m4a", ".mp3"):
        assert skipped not in profiled
