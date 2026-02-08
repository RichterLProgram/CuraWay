from __future__ import annotations

import re
from typing import Dict, List, Optional


class TextChunker:
    """Simple text chunking with overlap."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Split text into overlapping chunks with metadata."""
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        chunks: List[Dict] = []
        current_chunk: List[str] = []
        current_length = 0

        for sentence in sentences:
            if not sentence:
                continue
            sentence_length = len(sentence)
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": metadata or {},
                        "char_count": len(chunk_text),
                    }
                )
                overlap_sentences = current_chunk[-2:] if len(current_chunk) > 1 else []
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": metadata or {},
                    "char_count": len(chunk_text),
                }
            )

        return chunks
