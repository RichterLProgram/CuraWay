"""Pytest fixtures for idp_agent tests."""
import sys
from pathlib import Path

# Ensure backend is on path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
