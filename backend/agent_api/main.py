from __future__ import annotations

# Load .env file at startup - MUST BE BEFORE ANY OTHER IMPORTS
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
        # Force reload for child processes
        if os.getenv("OPENAI_API_KEY"):
            print(f"✅ OpenAI API Key loaded successfully")
        else:
            print(f"⚠️  OPENAI_API_KEY not found in {env_path}")
    else:
        print(f"⚠️  .env not found at: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed")
except Exception as e:
    print(f"⚠️  Error loading .env: {e}")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import build_action_graph, run_agent, run_scenario_plan, run_text2sql
from src.analytics.causal_impact import estimate_causal_impact
from src.intelligence.policy_optimizer import optimize_policy
from src.geo.osrm_client import get_travel_time_minutes
from src.observability.provenance import read_provenance, write_provenance
from .schemas import (
    AgentRunRequest,
    AgentRunResponse,
    ActionGraphRequest,
    ActionGraphResponse,
    CausalImpactRequest,
    CausalImpactResponse,
    Citation,
    HealthResponse,
    HotspotReportRequest,
    HotspotReportResponse,
    PolicyOptimizeRequest,
    PolicyOptimizeResponse,
    ProvenanceResponse,
    RealtimeStatusResponse,
    RoutingRequest,
    RoutingResponse,
    ScenarioRequest,
    ScenarioResponse,
    Text2SqlRequest,
    Text2SqlResponse,
)
from pathlib import Path
import json


