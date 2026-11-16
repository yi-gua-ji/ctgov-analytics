"""Statistical tests used in the insights report."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

Z95 = 1.959963984540054


def wilson_ci(successes: int, n: int, z: float = Z95) -> tuple[float | None, float | None]:
    """Wilson score interval for a proportion."""
    if n <= 0:
        return None, None
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)


def chi_square_completion_by_sponsor(df: pd.DataFrame, min_n: int = 30) -> dict:
    """Chi-square test: does completion rate differ across sponsor classes?

    df is the output of metrics.completion_by_sponsor. Small strata are
    dropped to keep expected counts usable for the approximation.
    """
    usable = df[df["n_trials"] >= min_n].copy()
    usable["n_incomplete"] = usable["n_trials"] - usable["n_completed"]
    table = usable[["n_completed", "n_incomplete"]].to_numpy()
    if table.shape[0] < 2:
        return {"test": "chi2", "error": "not enough sponsor classes", "p_value": None}
    chi2, p_value, dof, expected = stats.chi2_contingency(table)
    return {
        "test": "chi-square (completion rate vs sponsor class)",
        "chi2": round(float(chi2), 3),
        "dof": int(dof),
        "p_value": float(p_value),
        "n_classes": int(table.shape[0]),
        "min_expected": round(float(expected.min()), 2),
    }


def kruskal_enrollment_by_phase(df: pd.DataFrame, min_n: int = 10) -> dict:
    """Kruskal-Wallis test of enrollment counts across phases.

    df must carry phase_category and enrollment_count columns (raw trials).
    """
    groups = []
    labels = []
    for label, subset in df.groupby("phase_category"):
        values = subset["enrollment_count"].dropna().astype(float)
        if len(values) >= min_n:
            groups.append(values.to_numpy())
            labels.append(str(label))
    if len(groups) < 2:
        return {"test": "kruskal", "error": "not enough groups", "p_value": None}
    statistic, p_value = stats.kruskal(*groups)
    return {
        "test": "Kruskal-Wallis (enrollment across phases)",
        "statistic": round(float(statistic), 3),
        "p_value": float(p_value),
        "groups": labels,
    }


def poisson_trend_by_year(df: pd.DataFrame, count_column: str = "n_trials") -> dict:
    """Poisson GLM of a yearly count with an incidence rate ratio and 95% CI."""
    data = df.dropna(subset=["start_year", count_column])
    data = data[(data["start_year"] >= 1990) & (data[count_column] >= 0)]
    if len(data) < 5:
        return {"test": "poisson", "error": "not enough years", "p_value": None}
    x = sm.add_constant(data["start_year"].astype(float).to_numpy())
    y = data[count_column].astype(float).to_numpy()
    model = sm.GLM(y, x, family=sm.families.Poisson())
    results = model.fit()
    coef = results.params[1]
    ci_low, ci_high = results.conf_int()[1]
    return {
        "test": "Poisson GLM trend (annual count)",
        "irr_per_year": round(float(np.exp(coef)), 4),
        "ci_low": round(float(np.exp(ci_low)), 4),
        "ci_high": round(float(np.exp(ci_high)), 4),
        "p_value": float(results.pvalues[1]),
        "n_years": int(len(data)),
    }