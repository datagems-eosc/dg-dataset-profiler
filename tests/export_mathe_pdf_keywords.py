import shutil
from dataset_profiler.profile_models import DatasetProfile
import os
import json

import random


def sampling_pdf_document(filepath: str) -> None:
    # get all pdf files name in the directory by glob
    from pathlib import Path

    pdf_files = list(Path("tests/assets/pdf/data").glob("*.pdf"))
    # sample up to 100 pdf files randomly with seed 42
    random.seed(42)
    sampled_files = random.sample(pdf_files, min(100, len(pdf_files)))
    # copy the sampled files to the given filepath
    os.makedirs(filepath + "/sampled", exist_ok=True)
    for pdf_file in sampled_files:
        shutil.copy(pdf_file, filepath + "/sampled/" + pdf_file.name)
    print(f"Sampled {len(sampled_files)} pdf files to {filepath}/sampled")


def dumping_mathe_pdf_profile(filepath: str):
    with open("tests/assets/pdf/sampled_specifications.json") as json_file:
        spec = json.load(json_file)

    profile = DatasetProfile(spec)
    # check if the directory of path exists

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # dumping the profile to a json string and save it to a file

    with open(filepath, "w") as f:
        f.write(profile.to_json_str())


if __name__ == "__main__":
    sampling_pdf_document("tests/assets/pdf")

    dumping_mathe_pdf_profile("tests/assets/pdf/sampled/mathe_pdf_profile.json")
