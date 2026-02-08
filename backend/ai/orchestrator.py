from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from src.ai.llm_client import call_llm
from src.ai.openai_client import DEFAULT_OPENAI_MODEL

from .tools.rag_tool import retrieve_context
from .tools.validator_tool import validate_medical_response

logger = logging.getLogger(__name__)

# Architecture: LangGraph orchestrator + LanceDB vector store
# - LangGraph: explicit graph for RAG -> Validate -> Respond flow
# - LanceDB: persistent vector storage (backend/data/vectors/)
# - Non-streaming default for simplicity and MLflow integration


class OrchestratorState(TypedDict):
    question: str
    mode: str
    dataset_id: str
    context: str
    retrieved_chunks: List[Dict]
    answer: str
    validation: Dict
    metadata: Dict


class MedicalOrchestrator:
    """
    LangGraph-based orchestrator for medical Q&A.
    Flow: Retrieve -> Generate -> Validate -> Respond
    """

    def __init__(self, dataset_id: str | None = None) -> None:
        self.dataset_id = dataset_id
        self.graph = self._build_graph()

    def _retrieve_node(self, state: OrchestratorState) -> OrchestratorState:
        logger.info("Orchestrator: retrieving context")
        start_time = time.time()

        if state["mode"] in ["rag", "hybrid"] and self.dataset_id:
            chunks = retrieve_context.invoke(
                {"query": state["question"], "dataset_id": self.dataset_id, "top_k": 5}
            )
            state["retrieved_chunks"] = chunks
            state["context"] = "\n\n".join([chunk["text"] for chunk in chunks])
        else:
            state["retrieved_chunks"] = []
            state["context"] = state.get("context", "")

        state["metadata"]["retrieval_time_ms"] = (time.time() - start_time) * 1000
        return state

    def _generate_node(self, state: OrchestratorState) -> OrchestratorState:
        logger.info("Orchestrator: generating answer")
        start_time = time.time()

        if state["context"]:
            prompt = (
                "Answer the following medical question based on the provided context.\n"
                "Be accurate and cite the context when possible.\n\n"
                f"Context:\n{state['context']}\n\n"
                f"Question: {state['question']}\n\n"
                "Answer:"
            )
        else:
            prompt = (
                "Answer the following medical question.\n\n"
                f"Question: {state['question']}\n\n"
                "Answer:"
            )

        try:
            response = call_llm(prompt=prompt, model=DEFAULT_OPENAI_MODEL)
            state["answer"] = response.text
            state["metadata"]["llm_model"] = response.model
            state["metadata"]["llm_provider"] = response.provider
            state["metadata"]["llm_latency_ms"] = response.latency_ms
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            state["answer"] = f"Error generating answer: {exc}"

        state["metadata"]["generation_time_ms"] = (time.time() - start_time) * 1000
        return state

    def _validate_node(self, state: OrchestratorState) -> OrchestratorState:
        logger.info("Orchestrator: validating answer")
        validation = validate_medical_response.invoke(
            {"answer": state["answer"], "sources": state["retrieved_chunks"]}
        )
        state["validation"] = validation
        return state

    def _build_graph(self):
        workflow = StateGraph(OrchestratorState)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("validate", self._validate_node)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", "validate")
        workflow.add_edge("validate", END)

        return workflow.compile()

    def run(self, question: str, mode: str = "rag", context: str = "") -> Dict[str, Any]:
        logger.info("Running orchestrator for question: %s", question)

        initial_state: OrchestratorState = {
            "question": question,
            "mode": mode,
            "dataset_id": self.dataset_id or "",
            "context": context,
            "retrieved_chunks": [],
            "answer": "",
            "validation": {},
            "metadata": {},
        }

        final_state = self.graph.invoke(initial_state)

        return {
            "answer": final_state["answer"],
            "sources": final_state["retrieved_chunks"],
            "validation": final_state["validation"],
            "metadata": {
                **final_state.get("metadata", {}),
                "mode": mode,
                "retrieved_chunks_count": len(final_state["retrieved_chunks"]),
            },
        }
