# Data dictionary

Warehouse table: `stg_studies` (one row per NCT id; upserted on every run).

| Column | Type | Source | Notes |
| --- | --- | --- | --- |
| nct_id | VARCHAR (PK) | identificationModule.nctId | dedupe key |
| title | VARCHAR | identificationModule.briefTitle | |
| status | VARCHAR | statusModule.overallStatus | enum validated |
| phases | VARCHAR | designModule.phases | original list joined with "; " |
| phase_category | VARCHAR | derived | single phase or COMBINED |
| enrollment_count | BIGINT | designModule.enrollmentInfo.count | nullable |
| enrollment_type | VARCHAR | designModule.enrollmentInfo.type | ACTUAL / ESTIMATED |
| conditions | VARCHAR | conditionsModule.conditions | joined |
| interventions | VARCHAR | armsInterventionsModule.interventions[].name | joined |
| intervention_types | VARCHAR | armsInterventionsModule.interventions[].type | joined |
| sponsor_name | VARCHAR | sponsorCollaboratorsModule.leadSponsor.name | |
| sponsor_class | VARCHAR | sponsorCollaboratorsModule.leadSponsor.class | INDUSTRY / ACADEMIC / NIH / ... |
| start_date | VARCHAR | statusModule.startDateStruct.date | ISO normalized |
| primary_completion_date | VARCHAR | statusModule.primaryCompletionDateStruct.date | ISO normalized |
| completion_date | VARCHAR | statusModule.completionDateStruct.date | ISO normalized |
| allocation | VARCHAR | designInfo.allocation | |
| intervention_model | VARCHAR | designInfo.interventionModel | |
| masking | VARCHAR | designInfo.maskingInfo.masking | |
| primary_purpose | VARCHAR | designInfo.primaryPurpose | |
| n_primary_outcomes | INTEGER | outcomesModule.primaryOutcomes | count |
| primary_outcome_first | VARCHAR | outcomesModule.primaryOutcomes[0].measure | |
| has_results | BOOLEAN | study.hasResults | |

Marts (views): `v_trials` adds `start_year`, `is_completed`, `is_stopped`, `is_sglt2`;
`v_trials_by_year`, `v_phase_distribution`, `v_completion_by_sponsor`,
`v_enrollment_by_phase`, `v_top_conditions`, `v_sglt2_trend` are metric views.