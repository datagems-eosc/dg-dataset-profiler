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
            "row_count": self.row_count,
            "mean": self.mean,
            "median": self.median,
            "standardDeviation": self.standard_deviation,
            "min": self.min_value,
            "max": self.max_value,
            "missingCount": self.missing_count,
            "missingPercentage": self.missing_percentage,
            "histogram": self.histogram,
            "uniqueCount": self.unique_count,
        }
