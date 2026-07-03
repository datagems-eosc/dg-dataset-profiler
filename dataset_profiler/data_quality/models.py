from typing import List

from pydantic import BaseModel


class ErrorExample(BaseModel):
    """A single erroneous value and the 1-indexed row it was found in."""

    value: str
    row: int


class ColumnError(BaseModel):
    """A detected error pattern in one column of a tabular record set."""

    column: str
    error_type: str  # format_inconsistency | value_error | consistency_error
    description: str
    examples: List[ErrorExample]
    total_affected_rows: int

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "errorType": self.error_type,
            "description": self.description,
            "examples": [{"value": ex.value, "row": ex.row} for ex in self.examples],
            "totalAffectedRows": self.total_affected_rows,
        }


class DataQualityResult(BaseModel):
    """Data quality errors detected in a tabular record set (detection only)."""

    summary: str
    errors: List[ColumnError]

    @property
    def total_affected_rows(self) -> int:
        return sum(e.total_affected_rows for e in self.errors)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "errors": [error.to_dict() for error in self.errors],
        }

    def to_dict_cdd(self) -> dict:
        return {
            "summary": self.summary,
            "errors": [error.model_dump() for error in self.errors],
        }
