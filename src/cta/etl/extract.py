"""Flatten ClinicalTrials.gov v2 study JSON into warehouse rows."""

from __future__ import annotations

import re
from typing import Any

DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?")

# Warehouse column order shared by extract, DDL and the loader.
STUDY_COLUMNS: list[tuple[str, str]] = [
    ("nct_id", "VARCHAR PRIMARY KEY"),
    ("title", "VARCHAR"),
    ("status", "VARCHAR"),
    ("phases", "VARCHAR"),
    ("phase_category", "VARCHAR"),
    ("enrollment_count", "BIGINT"),
    ("enrollment_type", "VARCHAR"),
    ("conditions", "VARCHAR"),
    ("interventions", "VARCHAR"),
    ("intervention_types", "VARCHAR"),
    ("sponsor_name", "VARCHAR"),
    ("sponsor_class", "VARCHAR"),
    ("start_date", "VARCHAR"),
    ("primary_completion_date", "VARCHAR"),
    ("completion_date", "VARCHAR"),
    ("allocation", "VARCHAR"),
    ("intervention_model", "VARCHAR"),
    ("masking", "VARCHAR"),
    ("primary_purpose", "VARCHAR"),
    ("n_primary_outcomes", "INTEGER"),
    ("primary_outcome_first", "VARCHAR"),
    ("has_results", "BOOLEAN"),
]


def parse_date(value: Any) -> str | None:
    """Normalize a CT.gov date (YYYY, YYYY-MM, YYYY-MM-DD) to ISO strings."""
    if not value:
        return None
    match = DATE_RE.match(str(value).strip())
    if not match:
        return None
    year, month, day = match.groups()
    if month and day:
        return f"{year}-{month}-{day}"
    if month:
        return f"{year}-{month}-01"
    return f"{year}-01-01"


def join_list(values: Any, sep: str = "; ") -> str | None:
    if not values:
        return None
    if isinstance(values, str):
        return values
    parts = [str(v).strip() for v in values if str(v).strip()]
    return sep.join(parts) if parts else None


def study_to_row(study: dict[str, Any]) -> dict[str, Any]:
    """Convert one API study object into a flat row keyed by STUDY_COLUMNS."""
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    status = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    sponsor = protocol.get("sponsorCollaboratorsModule") or {}
    conditions = protocol.get("conditionsModule") or {}
    interventions = protocol.get("armsInterventionsModule") or {}
    outcomes = protocol.get("outcomesModule") or {}
    enrollment = design.get("enrollmentInfo") or {}
    design_info = design.get("designInfo") or {}
    masking_info = design_info.get("maskingInfo") or {}
    lead_sponsor = sponsor.get("leadSponsor") or {}

    phases = design.get("phases") or []
    phase_list = [str(p).strip() for p in phases if str(p).strip()]
    phase_category = "COMBINED" if len(phase_list) > 1 else (phase_list[0] if phase_list else None)

    intervention_names = [
        str(item.get("name")).strip() for item in (interventions.get("interventions") or [])
        if item.get("name")
    ]
    intervention_types = [
        str(item.get("type")).strip() for item in (interventions.get("interventions") or [])
        if item.get("type")
    ]
    primary_outcomes = outcomes.get("primaryOutcomes") or []
    primary_measures = [str(o.get("measure")).strip() for o in primary_outcomes if o.get("measure")]

    return {
        "nct_id": identification.get("nctId"),
        "title": identification.get("briefTitle"),
        "status": status.get("overallStatus"),
        "phases": join_list(phase_list),
        "phase_category": phase_category,
        "enrollment_count": enrollment.get("count"),
        "enrollment_type": enrollment.get("type"),
        "conditions": join_list(conditions.get("conditions")),
        "interventions": join_list(intervention_names),
        "intervention_types": join_list(intervention_types),
        "sponsor_name": lead_sponsor.get("name"),
        "sponsor_class": lead_sponsor.get("class"),
        "start_date": parse_date((status.get("startDateStruct") or {}).get("date")),
        "primary_completion_date": parse_date((status.get("primaryCompletionDateStruct") or {}).get("date")),
        "completion_date": parse_date((status.get("completionDateStruct") or {}).get("date")),
        "allocation": design_info.get("allocation"),
        "intervention_model": design_info.get("interventionModel"),
        "masking": masking_info.get("masking"),
        "primary_purpose": design_info.get("primaryPurpose"),
        "n_primary_outcomes": len(primary_measures) or None,
        "primary_outcome_first": primary_measures[0] if primary_measures else None,
        "has_results": study.get("hasResults"),
    }


def extract_rows(studies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten a page of studies into rows."""
    rows: list[dict[str, Any]] = []
    for study in studies:
        try:
            row = study_to_row(study)
        except Exception:  # noqa: BLE001 - a malformed study must not drop the page
            continue
        if row.get("nct_id"):
            rows.append(row)
    return rows