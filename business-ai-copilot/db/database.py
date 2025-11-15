import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

load_dotenv()

DB_DIALECT = os.getenv("DB_DIALECT", "mssql+pymssql")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    raise RuntimeError("Database credentials not fully set in .env")

DB_URL = f"{DB_DIALECT}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DB_URL)

def run_query(query: str, params: dict | None = None):
    """Run a read-only query and return list of dict rows."""
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        # SQLAlchemy 2.x: use mappings() to get dict-like rows
        return [dict(row) for row in result.mappings()]

def get_schema_summary() -> str:
    """Return a text description of tables & columns for prompting the LLM."""
    insp = inspect(engine)
    lines: list[str] = []
    for table_name in insp.get_table_names():
        cols = insp.get_columns(table_name)
        col_str = ", ".join(f"{c['name']}({str(c['type'])})" for c in cols)
        lines.append(f"{table_name}: {col_str}")
    return "\n".join(lines)
