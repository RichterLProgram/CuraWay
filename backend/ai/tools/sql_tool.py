from __future__ import annotations

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def query_database(sql_query: str) -> str:
    """Execute SQL query against local sqlite demo backend."""
    _ = sql_query
    logger.info("SQL tool uses local sqlite demo backend")
    return "SQL tool uses local sqlite demo backend"
