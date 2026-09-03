import uuid
from typing import List, Literal

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


# The detection script is written by an LLM, which is asked for these three
# categories but is free to return anything. Declaring them as a Literal makes
# pydantic reject the rest at construction, so the value set stays closed and a
# drifting model surfaces as a logged, skipped error rather than a new category
# leaking into the published schema.
ErrorType = Literal["format_inconsistency", "value_error", "consistency_error"]


class ErrorExample(BaseModel):
    """A single erroneous value and the 1-indexed row it was found in."""

    value: str
    row: int


class ColumnError(BaseModel):
    """A detected error pattern in one column of a tabular record set."""

    # Consumers of the profile (MoMa) turn each error into its own graph node
    # and drop anything without an identifier, so one is minted here rather
    # than in to_dict() to keep it stable across repeated serialization.
    id: str = Field(default_factory=_new_id)
    column: str
    error_type: ErrorType
    description: str
    examples: List[ErrorExample]
    total_affected_rows: int

    def to_dict(self) -> dict:
        return {
            "@type": "dg:DataQualityError",
            "@id": self.id,
            "column": self.column,
            "errorType": self.error_type,
            "description": self.description,
            "examples": [{"value": ex.value, "row": ex.row} for ex in self.examples],
            "totalAffectedRows": self.total_affected_rows,
        }


class DataQualityResult(BaseModel):
    """Data quality errors detected in a tabular record set (detection only)."""

    id: str = Field(default_factory=_new_id)
    summary: str
    errors: List[ColumnError]

    @property
    def total_affected_rows(self) -> int:
        return sum(e.total_affected_rows for e in self.errors)

    def to_dict(self) -> dict:
        return {
            "@type": "dg:DataQuality",
            "@id": self.id,
            "summary": self.summary,
            "errors": [error.to_dict() for error in self.errors],
        }
