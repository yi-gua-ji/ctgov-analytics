-- Marts (views) over the staging table. Loaded after every ingest.
-- Keeping the transformations as SQL makes them reviewable and portable
-- (the dashboard and the insights report both read these views).

CREATE OR REPLACE VIEW v_trials AS
SELECT
    nct_id,
    title,
    status,
    phases,
    phase_category,
    enrollment_count,
    enrollment_type,
    conditions,
    interventions,
    intervention_types,
    sponsor_name,
    sponsor_class,
    start_date,
    primary_completion_date,
    completion_date,
    allocation,
    intervention_model,
    masking,
    primary_purpose,
    n_primary_outcomes,
    primary_outcome_first,
    has_results,
    CAST(substr(start_date, 1, 4) AS INTEGER) AS start_year,
    CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END AS is_completed,
    CASE WHEN status IN (
        'TERMINATED', 'WITHDRAWN', 'SUSPENDED'
    ) THEN 1 ELSE 0 END AS is_stopped,
    -- SGLT2 coverage: the class acronym plus every approved agent name, so
    -- trials naming only canagliflozin / ertugliflozin / sotagliflozin count.
    CASE WHEN LOWER(conditions) LIKE '%sglt2%' OR LOWER(interventions) LIKE '%sglt2%'
         OR LOWER(conditions) LIKE '%gliflozin%' OR LOWER(interventions) LIKE '%gliflozin%'
         OR LOWER(interventions) LIKE '%dapagliflozin%' OR LOWER(interventions) LIKE '%empagliflozin%'
         OR LOWER(interventions) LIKE '%canagliflozin%' OR LOWER(interventions) LIKE '%ertugliflozin%'
         OR LOWER(interventions) LIKE '%sotagliflozin%'
    THEN 1 ELSE 0 END AS is_sglt2
FROM stg_studies;

CREATE OR REPLACE VIEW v_trials_by_year AS
SELECT start_year, COUNT(*) AS n_trials
FROM v_trials
WHERE start_year IS NOT NULL
GROUP BY start_year
ORDER BY start_year;

CREATE OR REPLACE VIEW v_phase_distribution AS
SELECT COALESCE(phase_category, 'UNKNOWN') AS phase_category, COUNT(*) AS n_trials
FROM v_trials
GROUP BY phase_category
ORDER BY n_trials DESC;

CREATE OR REPLACE VIEW v_completion_by_sponsor AS
SELECT
    COALESCE(sponsor_class, 'UNKNOWN') AS sponsor_class,
    COUNT(*) AS n_trials,
    SUM(is_completed) AS n_completed,
    ROUND(SUM(is_completed) * 1.0 / COUNT(*), 4) AS completion_rate,
    SUM(is_stopped) AS n_stopped,
    ROUND(SUM(is_stopped) * 1.0 / COUNT(*), 4) AS stopped_rate
FROM v_trials
GROUP BY 1
ORDER BY n_trials DESC;

CREATE OR REPLACE VIEW v_enrollment_by_phase AS
SELECT
    COALESCE(phase_category, 'UNKNOWN') AS phase_category,
    COUNT(enrollment_count) AS n_with_enrollment,
    ROUND(MEDIAN(enrollment_count), 1) AS median_enrollment,
    ROUND(quantile_cont(enrollment_count, 0.25), 1) AS p25_enrollment,
    ROUND(quantile_cont(enrollment_count, 0.75), 1) AS p75_enrollment
FROM v_trials
WHERE enrollment_count IS NOT NULL
GROUP BY 1
ORDER BY n_with_enrollment DESC;

CREATE OR REPLACE VIEW v_top_conditions AS
SELECT conditions, COUNT(*) AS n_trials
FROM v_trials
WHERE conditions IS NOT NULL
GROUP BY conditions
ORDER BY n_trials DESC;

CREATE OR REPLACE VIEW v_sglt2_trend AS
SELECT
    start_year,
    CAST(SUM(is_sglt2) AS BIGINT) AS n_sglt2,
    CAST(COUNT(*) - SUM(is_sglt2) AS BIGINT) AS n_other
FROM v_trials
WHERE start_year IS NOT NULL
GROUP BY start_year
ORDER BY start_year;