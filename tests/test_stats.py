"""Statistical helper tests."""

from __future__ import annotations

import pandas as pd

from cta.analytics.stats import (
    chi_square_completion_by_sponsor,
    kruskal_enrollment_by_phase,
    poisson_trend_by_year,
    wilson_ci,
)


def test_wilson_ci_bounds():
    low, high = wilson_ci(50, 100)
    assert low < 0.5 < high
    assert wilson_ci(0, 0) == (None, None)


def test_chi_square_detects_different_rates():
    df = pd.DataFrame({
        "sponsor_class": ["A", "B"],
        "n_trials": [100, 100],
        "n_completed": [80, 20],
    })
    result = chi_square_completion_by_sponsor(df)
    assert result["p_value"] < 0.001
    assert result["n_classes"] == 2


def test_kruskal_runs_on_two_groups():
    df = pd.DataFrame({
        "phase_category": ["PHASE2"] * 20 + ["PHASE3"] * 20,
        "enrollment_count": [50 + i for i in range(20)] + [500 + i for i in range(20)],
    })
    result = kruskal_enrollment_by_phase(df)
    assert result["p_value"] < 0.05


def test_poisson_trend_direction():
    df = pd.DataFrame({
        "start_year": list(range(2010, 2016)),
        "n_trials": [10, 12, 15, 18, 22, 27],
    })
    result = poisson_trend_by_year(df)
    assert result["irr_per_year"] > 1.0
    assert result["p_value"] < 0.05

def test_poisson_trend_excludes_partial_and_future_years():
    """The default window stops at the last complete year, not at the caller's data."""
    years = list(range(2000, 2026))
    counts = [10 + i for i in range(len(years))]
    df = pd.DataFrame({"start_year": [*years, 2026, 2027], "n_trials": [*counts, 9000, 1]})
    result = poisson_trend_by_year(df)
    assert result["window"].endswith("2025")
    assert result["n_years"] == 26
    assert result["irr_per_year"] < 2.0


def test_poisson_trend_window_is_configurable():
    df = pd.DataFrame({
        "start_year": list(range(2005, 2021)),
        "n_trials": [10 + i for i in range(16)],
    })
    default = poisson_trend_by_year(df)
    narrow = poisson_trend_by_year(df, min_year=2010)
    assert default["n_years"] == 16
    assert narrow["n_years"] == 11
    assert narrow["window"] == "2010-2025"
