from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)
_logged = False


def _resolve_app_data_dir() -> tuple[Path, bool]:
    env_value = os.getenv("APP_DATA_DIR", "").strip()
    if env_value:
        return Path(env_value), True
    return Path("/tmp/cancercompass"), False


def _log_paths_once(app_data_dir: Path, env_set: bool) -> None:
    global _logged
    if _logged:
        return
    _logged = True
    logger.info(
        "Runtime paths: base=%s app_data_dir_set=%s",
        app_data_dir,
        "true" if env_set else "false",
    )
    logger.info("Runtime paths: vectorstore=%s", app_data_dir / "vectorstore")
    logger.info("Runtime paths: mlruns=%s", app_data_dir / "mlruns")


def get_app_data_dir() -> Path:
    app_data_dir, env_set = _resolve_app_data_dir()
    app_data_dir.mkdir(parents=True, exist_ok=True)
    _log_paths_once(app_data_dir, env_set)
    return app_data_dir


def get_vectorstore_dir() -> Path:
    vector_dir = get_app_data_dir() / "vectorstore"
    vector_dir.mkdir(parents=True, exist_ok=True)
    return vector_dir


def get_mlflow_dir() -> Path:
    mlflow_dir = get_app_data_dir() / "mlruns"
    mlflow_dir.mkdir(parents=True, exist_ok=True)
    return mlflow_dir


def get_mlflow_tracking_uri() -> str:
    mlflow_dir = get_mlflow_dir().resolve()
    return f"file:{mlflow_dir.as_posix()}"
