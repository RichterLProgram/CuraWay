from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.config.databricks import databricks_config

logger = logging.getLogger(__name__)


class DatabricksRAGAdapter:
    """
    Adapter for Databricks RAG integration.
    Provides stubs when not configured; implements real logic when credentials present.
    """

    def __init__(self) -> None:
        self.config = databricks_config
        if not self.config.is_configured:
            logger.warning(
                "DatabricksRAGAdapter initialized without credentials - using stubs"
            )

    def query_warehouse(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL query against Databricks SQL Warehouse."""
        if not self.config.is_configured:
            raise NotImplementedError(
                "Databricks not configured. Set environment variables: "
                "DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_SQL_WAREHOUSE_ID"
            )

        from databricks import sql as dbsql

        connection = dbsql.connect(
            server_hostname=self.config.host,
            http_path=self.config.http_path
            or f"/sql/1.0/warehouses/{self.config.warehouse_id}",
            access_token=self.config.token,
        )
        cursor = connection.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        connection.close()

        return [dict(row.asDict()) for row in results]

    def list_vector_indexes(self) -> List[str]:
        """List available Databricks vector indexes."""
        if not self.config.is_configured:
            logger.info("Databricks not configured - returning empty list")
            return []
        raise NotImplementedError("Implement using Databricks API")
