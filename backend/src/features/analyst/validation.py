"""Validation helpers for Analyst flow (cross-source + review)."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from features.ai.med_bert import cosine_similarity, embed_texts
from features.validation.anomaly_validator import is_negated
from io_utils import load_documents


@dataclass
class RAGChunk:
    text: str
    document_id: str
    chunk_id: str
    source: str


@dataclass
class RAGHit:
    score: float
    chunk: RAGChunk


class RAGIndex:
    def __init__(self, chunks: List[RAGChunk]) -> None:
        self.chunks = chunks
        self._mode = "token"
        self._token_idf: Dict[str, float] = {}
        self._token_vectors: List[Dict[str, float]] = []
        self._embeddings: List[List[float]] = []

    @classmethod
    def from_documents(
        cls,
        documents: Iterable[str],
        source: str,
        chunk_size: int = 1200,
        chunk_overlap: int = 120,
    ) -> "RAGIndex":
        chunks: List[RAGChunk] = []
        for doc in documents:
            document_id = _extract_document_id(doc)
            for idx, chunk in enumerate(_chunk_text(doc, chunk_size, chunk_overlap), start=1):
                chunks.append(
                    RAGChunk(
                        text=chunk,
                        document_id=document_id,
                        chunk_id=f"chunk-{idx:03d}",
                        source=source,
                    )
                )
        index = cls(chunks)
        index._build_vectors()
        return index

    def query(self, text: str, top_k: int = 5) -> List[RAGHit]:
        if not self.chunks:
            return []
        if self._mode == "bert":
            return self._query_bert(text, top_k)
        return self._query_token(text, top_k)

    def _build_vectors(self) -> None:
        if not self.chunks:
            return
        try:
            self._embeddings = embed_texts([c.text for c in self.chunks])
            if self._embeddings:
                self._mode = "bert"
                return
        except Exception:
            pass
        self._mode = "token"
        self._build_token_vectors()

    def _build_token_vectors(self) -> None:
        df: Dict[str, int] = {}
        tokenized = []
        for chunk in self.chunks:
            tokens = _tokenize(chunk.text)
            tokenized.append(tokens)
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1

        total = len(self.chunks)
        self._token_idf = {
            token: math.log((1 + total) / (1 + count)) + 1.0 for token, count in df.items()
        }
        self._token_vectors = []
        for tokens in tokenized:
            tf: Dict[str, float] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0.0) + 1.0
            vec = {t: (tf[t] / len(tokens)) * self._token_idf.get(t, 0.0) for t in tf}
            self._token_vectors.append(vec)

    def _query_bert(self, text: str, top_k: int) -> List[RAGHit]:
        try:
            query_vecs = embed_texts([text])
        except Exception:
            self._mode = "token"
            return self._query_token(text, top_k)
        if not query_vecs:
            return []
        query_vec = query_vecs[0]
        scored = [
            (cosine_similarity(query_vec, vec), idx)
            for idx, vec in enumerate(self._embeddings)
        ]
        return _top_hits(scored, self.chunks, top_k)

    def _query_token(self, text: str, top_k: int) -> List[RAGHit]:
        tokens = _tokenize(text)
        if not tokens:
            return []
        tf: Dict[str, float] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0.0) + 1.0
        query_vec = {t: (tf[t] / len(tokens)) * self._token_idf.get(t, 0.0) for t in tf}
        scored = [
            (_cosine_sparse(query_vec, vec), idx)
            for idx, vec in enumerate(self._token_vectors)
        ]
        return _top_hits(scored, self.chunks, top_k)


def load_external_sources(
    input_dir: Path,
    skip_names: Optional[Set[str]] = None,
) -> List[str]:
    if not input_dir.is_dir():
        return []
    return load_documents(input_dir, skip_names=skip_names)


_CAPABILITY_KEYWORDS = {
    "oncology_services": ["oncology", "cancer", "oncology clinic"],
    "ct_scanner": ["ct", "computed tomography"],
    "mri_scanner": ["mri", "magnetic resonance"],
    "pathology_lab": ["pathology", "laboratory", "lab"],
    "genomic_testing": ["genomic", "genetics", "sequencing"],
    "chemotherapy_delivery": ["chemotherapy", "chemo"],
    "radiotherapy": ["radiotherapy", "radiation therapy"],
    "icu": ["icu", "intensive care"],
    "trial_coordinator": ["trial coordinator", "research coordinator", "clinical trial"],
}


def build_cross_source_report(
    capability_decisions: Dict[str, Dict[str, dict]],
    rag_index: RAGIndex,
    top_k: int = 3,
) -> Dict[str, object]:
    issues: List[dict] = []
    support_count = 0
    conflict_count = 0
    for facility_id, decisions in capability_decisions.items():
        for capability, decision in decisions.items():
            keywords = _CAPABILITY_KEYWORDS.get(capability)
            if not keywords:
                continue
            query = " ".join(keywords)
            hits = rag_index.query(query, top_k=top_k)
            supported = bool(hits)
            decision_value = bool(decision.get("value"))
            issue_type = "ok"
            if decision_value and not supported:
                issue_type = "no_external_support"
                conflict_count += 1
            if not decision_value and supported:
                issue_type = "external_conflict"
                conflict_count += 1
            if supported:
                support_count += 1
            if issue_type != "ok":
                issues.append(
                    {
                        "facility_id": facility_id,
                        "capability": capability,
                        "decision_value": decision_value,
                        "decision_reason": decision.get("decision_reason"),
                        "issue": issue_type,
                        "external_hits": [_hit_to_dict(hit) for hit in hits],
                    }
                )
    return {
        "summary": {
            "facilities": len(capability_decisions),
            "supported_capability_checks": support_count,
            "issues": len(issues),
            "conflicts": conflict_count,
        },
        "issues": issues,
    }


def build_review_queue(
    capability_decisions: Dict[str, Dict[str, dict]],
    confidence_threshold: float = 0.6,
    min_evidence: int = 1,
) -> Dict[str, object]:
    queue: List[dict] = []
    for facility_id, decisions in capability_decisions.items():
        for capability, decision in decisions.items():
            confidence = float(decision.get("confidence", 0.0) or 0.0)
            evidence = decision.get("evidence", []) or []
            reason = decision.get("decision_reason", "insufficient_evidence")
            should_review = (
                confidence < confidence_threshold
                or reason in {"conflicting_evidence", "suspicious_claim"}
                or (decision.get("value") is True and len(evidence) < min_evidence)
            )
            if not should_review:
                continue
            queue.append(
                {
                    "facility_id": facility_id,
                    "capability": capability,
                    "decision_value": bool(decision.get("value")),
                    "decision_reason": reason,
                    "confidence": round(confidence, 3),
                    "evidence_count": len(evidence),
                    "evidence": _trim_evidence(evidence),
                    "review_reason": _review_reason(reason, confidence, evidence),
                    "explanation": explain_decision(decision),
                }
            )
    return {
        "summary": {
            "items": len(queue),
            "confidence_threshold": confidence_threshold,
        },
        "queue": queue,
    }


def explain_decision(decision: Dict[str, object]) -> str:
    reason = decision.get("decision_reason", "insufficient_evidence")
    confidence = float(decision.get("confidence", 0.0) or 0.0)
    evidence = decision.get("evidence", []) or []

    if reason == "direct_evidence":
        return "Direct evidence found with sufficient confidence."
    if reason == "conflicting_evidence":
        if _has_negation_conflict(evidence):
            return "Evidence contains both positive and negated statements."
        return "Evidence conflicts across sources."
    if reason == "suspicious_claim":
        return "Suspicious or marketing-style claim without strong evidence."
    if evidence:
        return f"Evidence exists but confidence ({confidence:.2f}) is below threshold."
    return "No explicit evidence found in the document."


def _has_negation_conflict(evidence: List[object]) -> bool:
    positives = 0
    negatives = 0
    for item in evidence:
        text = item.get("text") if isinstance(item, dict) else str(item)
        if not text:
            continue
        if is_negated(text):
            negatives += 1
        else:
            positives += 1
    return positives > 0 and negatives > 0


def _trim_evidence(items: List[object]) -> List[dict]:
    trimmed: List[dict] = []
    for item in items[:5]:
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            trimmed.append(
                {
                    "text": text[:220] + ("..." if len(text) > 220 else ""),
                    "document_id": item.get("document_id"),
                    "chunk_id": item.get("chunk_id"),
                }
            )
        else:
            text = str(item).strip()
            trimmed.append({"text": text[:220] + ("..." if len(text) > 220 else "")})
    return trimmed


def _review_reason(reason: str, confidence: float, evidence: List[object]) -> str:
    if reason in {"conflicting_evidence", "suspicious_claim"}:
        return reason
    if confidence < 0.6:
        return "low_confidence"
    if len(evidence) < 1:
        return "missing_evidence"
    return "manual_review"


def _top_hits(
    scored: List[Tuple[float, int]], chunks: List[RAGChunk], top_k: int
) -> List[RAGHit]:
    ranked = sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
    hits: List[RAGHit] = []
    for score, idx in ranked:
        if score <= 0:
            continue
        hits.append(RAGHit(score=round(score, 4), chunk=chunks[idx]))
    return hits


def _hit_to_dict(hit: RAGHit) -> dict:
    text = hit.chunk.text.strip().replace("\n", " ")
    snippet = text[:240] + ("..." if len(text) > 240 else "")
    return {
        "score": hit.score,
        "document_id": hit.chunk.document_id,
        "chunk_id": hit.chunk.chunk_id,
        "source": hit.chunk.source,
        "snippet": snippet,
    }


def _cosine_sparse(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in a.keys())
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tokenize(text: str) -> List[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s\-]", " ", text.lower())
    tokens = [t for t in cleaned.split() if len(t) > 2]
    return tokens


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= chunk_size:
            current = f"{current}\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        current = paragraph
    if current:
        chunks.append(current)
    if not chunks:
        return [text[:chunk_size]]
    if chunk_overlap <= 0 or len(chunks) == 1:
        return chunks
    overlapped = []
    for idx, chunk in enumerate(chunks):
        if idx == 0:
            overlapped.append(chunk)
            continue
        prev = chunks[idx - 1]
        overlap = prev[-chunk_overlap:]
        overlapped.append(f"{overlap}\n{chunk}".strip())
    return overlapped


def _extract_document_id(text: str) -> str:
    for line in text.splitlines()[:3]:
        if line.startswith("DOCUMENT_ID:"):
            return line.split("DOCUMENT_ID:", 1)[-1].strip() or "unknown"
    return "unknown"
