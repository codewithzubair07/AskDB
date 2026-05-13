import os
import re
import time

import requests
from sqlalchemy import text

from db_connector import get_db_type
from security import QueryValidationError

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

SYSTEM_PROMPT = """You are an expert SQL query writer.
Convert the natural language question into a correct 
SQL SELECT query for a {db_type} database.

STRICT RULES:
1. Output ONLY raw SQL. No explanation. No markdown.
   No backticks. No comments. Just valid SQL.
2. Only SELECT — never INSERT, UPDATE, DELETE, DROP, ALTER.
3. Use proper JOINs with ON clause always.
4. Select only columns relevant to the question.
5. Add ORDER BY when results have a natural order.
6. Always include LIMIT (max 200).
7. Use exact table and column names from the schema.
   Never invent or guess column names.
8. {date_hint}

{schema}

Respond with ONLY the SQL query, nothing else."""

DATE_HINTS = {
    "sqlite": (
        "Use SQLite date functions: date('now'), "
        "date('now','-30 days'), strftime('%Y-%m', col)"
    ),
    "postgresql": (
        "Use PostgreSQL functions: CURRENT_DATE, "
        "CURRENT_DATE - INTERVAL '30 days', "
        "DATE_TRUNC('month', col)"
    ),
    "mysql": (
        "Use MySQL functions: CURDATE(), "
        "DATE_SUB(CURDATE(), INTERVAL 30 DAY), "
        "DATE_FORMAT(col, '%Y-%m')"
    ),
}


class NLToSQLEngine:
    def __init__(self, db, schema_inspector, security_validator):
        self.db = db
        self.schema = schema_inspector
        self.security = security_validator
        self.db_type = get_db_type()

    def _call_ollama(self, question: str) -> str:
        prompt = SYSTEM_PROMPT.format(
            db_type=self.db_type.upper(),
            date_hint=DATE_HINTS.get(self.db_type, ""),
            schema=self.schema.get_schema_description(),
        )

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{prompt}\n\nQuestion: {question}\n\nSQL:",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 400,
                "stop": ["\n\n", "Question:", "--", "/*"],
            },
        }

        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=90)
            resp.raise_for_status()
            raw = resp.json().get("response", "").strip()
            return self._clean_sql(raw)
        except requests.ConnectionError as exc:
            raise RuntimeError(
                "Ollama is not running.\nFix: ollama serve\nThen: ollama pull llama3.2"
            ) from exc
        except requests.Timeout as exc:
            raise RuntimeError("Ollama timed out. Try a simpler question.") from exc

    def _clean_sql(self, raw: str) -> str:
        if not raw:
            return ""

        cleaned = raw.replace("```sql", "").replace("```", "")
        cleaned = cleaned.replace("`", "").strip()
        cleaned = cleaned.split(";")[0].strip()

        stop_prefixes = (
            "this",
            "note:",
            "explanation",
            "the above",
            "the query",
            "result:",
            "here",
        )
        lines = []
        for line in cleaned.splitlines():
            if line.strip().lower().startswith(stop_prefixes):
                break
            lines.append(line)

        cleaned = " ".join(" ".join(lines).split()).strip()

        if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
            match = re.search(r"(SELECT|WITH)\b", cleaned, re.IGNORECASE)
            if match:
                cleaned = cleaned[match.start() :].strip()

        return cleaned

    def _detect_chart(self, columns, rows) -> str | None:
        if not rows or len(columns) < 2:
            return None
        try:
            float(str(rows[0][1]))
            first_val = str(rows[0][0])
            if re.search(r"\d{4}[-/]\d{2}", first_val):
                return "line"
            if len(rows) <= 7:
                return "pie"
            return "bar"
        except Exception:
            return None

    def _explain(self, question: str, sql: str) -> str:
        sql_upper = sql.upper()
        parts = []
        if "JOIN" in sql_upper:
            parts.append("joins tables")
        if "GROUP BY" in sql_upper:
            parts.append("groups data")
        if "WHERE" in sql_upper:
            parts.append("filters rows")
        if "ORDER BY" in sql_upper:
            parts.append("sorts results")
        if "COUNT" in sql_upper:
            parts.append("counts records")
        if "SUM" in sql_upper:
            parts.append("sums values")
        if "AVG" in sql_upper:
            parts.append("averages values")

        if parts:
            return f"This query {' and '.join(parts)} to answer your question."
        return "This query answers your question."

    async def query(self, question: str) -> dict:
        start = time.time()
        warnings = []
        max_rows = int(os.getenv("MAX_ROWS", "200"))

        sql = self._call_ollama(question)
        if not sql or len(sql) < 7:
            raise ValueError("Could not generate SQL. Try rephrasing.")

        self.security.is_safe_query(sql)
        self.security.validate_tables(sql)
        sql = self.security.sanitize_query(sql)

        try:
            result = self.db.execute(text(sql))
            columns = list(result.keys())
            rows = [list(r) for r in result.fetchall()]
        except Exception as exc:
            raise RuntimeError(
                f"SQL Error: {str(exc)}\n\nSQL tried:\n{sql}\n\n"
                "Try rephrasing your question."
            ) from exc

        elapsed = round((time.time() - start) * 1000, 1)

        if len(rows) >= max_rows:
            warnings.append(
                f"Capped at {max_rows} rows. "
                "Refine your question for fewer results."
            )

        return {
            "sql": sql,
            "explanation": self._explain(question, sql),
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "execution_time_ms": elapsed,
            "warnings": warnings,
            "chart_suggestion": self._detect_chart(columns, rows),
        }
