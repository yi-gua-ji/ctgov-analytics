"""Data-quality rule tests."""

from __future__ import annotations

from cta.etl.validate import validate_rows


def _row(**overrides):
    base = {
        "nct_id": "NCT00000001",
        "status": "COMPLETED",
        "phase_category": "PHASE3",
        "enrollment_count": 1200,
        "start_date": "2020-01-01",
        "primary_completion_date": "2021-01-01",
        "completion_date": "2022-01-01",
        "has_results": True,
    }
    base.update(overrides)
    return base


def test_valid_row_passes():
    result = validate_rows([_row()])
    assert result["ok"] is True
    assert result["critical"] == 0


def test_invalid_nct_id_is_critical():
    result = validate_rows([_row(nct_id="BAD123")])
    assert result["ok"] is False
    assert result["critical"] == 1
    assert result["violations_by_rule"]["nct_id_format"] == 1


def test_duplicate_nct_id_is_a_warning():
    # Overlapping queries naturally return the same trial twice; the warehouse
    # upserts on nct_id, so duplicates are reported but not fatal.
    result = validate_rows([_row(), _row()])
    assert result["ok"] is True
    assert result["violations_by_rule"]["nct_id_duplicate"] == 1


def test_negative_enrollment_is_warning():
    result = validate_rows([_row(enrollment_count=-5)])
    assert result["ok"] is True
    assert result["violations_by_rule"]["enrollment_invalid"] == 1


def test_date_order_violation_is_warning():
    result = validate_rows([_row(start_date="2023-01-01", primary_completion_date="2022-01-01")])
    assert result["ok"] is True
    assert result["violations_by_rule"]["date_order_start_primary"] == 1


def test_missingness_reported():
    rows = [_row(), _row(nct_id="NCT00000002", enrollment_count=None)]
    result = validate_rows(rows)
    assert result["missingness"]["enrollment_count"] == 0.5