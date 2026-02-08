from __future__ import annotations

import os
import sys
import traceback


def _bootstrap_path() -> None:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)


def main() -> int:
    _bootstrap_path()
    os.environ.setdefault("LLM_DISABLED", "true")
    try:
        from src.analytics.desert_metrics import build_desert_metric_seeds
        from src.geo.haversine import haversine_km
        from src.ontology.normalize import normalize_capability_name

        normalize_capability_name("ct scan")
        _ = haversine_km(0, 0, 1, 1)
        seeds = build_desert_metric_seeds(
            facilities=[
                {
                    "facility_id": "fac-1",
                    "name": "Facility",
                    "location": {"lat": 0, "lon": 0, "region": "Region"},
                    "capabilities": [
                        {
                            "name": "IMAGING_CT",
                            "capability_code": "IMAGING_CT",
                            "evidence": {
                                "source_row_id": 1,
                                "source_column_name": "capability",
                                "snippet": "CT available",
                            },
                        }
                    ],
                    "canonical_capabilities": ["IMAGING_CT"],
                }
            ],
            capability_target="IMAGING_CT",
        )
        if not seeds:
            raise RuntimeError("Desert metric seeds not generated.")
    except Exception:
        traceback.print_exc()
        return 1
    print("health_check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
