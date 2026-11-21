"""Base ERA5-Land profile from the current profiler (structure, types, semantic types, samples).

Run from the repo root:  python generated_profiles/era5land_full/run_base.py
"""
import json
import os
import time

from dotenv import load_dotenv

load_dotenv(".env")
from dataset_profiler.profile_models import DatasetProfile  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
t = time.time()
spec = json.load(open("tests/assets/meteo_era5land/specifications.json"))
p = DatasetProfile(spec)
out = {"moma_profile_heavy": p.to_dict()}
try:
    out["cdd_profile"] = p.to_dict_cdd()
except Exception as e:
    print("cdd", e)
json.dump(out, open(os.path.join(HERE, "era5_base.json"), "w"), default=str)
print("done in", round(time.time() - t), "s", flush=True)
