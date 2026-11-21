"""Full-data column statistics for every table of the ERA5-Land database.

Small tables (estimated <= SAMPLE_ROWS rows), all exact:
  pass 1  row count, missing, min, max, mean, stddev, variance
  pass 2  10-bin histograms, unique counts, top values of text columns
Big tables, one scan over all rows:
  exact row count, missing, min, max, mean, stddev, variance;
  exact 10-bin histogram whose inner edges come from the planner's value range (pg_stats)
  and whose outer bins stretch to the exact min and max;
  exact value counts for low-cardinality columns listed in pg_stats most_common_vals.
Percentiles (p05, median, p95) come from a TABLESAMPLE SYSTEM block sample of ~SAMPLE_ROWS rows
(exact for small tables).

Float values at or below FILL (the NetCDF fill value -9e33, "no data") are counted as missing.

Writes stats/<table>.json next to this file; tables already written are skipped.
Run from the repo root:  python generated_profiles/era5land_full/full_stats.py [table ...]
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(".env")
from sqlalchemy import text  # noqa: E402

from dataset_profiler.profile_components.record_set.db.database_connector import DatagemsPostgres  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stats")
DB = os.environ.get("DB", "ds_era5_land")
WORKERS = int(os.environ.get("WORKERS", "2"))
SAMPLE_ROWS = 2_000_000
BINS = 10
FILL = -1e30
FILL_VALUE = -9e33

INTEGER = {"smallint", "integer", "bigint"}
FLOAT = {"numeric", "real", "double precision"}
NUMERIC = INTEGER | FLOAT
TEMPORAL = {"timestamp without time zone", "timestamp with time zone", "date"}
TEXT = {"text", "character varying", "character"}

os.makedirs(OUT, exist_ok=True)
engine = DatagemsPostgres(database=DB, schema="public", engine="PostgreSQL").engine


def log(*a):
    print(datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def q(name):
    return '"' + name.replace('"', '""') + '"'


def rows(conn, sql, **params):
    return conn.execute(text(sql), params).mappings().all()


def as_json(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    try:
        return float(v)
    except (TypeError, ValueError):
        return str(v)


def valid(name, kind):
    """SQL condition for a usable value: not NULL and, for floats, not the fill value."""
    return f"{name} > {FILL!r}::{kind}" if kind in FLOAT else f"{name} IS NOT NULL"


def profile_table(table, est_rows):
    path = os.path.join(OUT, f"{table}.json")
    if os.path.exists(path):
        log("skip", table)
        return
    t0 = time.time()
    with engine.connect() as conn:
        conn.execute(text("SET work_mem = '256MB'"))
        cols = rows(conn, """SELECT column_name, data_type FROM information_schema.columns
                             WHERE table_schema = 'public' AND table_name = :t ORDER BY ordinal_position""", t=table)
        pgs = {r["attname"]: r for r in rows(conn, """
            SELECT attname, n_distinct,
                   (histogram_bounds::text::text[])[1] AS lo,
                   (histogram_bounds::text::text[])[array_length(histogram_bounds::text::text[], 1)] AS hi,
                   most_common_vals::text::text[] AS mcv
            FROM pg_stats WHERE schemaname = 'public' AND tablename = :t""", t=table)}
        big = est_rows > SAMPLE_ROWS
        edges, mcv_cols = {}, {}
        if big:
            for i, c in enumerate(cols):
                ps, kind = pgs.get(c["column_name"]), c["data_type"]
                if not ps:
                    continue
                if kind in NUMERIC and ps["lo"] is not None:
                    lo, hi = float(ps["lo"]), float(ps["hi"])
                    if hi > lo and lo > FILL:
                        edges[i] = [lo + k * (hi - lo) / BINS for k in range(1, BINS)]
                limit = 20 if kind in TEXT else 60 if kind in INTEGER else 0
                if ps["mcv"] and ps["n_distinct"] is not None and 0 < ps["n_distinct"] <= limit:
                    mcv_cols[i] = ps["mcv"]

        # ---- pass 1: aggregates over all rows in one scan
        sel = ["count(*) AS n"]
        for i, c in enumerate(cols):
            name, kind = q(c["column_name"]), c["data_type"]
            ok = valid(name, kind)
            sel.append(f"count(*) FILTER (WHERE {ok}) AS c{i}_n")
            if kind in NUMERIC:
                sel += [f"min({name}::float8) FILTER (WHERE {ok}) AS c{i}_min",
                        f"max({name}::float8) FILTER (WHERE {ok}) AS c{i}_max",
                        f"avg({name}::float8) FILTER (WHERE {ok}) AS c{i}_avg",
                        f"stddev_samp({name}::float8) FILTER (WHERE {ok}) AS c{i}_sd",
                        f"var_samp({name}::float8) FILTER (WHERE {ok}) AS c{i}_var"]
            if kind in FLOAT:
                sel.append(f"count(*) FILTER (WHERE {name} <= {FILL!r}::{kind}) AS c{i}_fill")
            elif kind in TEMPORAL:
                sel += [f"min({name}) AS c{i}_min", f"max({name}) AS c{i}_max"]
            for k, e in enumerate(edges.get(i, [])):
                sel.append(f"count(*) FILTER (WHERE {ok} AND {name} < {e!r}::{kind}) AS c{i}_lt{k}")
            for k, v in enumerate(mcv_cols.get(i, [])):
                lit = v.replace("'", "''")
                sel.append(f"count(*) FILTER (WHERE {name} = '{lit}'::{kind}) AS c{i}_v{k}")
        p1 = rows(conn, f"SELECT {', '.join(sel)} FROM {q(table)}")[0]
        n = int(p1["n"])
        t1 = time.time()
        log(f"{table}: pass 1 done, {n:,} rows, {t1 - t0:.0f}s")

        # ---- pass 2 (small tables only): exact histograms + unique counts in one scan
        sets = []  # (set_id, column index, purpose, sql expression)
        for i, c in enumerate(cols if not big else []):
            name, kind = q(c["column_name"]), c["data_type"]
            ok = valid(name, kind)
            lo, hi = p1.get(f"c{i}_min"), p1.get(f"c{i}_max")
            if kind in NUMERIC and lo is not None and hi is not None and hi > lo:
                sets.append((len(sets), i, "hist", f"CASE WHEN {ok} THEN LEAST(width_bucket({name}::float8, "
                                                   f"{lo!r}, {hi!r}, {BINS}), {BINS})::text END"))
            if kind in NUMERIC | TEMPORAL | TEXT:
                sets.append((len(sets), i, "uniq", f"CASE WHEN {ok} THEN {name}::text END"))
        groups = {}
        if sets:
            values = ", ".join(f"({s}, {expr})" for s, _, _, expr in sets)
            for r in rows(conn, f"""SELECT v.s, v.k, count(*) AS cnt FROM {q(table)}
                                    CROSS JOIN LATERAL (VALUES {values}) AS v(s, k)
                                    WHERE v.k IS NOT NULL GROUP BY v.s, v.k"""):
                groups.setdefault(r["s"], []).append((r["k"], int(r["cnt"])))
        t2 = time.time()
        if sets:
            log(f"{table}: pass 2 done, {len(sets)} groupings, {t2 - t1:.0f}s")

        # ---- percentiles from a block sample (exact for small tables)
        num_idx = [i for i, c in enumerate(cols) if c["data_type"] in NUMERIC]
        pct = min(100.0, SAMPLE_ROWS / max(n, 1) * 100)
        pcts, sample_n = {}, 0
        if num_idx and n:
            src = q(table) if pct >= 100 else f"{q(table)} TABLESAMPLE SYSTEM ({pct:.6f}) REPEATABLE (42)"
            sel = ", ".join(
                f"percentile_cont(ARRAY[0.05, 0.5, 0.95]) WITHIN GROUP (ORDER BY {q(cols[i]['column_name'])}::float8) "
                f"FILTER (WHERE {valid(q(cols[i]['column_name']), cols[i]['data_type'])}) AS p{i}"
                for i in num_idx)
            r = rows(conn, f"SELECT count(*) AS sample_n, {sel} FROM {src}")[0]
            pcts = {i: r[f"p{i}"] for i in num_idx}
            sample_n = int(r["sample_n"])
        t3 = time.time()
        log(f"{table}: percentiles done on {sample_n:,} rows, {t3 - t2:.0f}s")

    now = datetime.now(timezone.utc).isoformat()
    out_cols = {}
    for i, c in enumerate(cols):
        kind = c["data_type"]
        usable = int(p1[f"c{i}_n"])
        st = {"rowCount": n, "missingCount": n - usable,
              "missingPercentage": (n - usable) / n * 100 if n else None, "generatedAt": now}
        if kind in FLOAT and p1.get(f"c{i}_fill"):
            st["fillValue"], st["fillValueCount"] = FILL_VALUE, int(p1[f"c{i}_fill"])
        if kind in NUMERIC or kind in TEMPORAL:
            st["min"], st["max"] = as_json(p1.get(f"c{i}_min")), as_json(p1.get(f"c{i}_max"))
        if kind in NUMERIC:
            st.update(mean=as_json(p1[f"c{i}_avg"]), standardDeviation=as_json(p1[f"c{i}_sd"]),
                      variance=as_json(p1[f"c{i}_var"]))
            if st["min"] is not None:
                st["range"] = st["max"] - st["min"]
            p = pcts.get(i)
            if p:
                st["percentile05"], st["median"], st["percentile95"] = (as_json(x) for x in p)
        for s, ci, purpose, _ in sets:
            if ci != i:
                continue
            g = groups.get(s, [])
            if purpose == "hist":
                lo, hi = st["min"], st["max"]
                w = (hi - lo) / BINS
                counts = {int(k): v for k, v in g}
                st["histogram"] = [{"binRange": [lo + (b - 1) * w, lo + b * w], "count": counts.get(b, 0)}
                                   for b in range(1, BINS + 1)]
            else:
                st["uniqueCount"] = len(g)
                if kind in TEXT:
                    st["topValues"] = [{"value": k, "count": v} for k, v in sorted(g, key=lambda kv: -kv[1])[:10]]
        if i in edges and st.get("min") is not None:
            cum = [int(p1[f"c{i}_lt{k}"]) for k in range(BINS - 1)] + [usable]
            bounds = [st["min"]] + edges[i] + [st["max"]]
            st["histogram"] = [{"binRange": [bounds[b], bounds[b + 1]],
                                "count": cum[b] - (cum[b - 1] if b else 0)} for b in range(BINS)]
        if i in mcv_cols:
            counts = [(v, int(p1[f"c{i}_v{k}"])) for k, v in enumerate(mcv_cols[i])]
            counts = [kv for kv in counts if kv[1] > 0]
            st["topValues"] = [{"value": v, "count": c_} for v, c_ in sorted(counts, key=lambda kv: -kv[1])[:10]]
            if sum(c_ for _, c_ in counts) == usable:
                st["uniqueCount"] = len(counts)  # every value is accounted for, so the count is exact
        st.setdefault("uniqueCount", None)
        out_cols[c["column_name"]] = st

    result = {"table": table, "method": "single scan + planner bounds" if big else "two scans, exact",
              "rows": n, "estimatedRows": est_rows, "seconds": round(t3 - t0, 1),
              "pass1Seconds": round(t1 - t0, 1), "pass2Seconds": round(t2 - t1, 1),
              "percentileSampleRows": sample_n, "percentileSamplePct": round(pct, 4),
              "sqlTypes": {c["column_name"]: c["data_type"] for c in cols}, "columns": out_cols}
    json.dump(result, open(path + ".tmp", "w"), indent=1)
    os.replace(path + ".tmp", path)
    log(f"{table}: written, total {t3 - t0:.0f}s")


def main():
    with engine.connect() as conn:
        tables = rows(conn, """SELECT c.relname AS t, greatest(c.reltuples, 0)::bigint AS est
                               FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                               WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'm')
                               ORDER BY pg_total_relation_size(c.oid) DESC""")
    wanted = set(sys.argv[1:])
    tables = [(r["t"], int(r["est"])) for r in tables if not wanted or r["t"] in wanted]
    log("tables:", [t for t, _ in tables])
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        for f in [ex.submit(profile_table, t, e) for t, e in tables]:
            try:
                f.result()
            except Exception as e:  # keep going with the other tables
                log("FAILED:", repr(e)[:500])
    log(f"all done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
