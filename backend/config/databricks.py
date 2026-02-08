from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class DatabricksConfig:
    """Configuration for Databricks connectivity."""

    def __init__(self) -> None:
        self.host = os.getenv("DATABRICKS_HOST")
        self.token = os.getenv("DATABRICKS_TOKEN")
        self.warehouse_id = os.getenv("DATABRICKS_SQL_WAREHOUSE_ID")
        self.http_path = os.getenv("DATABRICKS_HTTP_PATH")
        self._validate()

    def _validate(self) -> None:
        if not all([self.host, self.token, self.warehouse_id or self.http_path]):
            logger.warning(
                "Databricks not fully configured. Set DATABRICKS_HOST, "
                "DATABRICKS_TOKEN, and DATABRICKS_SQL_WAREHOUSE_ID or DATABRICKS_HTTP_PATH"
            )

    @property
    def is_configured(self) -> bool:
        return all([self.host, self.token, self.warehouse_id or self.http_path])


databricks_config = DatabricksConfig()
