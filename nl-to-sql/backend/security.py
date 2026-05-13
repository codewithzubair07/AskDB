import logging
import os
import re

from schema_inspector import SchemaInspector

logging.basicConfig(
    filename="security.log",
    level=logging.WARNING,
    format="%(asctime)s BLOCKED: %(message)s",
)

BLOCKED_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bCREATE\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bREPLACE\b",
    r"\bMERGE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bxp_\w+",
    r"sqlite_master",
    r"information_schema",
    r"pg_catalog",
    r"sys\.",
    r"--",
    r"/\*",
    r"\*/",
]


class QueryValidationError(Exception):
    pass


class QuerySecurityValidator:
    def __init__(self, schema_inspector: SchemaInspector):
        self.allowed_tables = {table.lower() for table in schema_inspector.get_tables()}

    def is_safe_query(self, sql: str) -> bool:
        sql_upper = sql.upper().strip()

        if not re.match(r"^(SELECT|WITH)\b", sql_upper):
            logging.warning("Non-SELECT query blocked: %s", sql.strip())
            raise QueryValidationError(
                "Only SELECT queries allowed. AskDB is read-only."
            )

        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                logging.warning("Blocked pattern '%s' in query: %s", pattern, sql.strip())
                raise QueryValidationError("Query contains a disallowed operation.")

        clean = re.sub(r"'[^']*'", "''", sql)
        if clean.count(";") > 0:
            logging.warning("Multiple statements blocked: %s", sql.strip())
            raise QueryValidationError("Multiple SQL statements not allowed.")

        return True

    def validate_tables(self, sql: str) -> bool:
        pattern = r"\b(?:FROM|JOIN)\s+([`\"\[]?\w+[`\"\]]?)"
        found = re.findall(pattern, sql, re.IGNORECASE)
        for table in found:
            cleaned = table.strip("`\"[]").lower()
            if cleaned not in self.allowed_tables:
                logging.warning("Unknown table '%s' in query: %s", cleaned, sql.strip())
                raise QueryValidationError(
                    f"Table '{cleaned}' not found in your database."
                )
        return True

    def sanitize_query(self, sql: str) -> str:
        sql = sql.strip().rstrip(";").strip()
        sql = " ".join(sql.split())
        max_rows = int(os.getenv("MAX_ROWS", "200"))
        if "LIMIT" not in sql.upper():
            sql += f" LIMIT {max_rows}"
        return sql
