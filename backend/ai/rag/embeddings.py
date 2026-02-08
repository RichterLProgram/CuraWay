from __future__ import annotations

import logging
from typing import List

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Local embedding generation using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        logger.info("Loading embedding model: %s", model_name)
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        return self.model.encode([query], convert_to_numpy=True)[0].tolist()
