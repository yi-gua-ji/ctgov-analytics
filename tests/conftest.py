"""Shared fixtures for the ctgov-analytics tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def sample_studies() -> list[dict]:
    return [
        {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000001", "briefTitle": "Empagliflozin in heart failure"},
                "statusModule": {
                    "overallStatus": "COMPLETED",
                    "startDateStruct": {"date": "2020-03-04"},
                    "primaryCompletionDateStruct": {"date": "2022-06"},
                    "completionDateStruct": {"date": "2023-01-01"},
                },
                "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Big Pharma", "class": "INDUSTRY"}},
                "conditionsModule": {"conditions": ["Heart Failure"]},
                "designModule": {
                    "phases": ["PHASE3"],
                    "designInfo": {
                        "allocation": "RANDOMIZED",
                        "interventionModel": "PARALLEL",
                        "maskingInfo": {"masking": "DOUBLE"},
                        "primaryPurpose": "TREATMENT",
                    },
                    "enrollmentInfo": {"count": 1200, "type": "ACTUAL"},
                },
                "armsInterventionsModule": {
                    "interventions": [{"type": "DRUG", "name": "Empagliflozin"}]
                },
                "outcomesModule": {"primaryOutcomes": [{"measure": "CV death or HF hospitalization"}]},
            },
            "hasResults": True,
        },
        {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000002", "briefTitle": "Statins in primary prevention"},
                "statusModule": {
                    "overallStatus": "TERMINATED",
                    "startDateStruct": {"date": "2018"},
                },
                "sponsorCollaboratorsModule": {"leadSponsor": {"name": "University", "class": "ACADEMIC"}},
                "conditionsModule": {"conditions": ["Hypercholesterolemia"]},
                "designModule": {
                    "phases": ["PHASE2", "PHASE3"],
                    "enrollmentInfo": {"count": 300, "type": "ESTIMATED"},
                },
                "armsInterventionsModule": {
                    "interventions": [{"type": "DRUG", "name": "Atorvastatin"}, {"type": "DRUG", "name": "Placebo"}]
                },
            },
        },
    ]