from typing import Any, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class QueryResponse(BaseModel):
    sql: str
    explanation: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float
    warnings: list[str]
    chart_suggestion: Optional[str]


class TableSummary(BaseModel):
    name: str
    row_count: int
    column_count: int
    columns: list[str]


class SchemaResponse(BaseModel):
    tables: list[TableSummary]
    db_type: str


class SuggestionsResponse(BaseModel):
    suggestions: list[str]


class HealthResponse(BaseModel):
    status: str
    db_type: str
    table_count: int