app = FastAPI(title="CancerCompass Agent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/agent/run", response_model=AgentRunResponse)
def agent_run(payload: AgentRunRequest) -> AgentRunResponse:
    try:
        result = run_agent(
            query=payload.query,
            provider=payload.provider,
            model=payload.model,
            top_k=payload.top_k,
            enable_rag=payload.enable_rag,
            system_prompt=payload.system_prompt,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime error surface
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    citations = [
        Citation(source=source, content=content, score=score)
        for source, content, score in result["citations"]
    ]
    return AgentRunResponse(
        trace_id=result["trace_id"],
        provider=result["provider"],
        model=result["model"],
        answer=result["answer"],
        citations=citations,
        rag_used=result["rag_used"],
        elapsed_ms=result["elapsed_ms"],
        council=result["council"],
        risk_flags=result["risk_flags"],
        compliance_notes=result["compliance_notes"],
        eval_metrics=result["eval_metrics"],
        provenance_id=result["provenance_id"],
    )


@app.post("/agent/text2sql", response_model=Text2SqlResponse)
def agent_text2sql(payload: Text2SqlRequest) -> Text2SqlResponse:
    try:
        result = run_text2sql(
            question=payload.question,
            schema=payload.schema,
            provider=payload.provider,
            model=payload.model,
            system_prompt=payload.system_prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime error surface
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return Text2SqlResponse(
        trace_id=result["trace_id"],
        provider=result["provider"],
        model=result["model"],
        sql=result["sql"],
        elapsed_ms=result["elapsed_ms"],
    )


@app.post("/agent/action_graph", response_model=ActionGraphResponse)
def agent_action_graph(payload: ActionGraphRequest) -> ActionGraphResponse:
    graph = build_action_graph(payload.actions, payload.dependencies)
    return ActionGraphResponse(**graph)


@app.post("/agent/scenario", response_model=ScenarioResponse)
def agent_scenario(payload: ScenarioRequest) -> ScenarioResponse:
    result = run_scenario_plan(payload.action_plan)
    return ScenarioResponse(**result)


@app.post("/agent/causal_impact", response_model=CausalImpactResponse)
def agent_causal_impact(payload: CausalImpactRequest) -> CausalImpactResponse:
    result = estimate_causal_impact(payload.baseline, payload.post)
    provenance_id = write_provenance(
        {"metric": payload.metric, "baseline": payload.baseline, "post": payload.post, "result": result}
    )
    return CausalImpactResponse(metric=payload.metric, provenance_id=provenance_id, **result)


@app.post("/agent/policy_optimize", response_model=PolicyOptimizeResponse)
def agent_policy_optimize(payload: PolicyOptimizeRequest) -> PolicyOptimizeResponse:
    result = optimize_policy({"constraints": payload.constraints})
    provenance_id = write_provenance({"constraints": payload.constraints, "result": result})
    return PolicyOptimizeResponse(options=result["options"], provenance_id=provenance_id)


@app.post("/agent/routing", response_model=RoutingResponse)
def agent_routing(payload: RoutingRequest) -> RoutingResponse:
    result = get_travel_time_minutes(payload.origin, payload.destination)
    return RoutingResponse(**result)


@app.get("/agent/realtime_status", response_model=RealtimeStatusResponse)
def agent_realtime_status() -> RealtimeStatusResponse:
    status_path = Path(__file__).resolve().parents[2] / "output" / "events" / "status.json"
    if status_path.exists():
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        return RealtimeStatusResponse(
            status=payload.get("status", "idle"),
            topic=payload.get("topic", "healthgrid.events"),
            last_ingested_at=payload.get("last_ingested_at"),
        )
    return RealtimeStatusResponse(status="idle", topic="healthgrid.events", last_ingested_at=None)


@app.get("/agent/provenance/{provenance_id}", response_model=ProvenanceResponse)
def agent_provenance(provenance_id: str) -> ProvenanceResponse:
    payload = read_provenance(provenance_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Provenance not found")
    return ProvenanceResponse(provenance_id=provenance_id, payload=payload)


@app.post("/agent/hotspot_report", response_model=HotspotReportResponse)
def agent_hotspot_report(payload: HotspotReportRequest) -> HotspotReportResponse:
    """Generate a detailed AI report for a specific hotspot with simulation."""
    from src.intelligence.planner_engine import build_planner_response
    from src.observability.tracing import create_trace_id
    
    trace_id = payload.trace_id or create_trace_id()
    hotspot = payload.hotspot
    region = hotspot.get("region_name") or hotspot.get("region", "Unknown Region")
    
    # Build query for the agent
    query = (
        f"Create a detailed action plan for {region}. "
        f"Gap score: {hotspot.get('gap_score', 0):.2f}, "
        f"Population affected: {hotspot.get('population_affected', 0):,}, "
        f"Missing capabilities: {', '.join(hotspot.get('missing_capabilities', []))}. "
        "Provide specific actions, timeline, risks, and expected impact."
    )
    
    # Run the agent to generate personalized recommendations
    try:
        agent_result = run_agent(
            query=query,
            provider="openai",
            model=None,
            top_k=5,
            enable_rag=True,
            system_prompt=(
                "You are a healthcare planning expert. Generate specific, actionable "
                "recommendations for addressing healthcare gaps in underserved regions. "
                "Focus on oncology services and capacity building."
            ),
            metadata={"hotspot": hotspot, "trace_id": trace_id}
        )
    except Exception as e:
        # Fallback if agent fails
        agent_result = {
            "answer": f"Prioritized action plan for {region} based on gap analysis.",
            "plan": {},
            "citations": [],
            "council": [],
            "risk_flags": [],
            "trace_id": trace_id,
            "provenance_id": "",
        }
    
    # Build the planner response with the hotspot data
    planner_payload = {
        "region": region,
        "demand": payload.demand,
        "supply": payload.supply,
        "gap": payload.gap,
        "hotspots": [hotspot],
        "recommendations": payload.recommendations,
        "baseline_kpis": payload.baseline_kpis,
    }
    
    planner_result = build_planner_response(planner_payload, trace_id=trace_id)
    
    # Merge agent insights into the planner result
    if agent_result.get("plan"):
        plan_data = agent_result["plan"]
        if isinstance(plan_data, dict):
            # Extract actions from agent plan
            if plan_data.get("actions"):
                planner_result["action_plan"]["actions"] = plan_data["actions"]
            if plan_data.get("timeline"):
                planner_result["action_plan"]["timeline"] = plan_data["timeline"]
            if plan_data.get("risks"):
                planner_result["action_plan"]["risks"] = plan_data["risks"]
            if plan_data.get("confidence"):
                planner_result["action_plan"]["confidence"] = plan_data["confidence"]
    
    # Add agent response to the result
    planner_result["agent_report"] = {
        "answer": agent_result.get("answer", ""),
        "citations": [
            {"source": source, "content": content[:200], "score": score}
            for source, content, score in agent_result.get("citations", [])[:3]
        ],
        "council": agent_result.get("council", []),
        "risk_flags": agent_result.get("risk_flags", []),
        "trace_id": agent_result.get("trace_id", trace_id),
        "provenance_id": agent_result.get("provenance_id", ""),
    }
    
    # Generate scenario simulation
    scenario_result = run_scenario_plan(planner_result.get("action_plan", {}))
    planner_result["simulation"] = scenario_result
    
    return HotspotReportResponse(**planner_result)
