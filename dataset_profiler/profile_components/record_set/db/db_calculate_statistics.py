"""Column statistics of database tables, computed in the database.

Statistics are opt-in via ENABLE_DB_STATISTICS: they read every row, and on large
tables (hundreds of millions of rows) that takes minutes per table.

Per table, not per column, so that a table is scanned as few times as possible:

* every table: one scan computes, for every column, the non-missing count, and for
  numeric columns min, max, mean, standard deviation and variance;
* tables of up to EXACT_MAX_ROWS rows: a second scan computes exact histograms and
  unique counts;
* larger tables: the histogram counts come from the first scan, with inner bin
  edges taken from the planner's value range (pg_stats) and outer bins stretching
  to the exact min and max; unique counts only where the planner's most common
  values account for every row, so that the count is exact;
* median and 5th / 95th percentiles: exact up to EXACT_MAX_ROWS rows, otherwise
  from a block sample of about that many rows.

Float values at or beyond FILL_VALUE_THRESHOLD are fill values and count as missing.
The field names follow the CSV statistics: row_count is the number of non-missing
values, and non-numeric columns get counts only.
"""
from datetime import datetime, timezone
import os

from sqlalchemy import text

from dataset_profiler.configs.config_logging import logger
from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
from dataset_profiler.profile_components.record_set.db.database_connector import DatagemsPostgres
from dataset_profiler.utilities import FILL_VALUE_THRESHOLD

HISTOGRAM_BINS = 10
EXACT_MAX_ROWS = 2_000_000
INTEGER = {"SMALLINT", "INTEGER", "BIGINT"}
FLOAT = {"REAL", "DOUBLE PRECISION", "NUMERIC", "DECIMAL"}
NUMERIC = INTEGER | FLOAT
COUNTABLE = NUMERIC | {"TEXT", "VARCHAR", "CHARACTER", "DATE", "BOOLEAN", "UUID",
                       "TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP WITH TIME ZONE"}
# A big table's value counts come from FILTER clauses, one per most common value;
# beyond this many values the scan gets slow and the count is unlikely to be exact.
MAX_COUNTED_VALUES = 60


def db_statistics_enabled() -> bool:
    return os.environ.get("ENABLE_DB_STATISTICS", "false").lower() in ["true", "1", "yes"]


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _usable(column: str, db_type: str) -> str:
    """SQL condition for a value that counts: not NULL and, for floats, not a fill value."""
    if db_type in FLOAT:
        return f"abs({column}) < CAST({FILL_VALUE_THRESHOLD!r} AS {db_type})"
    return f"{column} IS NOT NULL"


def _float(value):
    return None if value is None else float(value)


def calculate_table_statistics(
    db: DatagemsPostgres, table_name: str, column_types: dict[str, str]
) -> dict[str, ColumnStatistics]:
    """Statistics of every column of a table, keyed by column name.

    ``column_types`` maps column names to upper-cased information_schema types, as
    the schema extraction stores them. Any failure is logged and gives no statistics:
    they are an enrichment and must never fail the profile.
    """
    try:
        return _calculate_table_statistics(db, table_name, column_types)
    except Exception as e:
        logger.error("Database statistics failed", table=table_name, error=str(e))
        return {}


