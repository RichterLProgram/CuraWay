from __future__ import annotations

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def query_database(sql_query: str) -> str:
    """Execute SQL query against Databricks warehouse (stub for now)."""
    _ = sql_query
    logger.warning("SQL tool called but Databricks not configured - returning stub")
    return (
        "SQL tool not configured. Set DATABRICKS_HOST, DATABRICKS_TOKEN, "
        "DATABRICKS_SQL_WAREHOUSE_ID to enable."
    )
