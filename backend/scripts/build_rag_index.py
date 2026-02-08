from __future__ import annotations

from agent_api.rag import build_vector_store


def main() -> None:
    store = build_vector_store()
    print(f"RAG index built at {store._persist_directory}")  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
