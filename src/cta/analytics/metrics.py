"""Metric definitions as DuckDB queries over the marts."""

from __future__ import annotations

import duckdb
import pandas as pd


def _frame(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    return con.execute(sql).df()


def overview(con: duckdb.DuckDBPyConnection) -> dict:
    row = con.execute(
        """
        SELECT COUNT(*) AS n_trials,
               COUNT(DISTINCT sponsor_class) AS n_sponsor_classes,
               MIN(start_year) AS first_start_year,
               MAX(start_year) AS last_start_year,
               ROUND(AVG(CASE WHEN is_completed = 1 THEN 1.0 ELSE 0 END), 4) AS completion_rate,
               ROUND(AVG(CASE WHEN is_stopped = 1 THEN 1.0 ELSE 0 END), 4) AS stopped_rate,
               ROUND(MEDIAN(enrollment_count), 1) AS median_enrollment,
               SUM(is_sglt2) AS n_sglt2
        FROM v_trials
        """
    ).fetchall()[0]
    keys = [
        "n_trials", "n_sponsor_classes", "first_start_year", "last_start_year",
        "completion_rate", "stopped_rate", "median_enrollment", "n_sglt2",
    ]
    return dict(zip(keys, row))


def trials_by_year(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return _frame(con, "SELECT * FROM v_trials_by_year")


def phase_distribution(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return _frame(con, "SELECT * FROM v_phase_distribution")


def completion_by_sponsor(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return _frame(con, "SELECT * FROM v_completion_by_sponsor")


def enrollment_by_phase(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return _frame(con, "SELECT * FROM v_enrollment_by_phase")


def top_conditions(con: duckdb.DuckDBPyConnection, limit: int = 10) -> pd.DataFrame:
    return _frame(con, f"SELECT * FROM v_top_conditions LIMIT {int(limit)}")


def sglt2_trend(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return _frame(con, "SELECT * FROM v_sglt2_trend")


def data_quality(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Missingness and coverage per key field."""
    return _frame(
        con,
        """
        SELECT
          COUNT(*) AS n_trials,
          ROUND(avg(CASE WHEN enrollment_count IS NULL THEN 1.0 ELSE 0 END), 4) AS pct_missing_enrollment,
          ROUND(avg(CASE WHEN start_date IS NULL THEN 1.0 ELSE 0 END), 4) AS pct_missing_start,
          ROUND(avg(CASE WHEN completion_date IS NULL THEN 1.0 ELSE 0 END), 4) AS pct_missing_completion,
          ROUND(avg(CASE WHEN sponsor_class IS NULL THEN 1.0 ELSE 0 END), 4) AS pct_missing_sponsor,
          ROUND(avg(CASE WHEN phase_category IS NULL THEN 1.0 ELSE 0 END), 4) AS pct_missing_phase,
          SUM(CASE WHEN has_results THEN 1 ELSE 0 END) AS n_with_results,
          ROUND(avg(CASE WHEN has_results THEN 1.0 ELSE 0 END), 4) AS pct_with_results
        FROM v_trials
        """
    )