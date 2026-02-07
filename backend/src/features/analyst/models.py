"""Analyst view models (map + demand)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from features.models.shared import RegionalAssessment


class DemandPoint(BaseModel):
    point_id: str
    label: str
    latitude: float
    longitude: float
    source: str
    note: Optional[str] = None


class AnalystTrace(BaseModel):
    agent_id: str
    demand_points: int
    desert_regions: int


class AnalystMapData(BaseModel):
    demand_points: List[DemandPoint] = Field(default_factory=list)
    desert_regions: List[RegionalAssessment] = Field(default_factory=list)
    trace: AnalystTrace


class HeatmapRegion(BaseModel):
    region: str
    coverage_score: float
    risk_level: str
    explanation: str


class PlannerRecommendation(BaseModel):
    region: str
    missing_capabilities: List[str]
    summary: str
    priority: str
    actions: List[str]
    impact_notes: Optional[str] = None


class AnalystApiData(BaseModel):
    pins: List[DemandPoint] = Field(default_factory=list)
    heatmap: List[HeatmapRegion] = Field(default_factory=list)
    planner: List[PlannerRecommendation] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
