from __future__ import annotations

from collections import defaultdict
from typing import List

from src.shared.models import DemandRequirements, FacilityCapabilities, MedicalDesert
from src.shared.utils import infer_location


def detect_deserts(
    demand_points: List[DemandRequirements],
    facilities: List[FacilityCapabilities],
) -> List[MedicalDesert]:
    """
    Group by region and compare demand vs supply.

    High demand + low supply yields a high gap score.
    """
    demand_by_region: dict[str, list[DemandRequirements]] = defaultdict(list)
    supply_by_region: dict[str, list[FacilityCapabilities]] = defaultdict(list)

    for demand in demand_points:
        _, _, region = infer_location(demand.profile.location)
        demand_by_region[region].append(demand)

    for facility in facilities:
        supply_by_region[facility.location.region].append(facility)

    deserts: List[MedicalDesert] = []
    all_regions = set(demand_by_region.keys()) | set(supply_by_region.keys())

    for region in sorted(all_regions):
        demand_list = demand_by_region.get(region, [])
        supply_list = supply_by_region.get(region, [])
        demand_count = len(demand_list)
        supply_count = len(supply_list)

        if demand_count == 0:
            continue

        available_capabilities = {
            _entry_name(cap)
            for facility in supply_list
            for cap in facility.capabilities
        }
        required_capabilities = {
            cap for demand in demand_list for cap in demand.required_capabilities
        }
        missing_capabilities = sorted(required_capabilities - available_capabilities)

        raw_gap = demand_count / (supply_count + 1)
        gap_score = min(raw_gap / 5, 1.0)

        lat, lng, _ = infer_location(region)
        deserts.append(
            MedicalDesert(
                region_name=region,
                lat=lat,
                lng=lng,
                demand_count=demand_count,
                supply_count=supply_count,
                gap_score=gap_score,
                missing_capabilities=missing_capabilities,
            )
        )

    return deserts


def _entry_name(entry: object) -> str:
    if isinstance(entry, dict):
        return str(entry.get("name") or entry.get("capability_code") or "")
    if hasattr(entry, "name"):
        return str(getattr(entry, "name"))
    return str(entry)
