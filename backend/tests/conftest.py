"""Pytest fixtures for backend tests (idp, decision, orchestration, aggregation, models)."""
import sys
from pathlib import Path

# Ensure backend/src is on path
backend_dir = Path(__file__).resolve().parent.parent
src_dir = backend_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
