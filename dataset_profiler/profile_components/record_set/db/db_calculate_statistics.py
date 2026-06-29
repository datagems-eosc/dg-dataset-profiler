from datetime import datetime, timezone

from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
from dataset_profiler.profile_components.record_set.db.database_connector import DatagemsPostgres


def calculate_statistics_of_db(column_name: str, table_name: str, db_connector: DatagemsPostgres, data_type: str) -> ColumnStatistics:
    """
    Calculate statistics of a database column
    """
    if data_type == "sc:Integer" or data_type == "sc:Float":
        row_count = db_connector.execute(f"SELECT COUNT({column_name}) FROM {table_name}").iloc[0, 0]
        table_name = f"(SELECT {column_name} FROM {table_name} LIMIT 1000)" if row_count > 1000 else table_name

        mean = db_connector.execute(f"SELECT AVG({column_name}) FROM {table_name}").iloc[0, 0]
        median = db_connector.execute(f"SELECT PERCENTILE_CONT(0.5) "
                                      f"WITHIN GROUP (ORDER BY {column_name}) FROM {table_name}").iloc[0, 0]
        stddev = db_connector.execute(f"SELECT STDDEV({column_name}) FROM {table_name}").iloc[0, 0]
        variance = db_connector.execute(f"SELECT VAR_SAMP({column_name}) FROM {table_name}").iloc[0, 0]
        min_value = db_connector.execute(f"SELECT MIN({column_name}) FROM {table_name}").iloc[0, 0]
        max_value = db_connector.execute(f"SELECT MAX({column_name}) FROM {table_name}").iloc[0, 0]
        percentile05 = db_connector.execute(f"SELECT PERCENTILE_CONT(0.05) "
                                            f"WITHIN GROUP (ORDER BY {column_name}) FROM {table_name}").iloc[0, 0]
        percentile95 = db_connector.execute(f"SELECT PERCENTILE_CONT(0.95) "
                                            f"WITHIN GROUP (ORDER BY {column_name}) FROM {table_name}").iloc[0, 0]
        missing_count = db_connector.execute(f"SELECT COUNT({column_name}) FROM {table_name} WHERE {column_name} IS NULL").iloc[0, 0]
        missing_percentage = missing_count / row_count * 100
        histogram_results = db_connector.execute(f"""
            SELECT width_bucket({column_name}, min_val, max_val, 10) AS bucket,
                   COUNT(*) AS count
            FROM {table_name},
                 (SELECT MIN({column_name}) AS min_val, MAX({column_name}) AS max_val FROM {table_name}) AS bounds
            WHERE {column_name} IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket;
        """)

        histogram = []
        if not isinstance(histogram_results, dict):
            for _, row in histogram_results.iterrows():
                bucket, count = row
                if bucket is not None:
                    bin_range = [
                        float((bucket - 1) * (max_value - min_value) / 10 + min_value),
                        float(bucket * (max_value - min_value) / 10 + min_value)
                    ]
                    histogram.append({"binRange": bin_range, "count": int(count)})

        min_value = float(min_value) if min_value is not None else None
        max_value = float(max_value) if max_value is not None else None
        stats = ColumnStatistics(
            row_count=int(row_count) if row_count is not None else None,
            mean=float(mean) if mean is not None else None,
            median=float(median) if median is not None else None,
            standard_deviation=float(stddev) if stddev is not None else None,
            min_value=min_value,
            max_value=max_value,
            missing_count=int(missing_count) if missing_count is not None else None,
            missing_percentage=missing_percentage if missing_percentage is not None else None,
            histogram=histogram,
            unique_count=None,
            variance=float(variance) if variance is not None else None,
            range_value=(max_value - min_value) if min_value is not None and max_value is not None else None,
            percentile05=float(percentile05) if percentile05 is not None else None,
            percentile95=float(percentile95) if percentile95 is not None else None,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        return stats
    else:
        row_count = db_connector.execute(f"SELECT COUNT({column_name}) FROM {table_name}").iloc[0, 0]
        missing_count = db_connector.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL").iloc[0, 0]
        missing_percentage = missing_count / row_count * 100
        unique_count = db_connector.execute(f"SELECT COUNT(DISTINCT {column_name}) FROM {table_name}").iloc[0, 0]

        stats = ColumnStatistics(
            row_count=int(row_count),
            missing_count=int(missing_count),
            missing_percentage=missing_percentage,
            unique_count=int(unique_count),
        )
        return stats
