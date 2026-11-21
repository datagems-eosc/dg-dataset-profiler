"""Merge the full-data statistics into the base ERA5-Land profile.

Run from the repo root:  python generated_profiles/era5land_full/merge.py
Writes era5land_full_profile.json next to this file.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
base = json.load(open(os.path.join(HERE, "era5_base.json")))
heavy, cdd = base["moma_profile_heavy"], base.get("cdd_profile") or {}

SERIALISED = ("histogram", "topValues")  # JSON strings in the MoMa profile, as the other profilers write them
RUN_KEYS = ("method", "rows", "seconds", "pass1Seconds", "pass2Seconds", "percentileSampleRows",
            "percentileSamplePct", "sqlTypes", "histogramMethod", "histogramSeconds")


def load_stats(table):
    path = os.path.join(HERE, "stats", table + ".json")
    return json.load(open(path)) if os.path.exists(path) else None


run, missing = {}, []
for rs in heavy["recordSet"]:
    st = load_stats(rs["name"])
    if st is None:
        missing.append(rs["name"])
        continue
    run[rs["name"]] = {k: st.get(k) for k in RUN_KEYS}
    for f in rs["field"]:
        new = st["columns"].get(f["name"])
        if new is None:
            continue
        merged = {"@id": f["statistics"].get("@id"), "@type": f["statistics"].get("@type", "dg:ColumnStatistics")}
        merged.update({k: (json.dumps(v) if k in SERIALISED and v is not None else v) for k, v in new.items()})
        # The profiler's rowCount is the number of non-missing values (as for CSV columns).
        merged["rowCount"] = new["rowCount"] - new["missingCount"]
        f["statistics"] = merged

for file in cdd.get("files", []) if isinstance(cdd, dict) else []:
    for table in file.get("tables", []):
        st = load_stats(table.get("name", ""))
        if st:
            for c in table.get("columns", []):
                if c.get("name") in st["columns"]:
                    s = st["columns"][c["name"]]
                    c["statistics"] = {**s, "rowCount": s["rowCount"] - s["missingCount"]}

out = os.path.join(HERE, "era5land_full_profile.json")
json.dump({"moma_profile_heavy": heavy, "cdd_profile": cdd, "statisticsRun": run}, open(out, "w"), default=str)
print("merged", len(run), "tables; missing stats for", missing)
