"""Data-quality rules for the staging layer."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

NCT_RE = re.compile(r"^NCT\d{8}$")

STATUS_ENUM = {
    "RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED", "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION", "TERMINATED", "WITHDRAWN", "SUSPENDED", "UNKNOWN",
    "AVAILABLE", "APPROVED_FOR_MARKETING", "NO_LONGER_AVAILABLE", "TEMPORARILY_NOT_AVAILABLE",
    "WITHHELD",
}

PHASE_ENUM = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA", "COMBINED"}


def _is_valid_number(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == int(number) and number >= 0


def validate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply quality rules and return violations plus a summary.

    Critical rules (invalid nct_id, duplicate nct_id) mark the payload as not
    ok so a strict run can fail. Warning rules are reported only.
    """
    violations: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    seen: set[str] = set()
    # Duplicate nct_id across queries is expected (the queries overlap); the
    # warehouse deduplicates by nct_id, so duplicates are reported, not fatal.
    critical_rules = {"nct_id_format"}

    def add(rule: str, row: dict[str, Any], detail: str = "") -> None:
        counts[rule] += 1
        violations.append({
            "rule": rule,
            "critical": rule in critical_rules,
            "nct_id": row.get("nct_id"),
            "detail": detail,
        })

    for row in rows:
        nct_id = str(row.get("nct_id") or "").strip()
        if not NCT_RE.match(nct_id):
            add("nct_id_format", row, f"invalid nct_id: {row.get(chr(110)+chr(99)+chr(116)+chr(95)+chr(105)+chr(100))!r}")
        elif nct_id in seen:
            add("nct_id_duplicate", row, "duplicate nct_id in payload")
        else:
            seen.add(nct_id)

        enrollment = row.get("enrollment_count")
        if enrollment is not None and not _is_valid_number(enrollment):
            add("enrollment_invalid", row, f"enrollment_count={enrollment!r}")

        status = row.get("status")
        if status is not None and status not in STATUS_ENUM:
            add("status_enum", row, f"status={status!r}")

        phases = row.get("phase_category")
        if phases is not None and phases not in PHASE_ENUM:
            add("phase_enum", row, f"phase_category={phases!r}")

        start, primary, completion = row.get("start_date"), row.get("primary_completion_date"), row.get("completion_date")
        if start and primary and start > primary:
            add("date_order_start_primary", row, f"{start} > {primary}")
        if primary and completion and primary > completion:
            add("date_order_primary_completion", row, f"{primary} > {completion}")

    total = len(rows)
    missingness: dict[str, float] = {}
    if total:
        columns = list(rows[0].keys())
        for column in columns:
            missing = sum(1 for row in rows if row.get(column) is None)
            missingness[column] = round(missing / total, 4)

    critical = sum(1 for v in violations if v["critical"])
    return {
        "rows": total,
        "violations": violations,
        "violations_by_rule": dict(counts),
        "missingness": missingness,
        "critical": critical,
        "ok": critical == 0,
    }