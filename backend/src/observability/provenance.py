from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROVENANCE_DIR = BACKEND_ROOT / "output" / "provenance"


def write_provenance(payload: Dict[str, Any]) -> str:
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
    provenance_id = str(uuid.uuid4())
    payload = dict(payload)
    payload["provenance_id"] = provenance_id
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    path = PROVENANCE_DIR / f"{provenance_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return provenance_id


def read_provenance(provenance_id: str) -> Optional[Dict[str, Any]]:
    path = PROVENANCE_DIR / f"{provenance_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
