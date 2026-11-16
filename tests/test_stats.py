"""Statistical helper tests."""

from __future__ import annotations

import pandas as pd

from cta.analytics.stats import chi_square_completion_by_sponsor, kruskal_enrollment_by_phase, poisson_trend_by_year, wilson_ci


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