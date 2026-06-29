import json
import uuid


class ColumnStatistics:
    def __init__(
            self,
            row_count: int | None = None,
            mean: float | None = None,
            median: float | None = None,
            standard_deviation: float | None = None,
            min_value: float | None = None,
            max_value: float | None = None,
            missing_count: int | None = None,
            missing_percentage: float | None = None,
            histogram: list[dict] | None = None,
            unique_count: int | None = None,
            variance: float | None = None,
            range_value: float | None = None,
            percentile05: float | None = None,
            percentile95: float | None = None,
            generated_at: str | None = None,
    ):
        self.row_count = row_count
        self.mean = mean
        self.median = median
        self.standard_deviation = standard_deviation
        self.min_value = min_value
        self.max_value = max_value
        self.missing_count = missing_count
        self.missing_percentage = missing_percentage
        self.histogram = json.dumps(histogram) if histogram is not None else None
        self.unique_count = unique_count
        self.variance = variance
        self.range_value = range_value
        self.percentile05 = percentile05
        self.percentile95 = percentile95
        self.generated_at = generated_at

    def to_dict(self) -> dict:
        return {
            "@id": str(uuid.uuid4()),
            "@type": "dg:ColumnStatistics",
            "rowCount": self.row_count,
            "mean": self.mean,
            "median": self.median,
            "standardDeviation": self.standard_deviation,
            "min": self.min_value,
            "max": self.max_value,
            "missingCount": self.missing_count,
            "missingPercentage": self.missing_percentage,
            "histogram": self.histogram,
            "uniqueCount": self.unique_count,
            "variance": self.variance,
            "range": self.range_value,
            "percentile05": self.percentile05,
            "percentile95": self.percentile95,
            "generatedAt": self.generated_at,
        }

    def to_dict_cdd(self):
        return {
            "rowCount": self.row_count,
            "mean": self.mean,
            "median": self.median,
            "standardDeviation": self.standard_deviation,
            "min": self.min_value,
            "max": self.max_value,
            "missingCount": self.missing_count,
            "missingPercentage": self.missing_percentage,
            "histogram": self.histogram,
            "uniqueCount": self.unique_count,
            "variance": self.variance,
            "range": self.range_value,
            "percentile05": self.percentile05,
            "percentile95": self.percentile95,
            "generatedAt": self.generated_at,
        }
