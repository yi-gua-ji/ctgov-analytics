# ctgov-analytics

[![tests](https://github.com/yi-gua-ji/ctgov-analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/yi-gua-ji/ctgov-analytics/actions/workflows/tests.yml)
[![license](https://img.shields.io/github/license/yi-gua-ji/ctgov-analytics)](https://github.com/yi-gua-ji/ctgov-analytics/blob/main/LICENSE)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](https://github.com/yi-gua-ji/ctgov-analytics)

An end-to-end data pipeline and analysis layer over **ClinicalTrials.gov v2**:
ingest cardiometabolic trials, land raw payloads, build a typed DuckDB
warehouse with SQL marts, run metric and hypothesis tests, and explore the
result in a Streamlit dashboard.

Built as a data-engineering / data-analysis portfolio project: every layer is
testable offline, the pipeline is idempotent, and the statistical claims in
the report point to the function that produced them.

## Architecture

```text
ClinicalTrials.gov v2 API
        |  async client: paging, retry/backoff, pacing
        v
data/raw/*.jsonl          bronze: verbatim studies + fetched_at
        |  extract.py: flatten v2 JSON -> warehouse rows
        |  validate.py: rules (critical vs warning) + missingness
        v
DuckDB: stg_studies       silver: typed, keyed by nct_id (idempotent upsert)
        |  sql/02_marts.sql: SQL views
        v
v_trials, v_*_by_*       gold: reviewable metric views
        |
        +--> analytics/metrics.py   metric definitions as SQL
        +--> analytics/stats.py     chi-square, Kruskal-Wallis, Poisson trend
        +--> analytics/insights.py  reports/insights.md
        +--> dashboard/app.py       Streamlit exploration UI
```

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev,dashboard]"
python scripts/run_pipeline.py --max-studies 800   # ~1-2 min, ~3-4k trials
streamlit run src/cta/dashboard/app.py            # dashboard
pytest -q                                          # offline tests
```

Outputs after a run:

- `data/raw/*.jsonl` - raw API payloads per query (bronze)
- `data/ctgov.duckdb` - warehouse (silver) + `etl_runs` bookkeeping
- `reports/quality_report.json` - data-quality violations and missingness
- `reports/insights.md` - metric tables + statistical tests

## What the pipeline guarantees

- **Idempotent loads**: `INSERT OR REPLACE` keyed by `nct_id`; re-running a
  query does not duplicate rows (tested).
- **Incremental by query**: each run writes a timestamped bronze snapshot per
  query under `data/raw/` and upserts the warehouse; `etl_runs` keeps a run log
  with counts and status.
- **Quality gates**: `nct_id` format and duplicates are critical (strict mode
  exits 2); enum, date-order and enrollment rules are warnings and are
  counted in the quality report.
- **Reproducible statistics**: all tests live in `analytics/stats.py`, are
  listed in the report with their statistic and p-value, and are unit tested.

## Analysis

`reports/insights.md` covers:

1. Trials per start year (with a Poisson GLM trend: IRR per year, 95% CI,
   computed on completed registry years only — pre-2000 retrospective
   registrations and future-dated planned trials are excluded, and a
   window-sensitivity table shows the estimate is not an artefact of the
   window choice).
2. Phase distribution and enrollment by phase (Kruskal-Wallis).
3. Completion and stopping rates by sponsor class (chi-square screening test;
   Wilson 95% intervals per class).
4. SGLT2-related trial trend (Poisson IRR; the class flag matches the SGLT2
   acronym and every gliflozin agent name, so canagliflozin-only trials count).
5. Top conditions and a data-quality table (missingness, results availability).

Every table is generated from the SQL marts, and the method notes state the
observational limits (sponsor class is confounded with phase, size and disease
area; the chi-square test is a screening test, not a causal estimate).

## Results

Snapshot from the committed run (`docs/insights.md`, 2026-11-16): five queries,
1,200 studies per query, 4,971 unique trials after NCT-id deduplication.

| Metric | Value |
| --- | --- |
| Trials in warehouse | 4,971 (from 5,183 fetched rows; overlapping queries deduplicated) |
| Start years covered | 1965 - 2028 |
| Completed share | 49.5% |
| Stopped share (terminated/withdrawn/suspended) | 7.5% |
| Median enrollment | 114 participants |
| Trials with posted results | 14.7% |
| SGLT2-related trials | 589 (11.8%) |
| Annual trial-count trend (Poisson, 2000-2025) | IRR 1.092 per year (95% CI 1.087-1.097, p<0.001) |
| Trend window sensitivity | IRR 1.0755 (2005-2025), 1.0698 (2010-2025), 1.0786 (2015-2025) |
| SGLT2 annual trend (Poisson, 2000-2025) | IRR 1.236 per year (95% CI 1.212-1.260, p<0.001) |
| Completion differs by sponsor class | chi2 = 192.4, p<0.001 (Industry 68.1% vs Other 44.5%) |
| Enrollment differs by phase | Kruskal H = 366.3, p<0.001 (Phase1 ~42, Phase2 ~72, Phase3 ~264 medians) |
| Missingness | enrollment 0.7%, start date 0.3%, phase 22.5% |

The full per-year tables, per-sponsor rates and the method notes live in
`docs/insights.md`; the rule-level quality report is
`docs/quality_report.json`.

## Project layout

| Path | Purpose |
| --- | --- |
| `src/cta/http.py` | async ClinicalTrials.gov client |
| `src/cta/etl/extract.py` | JSON -> typed rows |
| `src/cta/etl/validate.py` | data-quality rules |
| `src/cta/etl/load.py` | DuckDB DDL + idempotent upsert + run log |
| `sql/02_marts.sql` | reviewable metric views |
| `src/cta/analytics/*` | metrics, statistics, insights report |
| `src/cta/dashboard/app.py` | Streamlit dashboard |
| `tests/` | offline unit tests |

## Limitations

- The five queries are a convenience sample of cardiometabolic trials, not a
  census of ClinicalTrials.gov; rates describe this slice only.
- Enrollment fields are self-reported by sponsors and often missing or
  estimated; the report shows the missingness explicitly.
- Completion status is a point-in-time snapshot; terminated trials may later
  resume, and completed trials may add follow-up results.

## License

MIT