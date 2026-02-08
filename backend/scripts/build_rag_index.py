from __future__ import annotations

import os

from agent_api.rag import build_vector_store


def main() -> None:
    if os.getenv("DATABRICKS_VECTOR_SEARCH_ENDPOINT") and os.getenv(
        "DATABRICKS_VECTOR_SEARCH_INDEX"
    ):
        print(
            "Databricks Vector Search is configured. "
            "Indexing is managed in Databricks; skipping local build."
        )
        return
    store = build_vector_store()
    print(f"RAG index built at {store._persist_directory}")  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
