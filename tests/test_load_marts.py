"""Warehouse load, marts and metric tests on an in-memory DuckDB."""

from __future__ import annotations

from pathlib import Path

import duckdb

from cta.analytics import metrics
from cta.etl.extract import extract_rows
from cta.etl.load import ddl, execute_script, load_rows

ROOT = Path(__file__).resolve().parents[1]


def _warehouse(sample_studies):
    con = duckdb.connect(":memory:")
    execute_script(con, ddl())
    load_rows(con, extract_rows(sample_studies))
    execute_script(con, (ROOT / "sql" / "02_marts.sql").read_text(encoding="utf-8"))
    return con


def test_load_is_idempotent(sample_studies):
    con = _warehouse(sample_studies)
    before = con.execute("SELECT COUNT(*) FROM stg_studies").fetchall()[0][0]
    load_rows(con, extract_rows(sample_studies))
    after = con.execute("SELECT COUNT(*) FROM stg_studies").fetchall()[0][0]
    assert before == 2
    assert after == 2


def test_overview_and_views(sample_studies):
    con = _warehouse(sample_studies)
    overview = metrics.overview(con)
    assert overview["n_trials"] == 2
    assert overview["completion_rate"] == 0.5
    assert overview["stopped_rate"] == 0.5
    assert overview["n_sglt2"] >= 1


def test_completion_by_sponsor(sample_studies):
    con = _warehouse(sample_studies)
    sponsors = metrics.completion_by_sponsor(con)
    assert set(sponsors["sponsor_class"]) == {"ACADEMIC", "INDUSTRY"}
    industry = sponsors[sponsors["sponsor_class"] == "INDUSTRY"].iloc[0]
    assert industry["completion_rate"] == 1.0


def test_is_sglt2_matches_gliflozin_agents():
    """A trial that names only canagliflozin must count as SGLT2."""
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000003", "briefTitle": "Canagliflozin trial"},
            "statusModule": {"overallStatus": "COMPLETED"},
            "armsInterventionsModule": {
                "interventions": [{"type": "DRUG", "name": "Canagliflozin 100 mg"}]
            },
        }
    }
    con = _warehouse([study])
    assert metrics.overview(con)["n_sglt2"] == 1


def test_upsert_replaces_values(sample_studies):
    con = _warehouse(sample_studies)
    rows = extract_rows(sample_studies)
    rows[0]["enrollment_count"] = 1500
    load_rows(con, rows[:1])
    value = con.execute("SELECT enrollment_count FROM stg_studies WHERE nct_id = ?", ["NCT00000001"]).fetchall()[0][0]
    assert value == 1500