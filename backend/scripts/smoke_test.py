from __future__ import annotations

import importlib
import os
import sys
import traceback


def _bootstrap_path() -> None:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    repo_root = os.path.dirname(base_dir)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _try_import(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        print(f"OK: imported {module_name}")
        return True
    except Exception:  # pragma: no cover - smoke test output
        print(f"ERROR: failed to import {module_name}")
        traceback.print_exc()
        return False


def main() -> int:
    _bootstrap_path()
    os.environ.setdefault("LLM_DISABLED", "true")

    if not _try_import("backend.api.server"):
        return 1

    try:
        from backend.api.server import app  # noqa: F401

        print("OK: FastAPI app loaded")
    except Exception:  # pragma: no cover - smoke test output
        print("ERROR: failed to access FastAPI app")
        traceback.print_exc()
        return 1

    orchestrator_spec = importlib.util.find_spec("backend.ai.orchestrator")
    if orchestrator_spec is None:
        print("SKIP: orchestrator not present")
    else:
        if not _try_import("backend.ai.orchestrator"):
            return 1

    print("smoke_test: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
