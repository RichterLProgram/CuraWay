from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parents[0]
PERSIST_DIR = BACKEND_ROOT / "output" / "rag_store"
TABLE_NAME = "rag_documents"


def _rag_disabled() -> bool:
    return os.getenv("RAG_DISABLED", "false").lower() == "true"


def _source_paths() -> List[Path]:
    sources: List[Path] = []
    data_dir = BACKEND_ROOT / "output" / "data"
    prompts_dir = BACKEND_ROOT / "prompts_and_pydantic_models"
    readme = PROJECT_ROOT / "README.md"

    if data_dir.exists():
        sources.extend(data_dir.rglob("*.json"))
    if prompts_dir.exists():
        sources.extend(prompts_dir.rglob("*.py"))
    if readme.exists():
        sources.append(readme)
    return [path for path in sources if path.is_file()]


def _load_documents() -> List[Document]:
    documents: List[Document] = []
    for path in _source_paths():
        suffix = path.suffix.lower()
        try:
            if suffix == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                content = json.dumps(payload, ensure_ascii=False, indent=2)
            else:
                content = path.read_text(encoding="utf-8")
        except Exception:
            continue

        if not content.strip():
            continue

        documents.append(
            Document(
                page_content=content,
                metadata={"source": str(path.relative_to(PROJECT_ROOT))},
            )
        )
    return documents


def _split_documents(documents: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=120)
    return splitter.split_documents(documents)


def _load_lancedb():
    try:
        import lancedb  # type: ignore
        from langchain_community.vectorstores import LanceDB  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "LanceDB is not installed. Install with: python -m pip install lancedb"
        ) from exc
    return lancedb, LanceDB


def build_vector_store():
    if _rag_disabled():
        raise RuntimeError("RAG is disabled via RAG_DISABLED=true")

    documents = _load_documents()
    if not documents:
        raise RuntimeError("No documents found for RAG indexing.")

    chunks = _split_documents(documents)
    embeddings = OpenAIEmbeddings()
    lancedb, LanceDB = _load_lancedb()
    db = lancedb.connect(str(PERSIST_DIR))
    return LanceDB.from_documents(
        documents=chunks,
        embedding=embeddings,
        connection=db,
        table_name=TABLE_NAME,
    )


def load_vector_store():
    embeddings = OpenAIEmbeddings()
    lancedb, LanceDB = _load_lancedb()
    db = lancedb.connect(str(PERSIST_DIR))
    return LanceDB(connection=db, table_name=TABLE_NAME, embedding=embeddings)


def get_vector_store():
    if PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir()):
        return load_vector_store()
    return build_vector_store()


def retrieve_documents(query: str, top_k: int = 4) -> List[Tuple[Document, float]]:
    store = get_vector_store()
    return store.similarity_search_with_relevance_scores(query, k=top_k)
