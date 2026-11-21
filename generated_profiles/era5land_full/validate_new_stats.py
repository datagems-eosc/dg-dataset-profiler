"""Compare dataset_profiler's calculate_table_statistics with the full_stats.py results."""
import json, sys, time
from dotenv import load_dotenv
load_dotenv(".env")
from dataset_profiler.profile_components.record_set.db.database_connector import DatagemsPostgres
from dataset_profiler.profile_components.record_set.db.db_calculate_statistics import calculate_table_statistics

db = DatagemsPostgres(database="ds_era5_land", schema="public", engine="PostgreSQL")
types = db.get_types_of_db()
for table in sys.argv[1:]:
    t = time.time()
    new = calculate_table_statistics(db, table, types[table])
    ref = json.load(open(f"generated_profiles/era5land_full/stats/{table}.json"))["columns"]
    print(f"== {table} ({time.time() - t:.0f}s)")
    for col, s in new.items():
        d, r = s.to_dict(), ref[col]
        ref_present = r["rowCount"] - r["missingCount"]
        hist = json.loads(d["histogram"]) if d["histogram"] else None
        checks = {
            "present": (d["rowCount"], ref_present),
            "missing": (d["missingCount"], r["missingCount"]),
            "min": (d["min"], r.get("min") if isinstance(r.get("min"), (int, float)) else None),
            "mean": (round(d["mean"], 6) if d["mean"] is not None else None,
                     round(r["mean"], 6) if r.get("mean") is not None else None),
            "unique": (d["uniqueCount"], r.get("uniqueCount")),
            "hist_sum": (sum(b["count"] for b in hist) if hist else None, ref_present if hist else None),
        }
        bad = {k: v for k, v in checks.items() if v[0] != v[1]}
        print(f"  {col:20s} {d['rowCount']:>12,} present  {'OK' if not bad else 'DIFF ' + str(bad)}")
