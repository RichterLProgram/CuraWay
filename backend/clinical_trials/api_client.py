"""ClinicalTrials.gov API Zugriff."""

import json
import urllib.parse
import urllib.request
from typing import List

from clinical_trials.models import TrialLocation, TrialRecord

API_URL = "https://clinicaltrials.gov/api/v2/studies"


def fetch_trials(query: str, page_size: int = 50) -> List[TrialRecord]:
    params = {
        "format": "json",
        "query.term": query,
        "pageSize": str(page_size),
        "fields": ",".join(
            [
                "protocolSection.identificationModule.nctId",
                "protocolSection.identificationModule.briefTitle",
                "protocolSection.conditionsModule.conditions",
                "protocolSection.statusModule.overallStatus",
                "protocolSection.designModule.phases",
                "protocolSection.eligibilityModule.eligibilityCriteria",
                "protocolSection.armsInterventionsModule.interventions",
                "protocolSection.contactsLocationsModule.locations",
            ]
        ),
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    studies = payload.get("studies", [])
    records: List[TrialRecord] = []
    for study in studies:
        if _is_excluded_status(study):
            continue
        record = _normalize_trial(study)
        if record:
            records.append(record)
    return records


def _normalize_trial(study: dict) -> TrialRecord | None:
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    nct_id = identification.get("nctId")
    title = identification.get("briefTitle")
    if not nct_id or not title:
        return None

    conditions_module = protocol.get("conditionsModule", {})
    status_module = protocol.get("statusModule", {})
    design_module = protocol.get("designModule", {})
    eligibility_module = protocol.get("eligibilityModule", {})
    arms_module = protocol.get("armsInterventionsModule", {})
    locations_module = protocol.get("contactsLocationsModule", {})

    interventions = []
    for item in arms_module.get("interventions", []) or []:
        name = item.get("name")
        if name:
            interventions.append(name)

    locations = []
    for loc in locations_module.get("locations", []) or []:
        locations.append(
            TrialLocation(
                name=loc.get("facility"),
                city=loc.get("city"),
                country=loc.get("country"),
                latitude=_safe_float(loc.get("geoPoint", {}).get("lat")),
                longitude=_safe_float(loc.get("geoPoint", {}).get("lon")),
            )
        )

    phases = design_module.get("phases", [])
    phase = phases[0] if phases else None

    return TrialRecord(
        nct_id=nct_id,
        title=title,
        phase=phase,
        status=status_module.get("overallStatus"),
        conditions=conditions_module.get("conditions") or [],
        interventions=interventions,
        eligibility_criteria=eligibility_module.get("eligibilityCriteria"),
        locations=locations,
    )


def _safe_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_excluded_status(study: dict) -> bool:
    protocol = study.get("protocolSection", {})
    status_module = protocol.get("statusModule", {})
    status = status_module.get("overallStatus")
    if not status:
        return False
    return status.strip().lower() in {
        "completed",
        "terminated",
        "withdrawn",
        "suspended",
        "unknown status",
        "no longer available",
    }
