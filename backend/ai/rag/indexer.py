from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from .chunker import TextChunker
from .embeddings import EmbeddingService
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Orchestrates chunking, embedding, and indexing."""

    def __init__(self) -> None:
        self.chunker = TextChunker()
        self.embedder = EmbeddingService()
        self.vector_store = VectorStore()

    def index_file(self, file_path: str, dataset_id: str) -> Dict:
        """Index a file into the vector store."""
        logger.info("Indexing file: %s with ID: %s", file_path, dataset_id)

        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="ignore")

        chunks = self.chunker.chunk_text(
            content, metadata={"dataset_id": dataset_id, "source": str(path)}
        )
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedder.embed(texts)

        documents: List[Dict] = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            documents.append(
                {
                    "id": f"{dataset_id}_chunk_{i}",
                    "text": chunk["text"],
                    "vector": embedding,
                    "dataset_id": dataset_id,
                    "source": str(path),
                    "chunk_index": i,
                    "char_count": chunk["char_count"],
                }
            )

        table_name = f"dataset_{dataset_id}"
        self.vector_store.add_documents(table_name, documents)

        return {
            "indexed_chunks": len(chunks),
            "vector_store_path": str(self.vector_store.db_path),
            "dataset_id": dataset_id,
            "table_name": table_name,
        }

    def query(self, dataset_id: str, query: str, top_k: int = 5) -> List[Dict]:
        """Query the vector store for relevant chunks."""
        query_vector = self.embedder.embed_query(query)
        table_name = f"dataset_{dataset_id}"
        return self.vector_store.search(table_name, query_vector, top_k)
