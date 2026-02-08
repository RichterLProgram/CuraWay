from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import run_agent, run_text2sql
from .schemas import (
    AgentRunRequest,
    AgentRunResponse,
    Citation,
    HealthResponse,
    Text2SqlRequest,
    Text2SqlResponse,
)


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
    except Exception as exc:  # pragma: no cover - runtime error surface
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return Text2SqlResponse(
        trace_id=result["trace_id"],
        provider=result["provider"],
        model=result["model"],
        sql=result["sql"],
        elapsed_ms=result["elapsed_ms"],
    )