def _calculate_table_statistics(db, table_name, column_types):
    schema = db.specific_schema or "public"
    table = f"{_quote(schema)}.{_quote(table_name)}"
    cols = list(column_types.items())
    started = datetime.now(timezone.utc)

    with db.engine.connect() as conn:
        def rows(sql, **params):
            return conn.execute(text(sql), params).mappings().all()

        est = rows("""SELECT greatest(c.reltuples, 0)::bigint AS est FROM pg_class c
                      JOIN pg_namespace n ON n.oid = c.relnamespace
                      WHERE n.nspname = :s AND c.relname = :t""", s=schema, t=table_name)
        exact = not est or est[0]["est"] <= EXACT_MAX_ROWS
        planner = {} if exact else {r["attname"]: r for r in rows("""
            SELECT attname, n_distinct,
                   (histogram_bounds::text::text[])[1] AS lo,
                   (histogram_bounds::text::text[])[array_length(histogram_bounds::text::text[], 1)] AS hi,
                   most_common_vals::text::text[] AS mcv
            FROM pg_stats WHERE schemaname = :s AND tablename = :t""", s=schema, t=table_name)}

        # Big tables: histogram edges and countable values from the planner.
        edges, counted = {}, {}
        for i, (name, db_type) in enumerate(cols):
            p = planner.get(name)
            if not p:
                continue
            if db_type in NUMERIC and p["lo"] is not None:
                lo, hi = float(p["lo"]), float(p["hi"])
                if hi > lo and abs(lo) < FILL_VALUE_THRESHOLD and abs(hi) < FILL_VALUE_THRESHOLD:
                    edges[i] = [lo + k * (hi - lo) / HISTOGRAM_BINS for k in range(1, HISTOGRAM_BINS)]
            if (db_type in COUNTABLE and p["mcv"] and p["n_distinct"] is not None
                    and 0 < p["n_distinct"] <= MAX_COUNTED_VALUES):
                counted[i] = p["mcv"]

        # Scan 1: counts and moments of every column.
        select = ["count(*) AS total"]
        for i, (name, db_type) in enumerate(cols):
            col, ok = _quote(name), _usable(_quote(name), db_type)
            select.append(f"count(*) FILTER (WHERE {ok}) AS c{i}_n")
            if db_type in NUMERIC:
                select += [f"{agg}({col}::float8) FILTER (WHERE {ok}) AS c{i}_{agg}"
                           for agg in ("min", "max", "avg", "stddev_samp", "var_samp")]
            # Compare in the column's own type: a per-row cast is what makes these scans slow.
            # Integer columns compare as floats, so that an edge such as 4.7 is not rounded.
            edge_type = "float8" if db_type in INTEGER else db_type
            for k, edge in enumerate(edges.get(i, [])):
                lhs = f"{col}::float8" if db_type in INTEGER else col
                select.append(f"count(*) FILTER (WHERE {ok} AND {lhs} < CAST({edge!r} AS {edge_type})) AS c{i}_lt{k}")
            for k, value in enumerate(counted.get(i, [])):
                literal = value.replace("'", "''")  # an untyped literal takes the column's type
                select.append(f"count(*) FILTER (WHERE {col} = '{literal}') AS c{i}_v{k}")
        scan = rows(f"SELECT {', '.join(select)} FROM {table}")[0]
        total = int(scan["total"])

        # Scan 2 (exact tables): histograms and unique counts, one grouping per column.
        groups = {}
        if exact and total:
            sets = []
            for i, (name, db_type) in enumerate(cols):
                col, ok = _quote(name), _usable(_quote(name), db_type)
                lo, hi = scan.get(f"c{i}_min"), scan.get(f"c{i}_max")
                if db_type in NUMERIC and lo is not None and hi > lo:
                    sets.append((f"h{i}", f"CASE WHEN {ok} THEN least(width_bucket({col}::float8, "
                                          f"{lo!r}, {hi!r}, {HISTOGRAM_BINS}), {HISTOGRAM_BINS})::text END"))
                if db_type in COUNTABLE:
                    sets.append((f"u{i}", f"CASE WHEN {ok} THEN {col}::text END"))
            if sets:
                values = ", ".join(f"('{key}', {expr})" for key, expr in sets)
                for r in rows(f"""SELECT v.s, v.k, count(*) AS n FROM {table}
                                  CROSS JOIN LATERAL (VALUES {values}) AS v(s, k)
                                  WHERE v.k IS NOT NULL GROUP BY v.s, v.k"""):
                    groups.setdefault(r["s"], []).append((r["k"], int(r["n"])))

        # Percentiles: exact, or from a block sample of about EXACT_MAX_ROWS rows.
        percentiles = {}
        numeric = [i for i, (_, db_type) in enumerate(cols) if db_type in NUMERIC]
        if numeric and total:
            source = table if exact else (f"{table} TABLESAMPLE SYSTEM "
                                          f"({min(100.0, EXACT_MAX_ROWS / total * 100):.6f}) REPEATABLE (42)")
            select = [(f"percentile_cont(ARRAY[0.05, 0.5, 0.95]) WITHIN GROUP (ORDER BY {_quote(cols[i][0])}::float8) "
                       f"FILTER (WHERE {_usable(_quote(cols[i][0]), cols[i][1])}) AS p{i}") for i in numeric]
            r = rows(f"SELECT {', '.join(select)} FROM {source}")[0]
            percentiles = {i: r[f"p{i}"] for i in numeric}

    generated_at = datetime.now(timezone.utc).isoformat()
    stats = {}
    for i, (name, db_type) in enumerate(cols):
        present = int(scan[f"c{i}_n"])
        missing = total - present
        unique = None
        if f"u{i}" in groups:
            unique = len(groups[f"u{i}"])
        elif i in counted:
            value_counts = [int(scan[f"c{i}_v{k}"]) for k in range(len(counted[i]))]
            if sum(value_counts) == present:  # every value counted, so the count is exact
                unique = sum(1 for n in value_counts if n)
        common = {"row_count": present, "missing_count": missing,
                  "missing_percentage": missing / total * 100 if total else None,
                  "unique_count": unique}
        if db_type not in NUMERIC or not present:
            stats[name] = ColumnStatistics(**common)
            continue

        lo, hi = float(scan[f"c{i}_min"]), float(scan[f"c{i}_max"])
        histogram = None
        if f"h{i}" in groups:
            width = (hi - lo) / HISTOGRAM_BINS
            counts = {int(k): n for k, n in groups[f"h{i}"]}
            histogram = [{"binRange": [lo + (b - 1) * width, lo + b * width], "count": counts.get(b, 0)}
                         for b in range(1, HISTOGRAM_BINS + 1)]
        elif i in edges:
            below = [int(scan[f"c{i}_lt{k}"]) for k in range(HISTOGRAM_BINS - 1)] + [present]
            bounds = [lo] + edges[i] + [hi]
            histogram = [{"binRange": [bounds[b], bounds[b + 1]], "count": below[b] - (below[b - 1] if b else 0)}
                         for b in range(HISTOGRAM_BINS)]
        p05, median, p95 = percentiles.get(i) or (None, None, None)
        stats[name] = ColumnStatistics(
            **common,
            mean=_float(scan[f"c{i}_avg"]),
            median=_float(median),
            standard_deviation=_float(scan[f"c{i}_stddev_samp"]),
            min_value=lo,
            max_value=hi,
            histogram=histogram,
            variance=_float(scan[f"c{i}_var_samp"]),
            range_value=hi - lo,
            percentile05=_float(p05),
            percentile95=_float(p95),
            generated_at=generated_at,
        )
    logger.info("Database statistics computed", table=table_name, rows=total, exact=exact,
                seconds=round((datetime.now(timezone.utc) - started).total_seconds(), 1))
    return stats
