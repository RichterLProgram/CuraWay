from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class AgentRunRequest(BaseModel):
    query: str = Field(..., min_length=1)
    provider: Literal["openai"] = "openai"
    model: Optional[str] = None
    top_k: int = Field(4, ge=1, le=20)
    enable_rag: bool = True
    system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    source: str
    content: str
    score: Optional[float] = None


class CouncilOutput(BaseModel):
    role: Literal["planner", "retriever", "verifier", "writer"]
    summary: str
    details: Dict[str, Any]
    confidence: Optional[str] = None


class EvalMetrics(BaseModel):
    faithfulness: float
    completeness: float
    evidence_coverage: float
    citations_count: int
    latency_ms: int
    cost_estimate_usd: float


class AgentRunResponse(BaseModel):
    trace_id: str
    provider: str
    model: str
    answer: str
    citations: List[Citation]
    rag_used: bool
    elapsed_ms: int
    council: List[CouncilOutput]
    risk_flags: List[str]
    compliance_notes: List[str]
    eval_metrics: EvalMetrics
    provenance_id: str


class Text2SqlRequest(BaseModel):
    question: str = Field(..., min_length=1)
    schema: str = Field(..., min_length=1)
    provider: Literal["openai"] = "openai"
    model: Optional[str] = None
    system_prompt: Optional[str] = None


class Text2SqlResponse(BaseModel):
    trace_id: str
    provider: str
    model: str
    sql: str
    elapsed_ms: int


class CausalImpactRequest(BaseModel):
    baseline: List[float]
    post: List[float]
    metric: str = "coverage"


class CausalImpactResponse(BaseModel):
    metric: str
    effect: float
    uplift_pct: float
    confidence_low: float
    confidence_high: float
    confidence: float
    provenance_id: str


class PolicyOptimizeRequest(BaseModel):
    constraints: Dict[str, Any]


class PolicyOptimizeResponse(BaseModel):
    options: List[Dict[str, Any]]
    provenance_id: str


class RoutingRequest(BaseModel):
    origin: Dict[str, float]
    destination: Dict[str, float]


class RoutingResponse(BaseModel):
    minutes: Optional[float]
    distance_km: Optional[float]
    source: str


class RealtimeStatusResponse(BaseModel):
    status: str
    topic: str
    last_ingested_at: Optional[str] = None


class ProvenanceResponse(BaseModel):
    provenance_id: str
    payload: Dict[str, Any]


class ActionGraphRequest(BaseModel):
    actions: List[str]
    dependencies: Optional[List[str]] = None


class ActionGraphNode(BaseModel):
    id: str
    label: str


class ActionGraphEdge(BaseModel):
    from_action: str
    to_action: str
    reason: Optional[str] = None


class ActionGraphResponse(BaseModel):
    nodes: List[ActionGraphNode]
    edges: List[ActionGraphEdge]
    critical_path: List[str]


class ScenarioPreset(BaseModel):
    coverage_delta: int
    underserved_delta: int
    roi_window: str
    demand_impact: List[Dict[str, Any]]
    coverage_shift: List[Dict[str, Any]]
    cost_curve: Dict[str, Any]


class ScenarioRequest(BaseModel):
    action_plan: Dict[str, Any]


class ScenarioResponse(BaseModel):
    simulation_presets: Dict[str, ScenarioPreset]
