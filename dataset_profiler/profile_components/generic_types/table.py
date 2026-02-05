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
    ):
        self.row_count = row_count
        self.mean = mean
        self.median = median
        self.standard_deviation = standard_deviation
        self.min_value = min_value
        self.max_value = max_value
        self.missing_count = missing_count
        self.missing_percentage = missing_percentage
        self.histogram = histogram
        self.unique_count = unique_count

    def to_dict(self) -> dict:
        return {
            "@id": str(uuid.uuid4()),
            "@type": "dg:ColumnStatistics",
            "dg:rowCount": self.row_count,
            "dg:mean": self.mean,
            "dg:median": self.median,
            "dg:standardDeviation": self.standard_deviation,
            "dg:min": self.min_value,
            "dg:max": self.max_value,
            "dg:missingCount": self.missing_count,
            "dg:missingPercentage": self.missing_percentage,
            "dg:histogram": self.histogram,
            "dg:uniqueCount": self.unique_count,
        }
