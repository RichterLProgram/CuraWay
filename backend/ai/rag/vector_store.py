from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import lancedb

logger = logging.getLogger(__name__)


class VectorStore:
    """LanceDB-based vector storage with persistence."""

    def __init__(self, db_path: str = "./backend/data/vectors") -> None:
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(self.db_path))
        logger.info("Vector store initialized at %s", self.db_path)

    def create_table(self, table_name: str, schema: Dict) -> None:
        """Create or get a table (LanceDB creates on first insert)."""
        _ = (table_name, schema)

    def add_documents(self, table_name: str, documents: List[Dict]) -> int:
        """Add documents with embeddings to the table."""
        try:
            self.db.create_table(table_name, data=documents, mode="overwrite")
            logger.info("Added %s documents to %s", len(documents), table_name)
            return len(documents)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to add documents: %s", exc)
            raise

    def search(
        self, table_name: str, query_vector: List[float], top_k: int = 5
    ) -> List[Dict]:
        """Search for similar documents."""
        try:
            table = self.db.open_table(table_name)
            return table.search(query_vector).limit(top_k).to_list()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Search failed: %s", exc)
            return []

    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        return self.db.table_names()
