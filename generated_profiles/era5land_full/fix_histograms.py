"""Recompute the histograms of some big tables with equal-width bins over the exact range.

full_stats.py takes a big table's inner bin edges from pg_stats. ERA5-Land was never
analysed, so for some columns the planner's range is far narrower than the data
(latitude 45-48 against 35-48) and most rows land in the first bin. The exact min and
max are already known, so one more scan per table gives equal-width bins.

Run from the repo root:  python generated_profiles/era5land_full/fix_histograms.py table [table ...]
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(".env")
from sqlalchemy import text  # noqa: E402

from dataset_profiler.profile_components.record_set.db.database_connector import DatagemsPostgres  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BINS = 10
FILL = 1e30
INTEGER = {"smallint", "integer", "bigint"}
FLOAT = {"numeric", "real", "double precision"}
engine = DatagemsPostgres(database="ds_era5_land", schema="public", engine="PostgreSQL").engine


def log(*a):
    print(datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def q(name):
    return '"' + name.replace('"', '""') + '"'


def fix(table):
    path = os.path.join(HERE, "stats", f"{table}.json")
    st = json.load(open(path))
    t0 = time.time()
    plan, select = {}, []
    for c, s in st["columns"].items():
        kind = st["sqlTypes"][c]
        if kind not in INTEGER | FLOAT or s.get("min") is None or not s["max"] > s["min"]:
            continue
        lo, hi = s["min"], s["max"]
        edges = [lo + k * (hi - lo) / BINS for k in range(1, BINS)]
        plan[c] = edges
        col = q(c)
        ok = f"abs({col}) < CAST({FILL!r} AS {kind})" if kind in FLOAT else f"{col} IS NOT NULL"
        lhs, cast = (f"{col}::float8", "float8") if kind in INTEGER else (col, kind)
        select += [f'count(*) FILTER (WHERE {ok} AND {lhs} < CAST({e!r} AS {cast})) AS "{c}__{k}"'
                   for k, e in enumerate(edges)]
    with engine.connect() as conn:
        r = conn.execute(text(f"SELECT {', '.join(select)} FROM {q(table)}")).mappings().one()
    for c, edges in plan.items():
        s = st["columns"][c]
        usable = s["rowCount"] - s["missingCount"]
        below = [int(r[f"{c}__{k}"]) for k in range(BINS - 1)] + [usable]
        bounds = [s["min"]] + edges + [s["max"]]
        s["histogram"] = [{"binRange": [bounds[b], bounds[b + 1]], "count": below[b] - (below[b - 1] if b else 0)}
                          for b in range(BINS)]
    st["histogramMethod"] = "equal width over the exact range"
    st["histogramSeconds"] = round(time.time() - t0, 1)
    json.dump(st, open(path + ".tmp", "w"), indent=1)
    os.replace(path + ".tmp", path)
    log(f"{table}: {len(plan)} histograms, {time.time() - t0:.0f}s")


def main():
    t0 = time.time()
    with ThreadPoolExecutor(2) as ex:
        for f in [ex.submit(fix, t) for t in sys.argv[1:]]:
            try:
                f.result()
            except Exception as e:
                log("FAILED:", repr(e)[:400])
    log(f"all done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
