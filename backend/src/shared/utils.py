from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


CITY_COORDINATES = {
    "accra": (5.6037, -0.1870, "Greater Accra"),
    "kumasi": (6.6885, -1.6244, "Ashanti"),
    "tamale": (9.4008, -0.8393, "Northern"),
    "takoradi": (4.9036, -1.7486, "Western"),
    "tema": (5.6698, -0.0166, "Greater Accra"),
    "akatsi": (5.5786, 0.0865, "Volta"),
    "cape coast": (5.1054, -1.2466, "Central"),
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def extract_with_regex(pattern: str, text: str, group: int = 1) -> Optional[str]:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(group).strip()


def extract_all_with_regex(pattern: str, text: str, group: int = 1) -> List[str]:
    return [m.group(group).strip() for m in re.finditer(pattern, text, flags=re.IGNORECASE)]


def infer_location(location_text: str) -> Tuple[float, float, str]:
    location_text = location_text.lower()
    for city, (lat, lng, region) in CITY_COORDINATES.items():
        if city in location_text:
            return lat, lng, region
    return 7.9465, -1.0232, "Unknown"


def compute_urgency_score(stage: Optional[str], comorbidities: List[str]) -> int:
    stage_score = 0
    if stage:
        stage_map = {"i": 2, "ii": 4, "iii": 7, "iv": 9}
        stage_key = stage.strip().lower().replace("stage", "").strip()
        stage_score = stage_map.get(stage_key, 5)
    comorbidity_score = min(len(comorbidities) * 1, 3)
    return min(stage_score + comorbidity_score, 10)


def compute_coverage_score(
    capabilities: List, equipment: List, specialists: List
) -> float:
    cap_values = [_entry_name(item) for item in capabilities]
    equip_values = [_entry_name(item) for item in equipment]
    spec_values = [_entry_name(item) for item in specialists]
    base = len(set(cap_values)) * 8 + len(set(equip_values)) * 4 + len(set(spec_values)) * 3
    return float(min(base, 100))


def _entry_name(item: object) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or "")
    if hasattr(item, "name"):
        return str(getattr(item, "name"))
    return str(item)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_text_files(folder: str) -> List[Tuple[str, str]]:
    paths = sorted(Path(folder).glob("*.txt"))
    results: List[Tuple[str, str]] = []
    for path in paths:
        results.append((path.name, path.read_text(encoding="utf-8")))
    return results


def write_json(path: str, payload: Iterable) -> None:
    ensure_dir(str(Path(path).parent))
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
