"""Row extraction tests (no network)."""

from __future__ import annotations

from cta.etl.extract import extract_rows, parse_date, study_to_row


def test_study_to_row_flattens_fields(sample_studies):
    row = study_to_row(sample_studies[0])
    assert row["nct_id"] == "NCT00000001"
    assert row["status"] == "COMPLETED"
    assert row["phase_category"] == "PHASE3"
    assert row["enrollment_count"] == 1200
    assert row["enrollment_type"] == "ACTUAL"
    assert row["sponsor_class"] == "INDUSTRY"
    assert row["interventions"] == "Empagliflozin"
    assert row["start_date"] == "2020-03-04"
    assert row["primary_completion_date"] == "2022-06-01"
    assert row["has_results"] is True
    assert row["n_primary_outcomes"] == 1


def test_combined_phase_is_categorized(sample_studies):
    row = study_to_row(sample_studies[1])
    assert row["phase_category"] == "COMBINED"
    assert row["phases"] == "PHASE2; PHASE3"
    assert row["start_date"] == "2018-01-01"


def test_extract_rows_skips_malformed():
    rows = extract_rows([{"protocolSection": {"identificationModule": {"nctId": "NCT00000003"}}}, {None: 1}])
    assert len(rows) == 1
    assert rows[0]["nct_id"] == "NCT00000003"


def test_parse_date_variants():
    assert parse_date("2023") == "2023-01-01"
    assert parse_date("2023-07") == "2023-07-01"
    assert parse_date("2023-07-15") == "2023-07-15"
    assert parse_date("") is None
    assert parse_date(None) is None
    assert parse_date("not-a-date") is None