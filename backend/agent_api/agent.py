from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from .rag import retrieve_documents
from .tracking import trace_agent_start, trace_agent_step, trace_agent_end, Stopwatch
from src.observability.tracing import create_trace_id
from src.observability.provenance import write_provenance


DEFAULT_SYSTEM_PROMPT = (
    "You are a healthcare planning assistant. Provide structured, evidence-first "
    "recommendations. If citations are missing, respond with 'insufficient evidence'."
)

TEXT2SQL_PROMPT = (
    "You are Text2SQL Genie. Convert the user question into a single SQL query "
    "using ONLY the provided schema. Return only SQL with no commentary."
)


class PlannerOutput(BaseModel):
    summary: str
    focus_region: str
    goals: List[str]
    actions: List[str]
    timeline: List[str]
    dependencies: List[str]
    risks: List[str]
    confidence: str = Field(default="medium")


class VerifierOutput(BaseModel):
    evidence_ok: bool
    risk_flags: List[str]
    compliance_notes: List[str]
    confidence: str = Field(default="medium")


class WriterOutput(BaseModel):
    answer: str
    confidence: str = Field(default="medium")


class AgentState(TypedDict):
    trace_id: str
    query: str
    metadata: Dict[str, Any]
    plan: Optional[PlannerOutput]
    citations: List[Tuple[str, str, Optional[float]]]
    context: str
    verifier: Optional[VerifierOutput]
    answer: str


def _build_llm(model: Optional[str]) -> ChatOpenAI:
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model_name, temperature=temperature)


def _enforce_openai(provider: str) -> None:
    if provider != "openai":
        raise ValueError("Only the OpenAI provider is enabled.")


def _format_context(citations: List[Tuple[str, str, Optional[float]]]) -> str:
    blocks = []
    for source, content, score in citations:
        blocks.append(f"Source: {source}\nRelevance: {score}\n{content}")
    return "\n\n".join(blocks)


def _estimate_eval(answer: str, citations: List[Tuple[str, str, Optional[float]]], elapsed_ms: int) -> Dict[str, Any]:
    citations_count = len(citations)
    evidence_coverage = min(1.0, citations_count / 3.0)
    faithfulness = 1.0 if citations_count > 0 else 0.0
    completeness = min(1.0, max(0.2, len(answer) / 600.0))
    cost_estimate = round((len(answer) / 4.0) * 0.00002, 6)
    return {
        "faithfulness": faithfulness,
        "completeness": completeness,
        "evidence_coverage": evidence_coverage,
        "citations_count": citations_count,
        "latency_ms": elapsed_ms,
        "cost_estimate_usd": cost_estimate,
    }


def _planner_node(state: AgentState) -> AgentState:
    llm = _build_llm(state["metadata"].get("model"))
    planner = llm.with_structured_output(PlannerOutput)
    prompt = (
        "Create a structured action plan for the query. Focus on medical access gaps.\n"
        f"Query: {state['query']}\n"
    )
    plan = planner.invoke(prompt)
    trace_agent_step(
        state["trace_id"],
        "planner_complete",
        outputs={"actions": len(plan.actions), "risks": len(plan.risks)},
    )
    return {**state, "plan": plan}


def _retriever_node(state: AgentState) -> AgentState:
    if not state["metadata"].get("enable_rag", True):
        return {**state, "citations": [], "context": ""}
    docs = retrieve_documents(state["query"], top_k=state["metadata"].get("top_k", 4))
    citations = [(doc.metadata.get("source", "unknown"), doc.page_content, score) for doc, score in docs]
    context = _format_context(citations)
    trace_agent_step(
        state["trace_id"],
        "retriever_complete",
        outputs={"citations": len(citations)},
    )
    return {**state, "citations": citations, "context": context}


def _verifier_node(state: AgentState) -> AgentState:
    if not state["citations"]:
        result = VerifierOutput(
            evidence_ok=False,
            risk_flags=["No citations available."],
            compliance_notes=["Insufficient evidence to provide a recommendation."],
            confidence="low",
        )
        trace_agent_step(
            state["trace_id"],
            "verifier_complete",
            outputs={"evidence_ok": False, "risk_flags": len(result.risk_flags)},
        )
        return {
            **state,
            "verifier": result,
        }
    llm = _build_llm(state["metadata"].get("model"))
    verifier = llm.with_structured_output(VerifierOutput)
    prompt = (
        "Validate the plan against evidence. Flag any risky or unsupported claims.\n"
        f"Plan Summary: {state['plan'].summary if state['plan'] else ''}\n"
        f"Context: {state['context']}\n"
    )
    result = verifier.invoke(prompt)
    trace_agent_step(
        state["trace_id"],
        "verifier_complete",
        outputs={"evidence_ok": result.evidence_ok, "risk_flags": len(result.risk_flags)},
    )
    return {**state, "verifier": result}


