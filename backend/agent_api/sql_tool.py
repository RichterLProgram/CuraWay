from __future__ import annotations

import logging
import sqlite3
from typing import Any, Iterable, List, Tuple

logger = logging.getLogger(__name__)


def run_sql(sql: str, parameters: Iterable[Any] | None = None) -> List[Tuple]:
    logger.info("SQL mode uses local sqlite demo backend")
    with sqlite3.connect(":memory:") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, parameters or [])
            return cursor.fetchall()
        except sqlite3.Error:
            return [("SQL mode uses local sqlite demo backend",)]
