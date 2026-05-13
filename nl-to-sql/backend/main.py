from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from db_connector import get_db, test_connection
from models import QueryRequest
from query_engine import NLToSQLEngine
from schema_inspector import SchemaInspector
from security import QuerySecurityValidator, QueryValidationError

schema_inspector = SchemaInspector()
security_validator = QuerySecurityValidator(schema_inspector)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Checking database...")
    test_connection()
    tables = schema_inspector.get_tables()
    print(f"Connected. Found {len(tables)} tables.")
    print("Checking Ollama...")
    try:
        import requests

        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [model["name"] for model in r.json().get("models", [])]
        print(f"Ollama OK. Models: {models}")
    except Exception:
        print(
            "WARNING: Ollama not detected. "
            "Run: ollama serve && ollama pull llama3.2"
        )
    yield


app = FastAPI(title="AskDB", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/app", StaticFiles(directory="../frontend", html=True), name="frontend")


@app.get("/api/health")
def health():
    tables = schema_inspector.get_tables()
    return {
        "status": "ok",
        "db_type": schema_inspector.db_type,
        "table_count": len(tables),
    }


@app.get("/api/schema")
def get_schema():
    try:
        return {
            "tables": schema_inspector.get_tables_summary(),
            "db_type": schema_inspector.db_type,
        }
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/schema/refresh")
def refresh_schema():
    schema_inspector.refresh_cache()
    return {"message": "Schema refreshed."}


@app.get("/api/suggestions")
def get_suggestions():
    try:
        return {"suggestions": schema_inspector.get_suggestions()}
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/query")
async def run_query(body: QueryRequest, db: Session = Depends(get_db)):
    engine = NLToSQLEngine(db, schema_inspector, security_validator)
    try:
        result = await engine.query(body.question)
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except QueryValidationError as exc:
        raise HTTPException(403, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