def _writer_node(state: AgentState) -> AgentState:
    verifier = state["verifier"]
    if verifier and not verifier.evidence_ok:
        trace_agent_step(
            state["trace_id"],
            "writer_complete",
            outputs={"evidence_ok": False},
        )
        return {**state, "answer": "Insufficient evidence to answer with citations."}
    llm = _build_llm(state["metadata"].get("model"))
    writer = llm.with_structured_output(WriterOutput)
    prompt = (
        "Write a concise, evidence-based recommendation with actions, risks, and timeline. "
        "Include short citations list at the end.\n"
        f"Plan: {state['plan'].model_dump() if state['plan'] else {}}\n"
        f"Context: {state['context']}\n"
    )
    result = writer.invoke(prompt)
    trace_agent_step(
        state["trace_id"],
        "writer_complete",
        outputs={"answer_length": len(result.answer)},
    )
    return {**state, "answer": result.answer}


def _build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("planner", _planner_node)
    graph.add_node("retriever", _retriever_node)
    graph.add_node("verifier", _verifier_node)
    graph.add_node("writer", _writer_node)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "verifier")
    graph.add_edge("verifier", "writer")
    graph.add_edge("writer", END)
    return graph


def run_agent(
    query: str,
    provider: str,
    model: Optional[str],
    top_k: int,
    enable_rag: bool,
    system_prompt: Optional[str],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    _enforce_openai(provider)
    trace_id = create_trace_id()
    stopwatch = Stopwatch()
    trace_agent_start(
        trace_id,
        {
            "query_length": len(query),
            "provider": provider,
            "model": model or "",
            "rag_enabled": enable_rag,
            "top_k": top_k,
        },
    )

    state: AgentState = {
        "trace_id": trace_id,
        "query": query,
        "metadata": {"top_k": top_k, "model": model, "enable_rag": enable_rag, **(metadata or {})},
        "plan": None,
        "citations": [],
        "context": "",
        "verifier": None,
        "answer": "",
    }

    graph = _build_graph().compile()
    result: AgentState = graph.invoke(state)

    trace_agent_step(
        trace_id,
        "agent_complete",
        outputs={"answer_length": len(result["answer"]), "citations": len(result["citations"])},
    )

    eval_metrics = _estimate_eval(result["answer"], result["citations"], stopwatch.elapsed_ms())
    provenance_id = write_provenance(
        {
            "trace_id": trace_id,
            "query": query,
            "citations": [{"source": source, "score": score} for source, _, score in result["citations"]],
            "model": _build_llm(model).model_name,
            "provider": provider,
            "eval_metrics": eval_metrics,
        }
    )
    trace_agent_end(
        trace_id,
        outputs={
            "answer": result["answer"],
            "citations": [{"source": source, "score": score} for source, _, score in result["citations"]],
            "eval_metrics": eval_metrics,
        },
        params={"model": _build_llm(model).model_name, "provider": provider},
    )

    verifier = result["verifier"] or VerifierOutput(
        evidence_ok=bool(result["citations"]),
        risk_flags=[],
        compliance_notes=[],
        confidence="low",
    )

    council = []
    if result["plan"]:
        council.append(
            {
                "role": "planner",
                "summary": result["plan"].summary,
                "details": result["plan"].model_dump(),
                "confidence": result["plan"].confidence,
            }
        )
    council.append(
        {
            "role": "retriever",
            "summary": f"Retrieved {len(result['citations'])} sources.",
            "details": {"sources": [source for source, _, _ in result["citations"]]},
            "confidence": "medium" if result["citations"] else "low",
        }
    )
    council.append(
        {
            "role": "verifier",
            "summary": "Evidence verified." if verifier.evidence_ok else "Evidence insufficient.",
            "details": verifier.model_dump(),
            "confidence": verifier.confidence,
        }
    )
    council.append(
        {
            "role": "writer",
            "summary": result["answer"][:160],
            "details": {"answer_length": len(result["answer"])},
            "confidence": "medium",
        }
    )

    return {
        "trace_id": trace_id,
        "answer": result["answer"],
        "citations": result["citations"],
        "provider": provider,
        "model": _build_llm(model).model_name,
        "elapsed_ms": stopwatch.elapsed_ms(),
        "rag_used": bool(result["citations"]),
        "plan": result["plan"].model_dump() if result["plan"] else {},
        "verifier": verifier.model_dump(),
        "eval_metrics": eval_metrics,
        "council": council,
        "risk_flags": verifier.risk_flags,
        "compliance_notes": verifier.compliance_notes,
        "provenance_id": provenance_id,
    }


def _sql_is_read_only(sql: str) -> bool:
    forbidden = re.compile(r"\\b(insert|update|delete|drop|create|alter|truncate)\\b", re.I)
    return not forbidden.search(sql) and sql.strip().lower().startswith("select")


def run_text2sql(
    question: str,
    schema: str,
    provider: str,
    model: Optional[str],
    system_prompt: Optional[str],
) -> Dict[str, Any]:
    _enforce_openai(provider)
    trace_id = create_trace_id()
    stopwatch = Stopwatch()
    trace_agent_start(
        trace_id,
        {
            "question_length": len(question),
            "provider": provider,
            "model": model or "",
            "mode": "text2sql",
        },
    )

    llm = _build_llm(model)
    prompt = system_prompt or TEXT2SQL_PROMPT
    response = llm.invoke(
        [
            ("system", prompt),
            ("human", f"Schema:\n{schema}\n\nQuestion:\n{question}"),
        ]
    )
    sql = response.content.strip()
    if not _sql_is_read_only(sql):
        raise ValueError("Generated SQL is not read-only.")

    trace_agent_step(
        trace_id,
        "text2sql_complete",
        outputs={"sql_length": len(sql)},
    )
    trace_agent_end(
        trace_id,
        outputs={"sql": sql},
        params={"model": llm.model_name, "provider": provider},
    )

    return {
        "trace_id": trace_id,
        "sql": sql,
        "provider": provider,
        "model": llm.model_name,
        "elapsed_ms": stopwatch.elapsed_ms(),
    }


def build_action_graph(actions: List[str], dependencies: Optional[List[str]] = None) -> Dict[str, Any]:
    nodes = [{"id": f"action-{idx}", "label": action} for idx, action in enumerate(actions)]
    edges: List[Dict[str, str]] = []
    if dependencies:
        for dep in dependencies:
            if "->" in dep:
                left, right = [part.strip() for part in dep.split("->", 1)]
                try:
                    source_idx = actions.index(left)
                    target_idx = actions.index(right)
                    edges.append(
                        {
                            "from_action": f"action-{source_idx}",
                            "to_action": f"action-{target_idx}",
                            "reason": dep,
                        }
                    )
                except ValueError:
                    continue
    if not edges and len(actions) > 1:
        for idx in range(len(actions) - 1):
            edges.append(
                {
                    "from_action": f"action-{idx}",
                    "to_action": f"action-{idx + 1}",
                    "reason": "sequenced",
                }
            )
    critical_path = [node["id"] for node in nodes]
    return {"nodes": nodes, "edges": edges, "critical_path": critical_path}


def run_scenario_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    action_count = len(plan.get("actions") or [])
    base_coverage = 10 + action_count * 3
    base_underserved = 40 + action_count * 8
    base_roi = max(1.4, 3.8 - action_count * 0.2)
    presets = {}
    for label, multiplier in [("Low", 0.7), ("Balanced", 1.0), ("Aggressive", 1.3)]:
        coverage_delta = int(base_coverage * multiplier)
        underserved_delta = int(base_underserved * multiplier)
        roi_window = f"{base_roi / multiplier:.1f} yrs"
        demand_impact = [
            {"month": f"M{idx+1}", "baseline": 100 + idx * 2, "simulated": 100 - coverage_delta + idx}
            for idx in range(6)
        ]
        coverage_shift = [
            {"region": "North", "baseline": 42, "simulated": 42 + coverage_delta // 2},
            {"region": "Central", "baseline": 55, "simulated": 55 + coverage_delta // 2},
            {"region": "East", "baseline": 48, "simulated": 48 + coverage_delta // 2},
            {"region": "South", "baseline": 62, "simulated": 62 + coverage_delta // 2},
        ]
        cost_curve = {"cost": int(350 * multiplier), "impact": coverage_delta}
        presets[label] = {
            "coverage_delta": coverage_delta,
            "underserved_delta": underserved_delta,
            "roi_window": roi_window,
            "demand_impact": demand_impact,
            "coverage_shift": coverage_shift,
            "cost_curve": cost_curve,
        }
    return {"simulation_presets": presets}
