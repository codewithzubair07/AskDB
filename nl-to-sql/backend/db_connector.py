import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

load_dotenv()


def get_db_type() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Check DATABASE_URL in .env")

    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("postgresql"):
        return "postgresql"
    if database_url.startswith("mysql"):
        return "mysql"

    raise RuntimeError("Unsupported DATABASE_URL. Use sqlite, postgresql, or mysql.")


def build_engine():
    database_url = os.getenv("DATABASE_URL")
    db_type = get_db_type()

    if db_type == "sqlite":
        return create_engine(database_url, connect_args={"check_same_thread": False})

    if db_type in {"postgresql", "mysql"}:
        return create_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

    raise RuntimeError("Unsupported DATABASE_URL. Use sqlite, postgresql, or mysql.")


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except (ConnectionError, OperationalError) as exc:
        raise RuntimeError(
            "Cannot connect to database. Check DATABASE_URL in .env"
        ) from exc

    return True
