from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from .rag import retrieve_documents
from .tracking import trace_agent_start, trace_agent_step, trace_agent_end, Stopwatch
from src.observability.tracing import create_trace_id


DEFAULT_SYSTEM_PROMPT = (
    "You are a healthcare planning assistant. Use tools when helpful. "
    "If retrieval is used, cite the sources in a short bullet list at the end "
    "of the answer. Keep the response concise and actionable."
)

TEXT2SQL_PROMPT = (
    "You are Text2SQL Genie. Convert the user question into a single SQL query "
    "using ONLY the provided schema. Return only SQL with no commentary."
)


def _build_llm(provider: str, model: Optional[str]):
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    if provider == "anthropic":
        model_name = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
        return ChatAnthropic(model=model_name, temperature=temperature)
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model_name, temperature=temperature)


def run_agent(
    query: str,
    provider: str,
    model: Optional[str],
    top_k: int,
    enable_rag: bool,
    system_prompt: Optional[str],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
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

    citations: List[Tuple[str, str, Optional[float]]] = []

    def _track_retrieval(docs: List[Tuple[Any, float]]) -> str:
        citations.clear()
        context_blocks = []
        for doc, score in docs:
            source = doc.metadata.get("source", "unknown")
            citations.append((source, doc.page_content, float(score)))
            context_blocks.append(f"Source: {source}\n{doc.page_content}")
        return "\n\n".join(context_blocks)

    tools = []
    if enable_rag:

        @tool("retrieve_context")
        def retrieve_context(question: str) -> str:
            """Retrieve relevant context for a question."""
            docs = retrieve_documents(question, top_k=top_k)
            trace_agent_step(
                trace_id,
                "rag_retrieve",
                inputs={"question": question, "top_k": top_k},
                outputs={"matches": len(docs)},
            )
            return _track_retrieval(docs)

        tools.append(retrieve_context)

    llm = _build_llm(provider, model)
    graph = create_react_agent(llm, tools, prompt=system_prompt or DEFAULT_SYSTEM_PROMPT)
    result = graph.invoke({"messages": [HumanMessage(content=query)]})
    messages = result.get("messages") or []
    answer = messages[-1].content if messages else ""
    trace_agent_step(
        trace_id,
        "agent_complete",
        outputs={"answer_length": len(answer), "tool_calls": len(citations)},
    )

    trace_agent_end(
        trace_id,
        outputs={
            "answer": answer,
            "citations": [
                {"source": source, "score": score} for source, _, score in citations
            ],
        },
        params={
            "model": llm.model_name if hasattr(llm, "model_name") else "",
            "provider": provider,
        },
    )

    return {
        "trace_id": trace_id,
        "answer": answer,
        "citations": citations,
        "provider": provider,
        "model": llm.model_name if hasattr(llm, "model_name") else "",
        "elapsed_ms": stopwatch.elapsed_ms(),
        "rag_used": bool(citations),
    }


def run_text2sql(
    question: str,
    schema: str,
    provider: str,
    model: Optional[str],
    system_prompt: Optional[str],
) -> Dict[str, Any]:
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

    llm = _build_llm(provider, model)
    prompt = system_prompt or TEXT2SQL_PROMPT
    response = llm.invoke(
        [
            ("system", prompt),
            ("human", f"Schema:\n{schema}\n\nQuestion:\n{question}"),
        ]
    )
    sql = response.content.strip()

    trace_agent_step(
        trace_id,
        "text2sql_complete",
        outputs={"sql_length": len(sql)},
    )
    trace_agent_end(
        trace_id,
        outputs={"sql": sql},
        params={"model": llm.model_name if hasattr(llm, "model_name") else "", "provider": provider},
    )

    return {
        "trace_id": trace_id,
        "sql": sql,
        "provider": provider,
        "model": llm.model_name if hasattr(llm, "model_name") else "",
        "elapsed_ms": stopwatch.elapsed_ms(),
    }
