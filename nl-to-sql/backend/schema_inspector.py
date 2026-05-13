import os
import time

from sqlalchemy import inspect, text

from db_connector import engine, get_db_type

EXCLUDED_TABLES = [
    table.strip()
    for table in os.getenv("EXCLUDED_TABLES", "").split(",")
    if table.strip()
]
SKIP_SAMPLE_TYPES = {"BLOB", "BINARY", "BYTEA", "JSON"}
TEXT_TYPE_TOKENS = {"VARCHAR", "TEXT", "CHAR"}
DATE_TOKENS = {"date", "created", "updated", "time", "at", "timestamp"}
NUMERIC_TOKENS = {
    "amount",
    "price",
    "salary",
    "total",
    "count",
    "score",
    "qty",
    "quantity",
    "revenue",
    "cost",
    "balance",
}
CATEGORY_TOKENS = {
    "status",
    "type",
    "category",
    "plan",
    "priority",
    "role",
    "department",
    "gender",
    "country",
    "city",
}


class SchemaInspector:
    def __init__(self):
        self.inspector = inspect(engine)
        self.db_type = get_db_type()
        self._schema_cache = None
        self._cache_time = 0
        self._cache_ttl = 300

    def get_tables(self) -> list[str]:
        tables = self.inspector.get_table_names()
        return [table for table in tables if table not in EXCLUDED_TABLES]

    def get_columns(self, table: str) -> list[dict]:
        columns = self.inspector.get_columns(table)
        pk_constraint = self.inspector.get_pk_constraint(table)
        pk_columns = set(pk_constraint.get("constrained_columns") or [])
        foreign_keys = self.inspector.get_foreign_keys(table)
        fk_map = {}

        for fk in foreign_keys:
            constrained_columns = fk.get("constrained_columns") or []
            referred_columns = fk.get("referred_columns") or []
            referred_table = fk.get("referred_table")
            for local_col, ref_col in zip(constrained_columns, referred_columns):
                if referred_table and ref_col:
                    fk_map[local_col] = f"{referred_table}.{ref_col}"

        results = []
        for column in columns:
            column_name = column.get("name")
            results.append(
                {
                    "name": column_name,
                    "type": str(column.get("type")),
                    "nullable": bool(column.get("nullable")),
                    "primary_key": column_name in pk_columns,
                    "foreign_key": fk_map.get(column_name),
                }
            )

        return results

    def _quote_identifier(self, name: str) -> str:
        return engine.dialect.identifier_preparer.quote(name)

    def get_sample_values(self, table: str, column: dict | str, limit: int = 4) -> list:
        try:
            if table not in self.get_tables():
                return []

            column_name = column
            column_type = ""
            if isinstance(column, dict):
                column_name = column.get("name")
                column_type = str(column.get("type", ""))

            if not column_name:
                return []

            column_names = {col["name"] for col in self.get_columns(table)}
            if column_name not in column_names:
                return []

            type_upper = column_type.upper()
            if any(token in type_upper for token in SKIP_SAMPLE_TYPES):
                return []

            safe_table = self._quote_identifier(table)
            safe_column = self._quote_identifier(column_name)
            query = text(
                f"SELECT DISTINCT {safe_column} FROM {safe_table} "
                f"WHERE {safe_column} IS NOT NULL LIMIT {int(limit)}"
            )
            with engine.connect() as connection:
                result = connection.execute(query).fetchall()

            return [str(row[0]) for row in result if row[0] is not None]
        except Exception:
            return []

    def get_row_count(self, table: str) -> int:
        try:
            if table not in self.get_tables():
                return 0
            safe_table = self._quote_identifier(table)
            query = text(f"SELECT COUNT(*) FROM {safe_table}")
            with engine.connect() as connection:
                result = connection.execute(query).scalar()
            return int(result or 0)
        except Exception:
            return 0

    def get_schema_description(self) -> str:
        if (
            self._schema_cache is not None
            and time.time() - self._cache_time < self._cache_ttl
        ):
            return self._schema_cache

        tables = self.get_tables()
        lines = [
            f"DATABASE TYPE: {self.db_type.upper()}",
            f"TOTAL TABLES: {len(tables)}",
            "==================================================",
            "",
        ]

        relationships = []

        for table in tables:
            row_count = self.get_row_count(table)
            lines.append(f"Table: {table} ({row_count:,} rows)")
            lines.append("Columns:")
            columns = self.get_columns(table)

            for column in columns:
                column_line = f"  - {column['name']}: {column['type']}"
                if column["primary_key"]:
                    column_line += "  [PRIMARY KEY]"
                if column["foreign_key"]:
                    column_line += f"  [FK → {column['foreign_key']}]"
                if not column["nullable"]:
                    column_line += "  [NOT NULL]"

                type_upper = column["type"].upper()
                is_key = column["primary_key"] or column["foreign_key"] is not None
                if any(token in type_upper for token in TEXT_TYPE_TOKENS) and not is_key:
                    samples = self.get_sample_values(table, column, limit=4)
                    if samples:
                        formatted_samples = ", ".join(f"'{value}'" for value in samples)
                        column_line += f"  — e.g. {formatted_samples}"

                lines.append(column_line)

            for column in columns:
                if column["foreign_key"]:
                    relationships.append(
                        f"{table}.{column['name']} → {column['foreign_key']}"
                    )

            lines.append("")

        lines.append("RELATIONSHIPS (Foreign Keys):")
        for relation in relationships:
            lines.append(f"  {relation}")

        if self.db_type == "sqlite":
            lines.extend(
                [
                    "",
                    "SQLITE DATE FUNCTIONS:",
                    "  Today: date('now')",
                    "  30 days ago: date('now', '-30 days')",
                    "  Group by month: strftime('%Y-%m', date_col)",
                    "  This year: strftime('%Y', date_col) = strftime('%Y','now')",
                ]
            )
        elif self.db_type == "postgresql":
            lines.extend(
                [
                    "",
                    "POSTGRESQL DATE FUNCTIONS:",
                    "  Today: CURRENT_DATE",
                    "  30 days ago: CURRENT_DATE - INTERVAL '30 days'",
                    "  Group by month: DATE_TRUNC('month', date_col)",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "MYSQL DATE FUNCTIONS:",
                    "  Today: CURDATE()",
                    "  30 days ago: DATE_SUB(CURDATE(), INTERVAL 30 DAY)",
                    "  Group by month: DATE_FORMAT(date_col, '%Y-%m')",
                ]
            )

        schema_description = "\n".join(lines)
        self._schema_cache = schema_description
        self._cache_time = time.time()
        return schema_description

    def get_tables_summary(self) -> list[dict]:
        summaries = []
        for table in self.get_tables():
            columns = self.get_columns(table)
            summaries.append(
                {
                    "name": table,
                    "row_count": self.get_row_count(table),
                    "column_count": len(columns),
                    "columns": [column["name"] for column in columns],
                }
            )
        return summaries

    def refresh_cache(self):
        self._schema_cache = None
        self._cache_time = 0
        return self.get_schema_description()

    def get_suggestions(self) -> list[str]:
        suggestions = []
        seen = set()

        for table in self.get_tables()[:5]:
            base_question = f"How many rows are in {table}?"
            if base_question not in seen:
                suggestions.append(base_question)
                seen.add(base_question)

            columns = self.get_columns(table)
            column_names = [column["name"] for column in columns]

            if any(
                token in name.lower() for name in column_names for token in DATE_TOKENS
            ):
                question = f"Show me recent {table} from the last 30 days"
                if question not in seen:
                    suggestions.append(question)
                    seen.add(question)

            for name in column_names:
                lower_name = name.lower()
                if any(token in lower_name for token in NUMERIC_TOKENS):
                    avg_question = f"What is the average {name} in {table}?"
                    if avg_question not in seen:
                        suggestions.append(avg_question)
                        seen.add(avg_question)

                    top_question = f"Show me top 10 {table} by {name} descending"
                    if top_question not in seen:
                        suggestions.append(top_question)
                        seen.add(top_question)

                if any(token in lower_name for token in CATEGORY_TOKENS):
                    group_question = f"Group {table} by {name} and show counts"
                    if group_question not in seen:
                        suggestions.append(group_question)
                        seen.add(group_question)

        return suggestions[:8]
