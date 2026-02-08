from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any, Iterable, List, Tuple

logger = logging.getLogger(__name__)


def _databricks_env_ready() -> bool:
    return all(
        os.getenv(name)
        for name in (
            "DATABRICKS_HOST",
            "DATABRICKS_TOKEN",
            "DATABRICKS_SQL_HTTP_PATH",
        )
    )


def _sqlite_fallback(sql: str, parameters: Iterable[Any] | None = None) -> List[Tuple]:
    logger.warning(
        "Databricks connector not installed/configured, using sqlite fallback"
    )
    with sqlite3.connect(":memory:") as conn:
        cursor = conn.cursor()
        cursor.execute(sql, parameters or [])
        rows = cursor.fetchall()
    return rows


def run_sql(sql: str, parameters: Iterable[Any] | None = None) -> List[Tuple]:
    if not _databricks_env_ready():
        return _sqlite_fallback(sql, parameters)

    try:
        from databricks import sql as databricks_sql  # type: ignore
    except Exception:
        return _sqlite_fallback(sql, parameters)

    try:
        with databricks_sql.connect(
            server_hostname=os.environ["DATABRICKS_HOST"],
            http_path=os.environ["DATABRICKS_SQL_HTTP_PATH"],
            access_token=os.environ["DATABRICKS_TOKEN"],
        ) as connection:
            cursor = connection.cursor()
            cursor.execute(sql, parameters or [])
            rows = cursor.fetchall()
        return rows
    except Exception:
        return _sqlite_fallback(sql, parameters)
