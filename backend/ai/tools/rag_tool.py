from __future__ import annotations

import logging
from typing import Dict, List

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def retrieve_context(query: str, dataset_id: str, top_k: int = 5) -> List[Dict]:
    """Retrieve relevant context from the vector store."""
    from backend.ai.rag.indexer import DocumentIndexer

    indexer = DocumentIndexer()
    results = indexer.query(dataset_id, query, top_k)

    logger.info("Retrieved %s chunks for query", len(results))
    return [
        {
            "text": result.get("text", ""),
            "score": result.get("_distance", 0.0),
            "metadata": {
                "dataset_id": result.get("dataset_id"),
                "chunk_index": result.get("chunk_index"),
                "source": result.get("source"),
            },
        }
        for result in results
    ]
