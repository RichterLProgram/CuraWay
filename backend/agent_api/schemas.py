from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class AgentRunRequest(BaseModel):
    query: str = Field(..., min_length=1)
    provider: Literal["openai", "anthropic"] = "openai"
    model: Optional[str] = None
    top_k: int = Field(4, ge=1, le=20)
    enable_rag: bool = True
    system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    source: str
    content: str
    score: Optional[float] = None


class AgentRunResponse(BaseModel):
    trace_id: str
    provider: str
    model: str
    answer: str
    citations: List[Citation]
    rag_used: bool
    elapsed_ms: int


class Text2SqlRequest(BaseModel):
    question: str = Field(..., min_length=1)
    schema: str = Field(..., min_length=1)
    provider: Literal["openai", "anthropic"] = "openai"
    model: Optional[str] = None
    system_prompt: Optional[str] = None


class Text2SqlResponse(BaseModel):
    trace_id: str
    provider: str
    model: str
    sql: str
    elapsed_ms: int
