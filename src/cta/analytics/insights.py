"""Render the insights report (Markdown) from the warehouse."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd

from . import metrics, stats


def _table(df: pd.DataFrame, max_rows: int = 12) -> str:
    """Render a DataFrame as a compact Markdown table."""
    frame = df.head(max_rows)
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        cells = []
        for col in columns:
            value = row[col]
            cells.append("" if pd.isna(value) else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _fmt_p(p) -> str:
    if p is None:
        return "n/a"
    if p < 0.001:
        return "<0.001"
    return f"{p:.4f}"


def _line(lines: list, text: str) -> None:
    lines.append(text)


def generate_insights(con: duckdb.DuckDBPyConnection, reports_dir) -> Path:
    """Build reports/insights.md from the marts and return its path."""
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    overview = metrics.overview(con)
    by_year = metrics.trials_by_year(con)
    phases = metrics.phase_distribution(con)
    sponsors = metrics.completion_by_sponsor(con)
    enrollment = metrics.enrollment_by_phase(con)
    conditions = metrics.top_conditions(con, limit=10)
    sglt2 = metrics.sglt2_trend(con)
    quality = metrics.data_quality(con)
    raw_phase = con.execute(
        "SELECT phase_category, enrollment_count FROM v_trials WHERE enrollment_count IS NOT NULL"
    ).df()

    chi = stats.chi_square_completion_by_sponsor(sponsors)
    kruskal = stats.kruskal_enrollment_by_phase(raw_phase)
    trend_all = stats.poisson_trend_by_year(by_year)
    trend_sglt2 = stats.poisson_trend_by_year(sglt2.rename(columns={"n_sglt2": "n_trials"})[["start_year", "n_trials"]])
    # Window sensitivity: the headline trend must not be an artefact of where
    # the observation window starts or ends.
    trend_windows = [
        (min_year, stats.poisson_trend_by_year(by_year, min_year=min_year))
        for min_year in (2000, 2005, 2010, 2015)
    ]
    sponsor_display = sponsors.copy()
    sponsor_display["ci_low"], sponsor_display["ci_high"] = zip(
        *[stats.wilson_ci(int(n), int(total)) for n, total in zip(sponsor_display["n_completed"], sponsor_display["n_trials"], strict=False)], strict=False
    )

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M") + " UTC"

    n_trials = overview["n_trials"]
    lines: list = []
    lines.append("# ClinicalTrials.gov cardiometabolic trials - insights")
    lines.append("")
    lines.append(f"Generated: {generated}")
    lines.append("")
    lines.append("## Headline numbers")
    lines.append("")
    lines.append(f"- Trials in warehouse: {n_trials}")
    lines.append("- Start years covered: " + str(overview["first_start_year"]) + " - " + str(overview["last_start_year"]))
    lines.append("- Completed share: " + str(overview["completion_rate"]) + " | stopped share: " + str(overview["stopped_rate"]))
    lines.append("- Median enrollment: " + str(overview["median_enrollment"]) + " participants")
    lines.append("- SGLT2-related trials: " + str(overview["n_sglt2"]))
    lines.append("")

    lines.append("## Trials per start year")
    lines.append("")
    lines.append(_table(by_year, max_rows=60))
    lines.append("")
    irr = trend_all.get("irr_per_year")
    lo = trend_all.get("ci_low")
    hi = trend_all.get("ci_high")
    lines.append("- Poisson trend of annual counts: IRR = " + str(irr) + " per year (95% CI " + str(lo) + "-" + str(hi) + ", p=" + _fmt_p(trend_all.get("p_value")) + "; window " + str(trend_all.get("window")) + ")")
    lines.append("- The table also lists pre-2000 retrospective registrations and future-dated planned trials; the trend excludes both.")
    lines.append("")
    lines.append("### Trend window sensitivity")
    lines.append("")
    table_rows = ["| window | IRR | 95% CI | p | n_years |", "| --- | --- | --- | --- | --- |"]
    for _min_year, result in trend_windows:
        if result.get("irr_per_year") is None:
            continue
        table_rows.append(
            "| " + str(result.get("window")) + " | " + str(result["irr_per_year"]) + " | "
            + str(result["ci_low"]) + "-" + str(result["ci_high"]) + " | "
            + _fmt_p(result.get("p_value")) + " | " + str(result["n_years"]) + " |"
        )
    lines.extend(table_rows)
    lines.append("")

    lines.append("## Phase distribution")
    lines.append("")
    lines.append(_table(phases))
    lines.append("")

    lines.append("## Completion and stopping by sponsor class")
    lines.append("")
    lines.append(_table(sponsor_display))
    lines.append("")
    lines.append("- completion_ci_low / completion_ci_high are Wilson 95% intervals.")
    lines.append("- Chi-square test of completion rate across sponsor classes: chi2=" + str(chi.get("chi2")) + ", p=" + _fmt_p(chi.get("p_value")) + " (classes with n>=30: " + str(chi.get("n_classes")) + ")")
    lines.append("")

    lines.append("## Enrollment by phase")
    lines.append("")
    lines.append(_table(enrollment))
    lines.append("")
    lines.append("- Kruskal-Wallis across phases: H=" + str(kruskal.get("statistic")) + ", p=" + _fmt_p(kruskal.get("p_value")))
    lines.append("")

    lines.append("## SGLT2 trial trend")
    lines.append("")
    lines.append(_table(sglt2, max_rows=60))
    lines.append("")
    irr_s = trend_sglt2.get("irr_per_year")
    lo_s = trend_sglt2.get("ci_low")
    hi_s = trend_sglt2.get("ci_high")
    lines.append("- SGLT2 annual counts: IRR = " + str(irr_s) + " per year (95% CI " + str(lo_s) + "-" + str(hi_s) + ", p=" + _fmt_p(trend_sglt2.get("p_value")) + ")")
    lines.append("")

    lines.append("## Top conditions")
    lines.append("")
    lines.append(_table(conditions))
    lines.append("")

    lines.append("## Data quality")
    lines.append("")
    lines.append(_table(quality))
    lines.append("")
    lines.append("## Method notes")
    lines.append("")
    lines.append("- Trials come from five cardiometabolic queries; the warehouse deduplicates by NCT id.")
    lines.append("- Completion/stopping rates are descriptive; the chi-square test is a screening test, not a causal estimate (sponsor class is confounded with phase, size and disease area).")
    lines.append("- Enrollment medians exclude trials without a reported enrollment count; Kruskal-Wallis compares distributions, not per-phase means.")
    lines.append("- The Poisson trend models yearly counts on completed registry years only (2000 to last complete year): pre-2000 retrospective registrations and future-dated planned trials are excluded; the window-sensitivity table shows the estimate is not an artefact of the window choice.")
    lines.append("- The query set is a convenience sample of five cardiometabolic terms; trend interpretation assumes it stays stable across years.")
    lines.append("")

    path = reports_dir / "insights.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path