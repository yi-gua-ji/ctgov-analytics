"""DuckDB warehouse: schema, idempotent upsert and run bookkeeping."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .extract import STUDY_COLUMNS

INT_COLUMNS = {"enrollment_count", "n_primary_outcomes"}
BOOL_COLUMNS = {"has_results"}


def ddl() -> str:
    """DDL for the staging table and the ETL run log."""
    columns = ",\n    ".join(f"{name} {sql_type}" for name, sql_type in STUDY_COLUMNS)
    return f"""
CREATE TABLE IF NOT EXISTS stg_studies (
    {columns}
);
CREATE TABLE IF NOT EXISTS etl_runs (
    run_id VARCHAR PRIMARY KEY,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    n_fetched BIGINT,
    n_upserted BIGINT,
    queries VARCHAR,
    status VARCHAR
);
"""


def connect(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """Open (or create) the warehouse and ensure the schema exists."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    execute_script(con, ddl())
    return con


def _typed_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    columns = [name for name, _ in STUDY_COLUMNS]
    df = pd.DataFrame(rows).reindex(columns=columns)
    for name in columns:
        if name in INT_COLUMNS:
            df[name] = pd.array(df[name], dtype="Int64")
        elif name in BOOL_COLUMNS:
            df[name] = pd.array(df[name], dtype="boolean")
    return df


def load_rows(con: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> int:
    """Idempotently upsert rows into stg_studies keyed by nct_id."""
    if not rows:
        return 0
    df = _typed_frame(rows)
    con.register("stg_new", df)
    try:
        con.execute("INSERT OR REPLACE INTO stg_studies SELECT * FROM stg_new")
    finally:
        con.unregister("stg_new")
    return len(df)


def record_run(
    con: duckdb.DuckDBPyConnection,
    n_fetched: int,
    n_upserted: int,
    queries: list[str],
    status: str,
    started_at: datetime | None = None,
    run_id: str | None = None,
) -> str:
    """Record one pipeline run in etl_runs."""
    run_id = run_id or uuid.uuid4().hex[:12]
    started_at = started_at or datetime.now(timezone.utc)
    con.execute(
        "INSERT OR REPLACE INTO etl_runs VALUES (?, ?, ?, ?, ?, ?, ?)",
        [run_id, started_at, datetime.now(timezone.utc), n_fetched, n_upserted, "; ".join(queries), status],
    )
    return run_id
def execute_script(con: duckdb.DuckDBPyConnection, sql: str) -> None:
    """Execute a multi-statement SQL file one statement at a time.

    DuckDB keeps a pending result after a multi-statement execute, which
    breaks later register() calls on the same connection.
    """
    for statement in sql.split(";"):
        if statement.strip():
            con.execute(statement)
