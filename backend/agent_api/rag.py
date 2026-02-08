from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Tuple

from langchain_core.documents import Document
import lancedb
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import LanceDB
from langchain_databricks import DatabricksVectorSearch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parents[0]
PERSIST_DIR = BACKEND_ROOT / "output" / "rag_store"
TABLE_NAME = "rag_documents"


def _rag_disabled() -> bool:
    return os.getenv("RAG_DISABLED", "false").lower() == "true"


def _databricks_enabled() -> bool:
    return bool(os.getenv("DATABRICKS_VECTOR_SEARCH_ENDPOINT")) and bool(
        os.getenv("DATABRICKS_VECTOR_SEARCH_INDEX")
    )


def _databricks_store() -> DatabricksVectorSearch:
    endpoint = os.getenv("DATABRICKS_VECTOR_SEARCH_ENDPOINT", "")
    index_name = os.getenv("DATABRICKS_VECTOR_SEARCH_INDEX", "")
    if not endpoint or not index_name:
        raise RuntimeError("Databricks Vector Search env vars are not set.")
    return DatabricksVectorSearch(
        endpoint=endpoint,
        index_name=index_name,
    )


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


def build_vector_store() -> LanceDB:
    if _rag_disabled():
        raise RuntimeError("RAG is disabled via RAG_DISABLED=true")

    documents = _load_documents()
    if not documents:
        raise RuntimeError("No documents found for RAG indexing.")

    chunks = _split_documents(documents)
    embeddings = OpenAIEmbeddings()
    db = lancedb.connect(str(PERSIST_DIR))
    return LanceDB.from_documents(
        documents=chunks,
        embedding=embeddings,
        connection=db,
        table_name=TABLE_NAME,
    )


def load_vector_store() -> LanceDB:
    embeddings = OpenAIEmbeddings()
    db = lancedb.connect(str(PERSIST_DIR))
    return LanceDB(connection=db, table_name=TABLE_NAME, embedding=embeddings)


def get_vector_store():
    if _databricks_enabled():
        return _databricks_store()
    if PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir()):
        return load_vector_store()
    return build_vector_store()


def retrieve_documents(query: str, top_k: int = 4) -> List[Tuple[Document, float]]:
    store = get_vector_store()
    return store.similarity_search_with_relevance_scores(query, k=top_k)
