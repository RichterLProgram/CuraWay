"""BioClinicalBERT Embeddings (optional)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"


@dataclass
class EmbeddingModel:
    tokenizer: object
    model: object
    device: str


_MODEL_CACHE: Optional[EmbeddingModel] = None


def _load_model() -> EmbeddingModel:
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Transformers/Torch not installed") from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME)
    model.to(device)
    model.eval()
    _MODEL_CACHE = EmbeddingModel(tokenizer=tokenizer, model=model, device=device)
    return _MODEL_CACHE


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = _load_model()

    import torch

    with torch.no_grad():
        inputs = model.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        outputs = model.model(**inputs)
        hidden = outputs.last_hidden_state
        mask = inputs["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
        masked = hidden * mask
        summed = masked.sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1.0)
        pooled = summed / counts
        return pooled.cpu().tolist()


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
