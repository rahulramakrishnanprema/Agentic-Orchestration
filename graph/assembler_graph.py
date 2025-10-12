"""
Assembler Agent LangGraph Workflow
Creates comprehensive deployment documents from subtasks
"""
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from tools.assembler_tool import generate_deployment_document
import logging
import json
import os

logger = logging.getLogger(__name__)


class AssemblerState(TypedDict):
    """State for the assembler sub-graph"""
    issue_data: Dict[str, Any]
    approved_subtasks: List[Dict[str, Any]]
    thread_id: str
    deployment_document: Optional[Dict[str, Any]]
    error: str
    tokens_used: int


def _route_success_or_error(state: AssemblerState) -> str:
    return "error" if state.get("error") else "success"


def _generate_document_node(state: AssemblerState) -> Dict[str, Any]:
    """Generate complete deployment document in one step"""
    thread_id = state.get("thread_id", "unknown")
    approved_subtasks = state.get("approved_subtasks", [])
    issue_data = state.get("issue_data", {})

    logger.info(f"[ASSEMBLER-{thread_id}] Generating full deployment document...")

    try:
        result = generate_deployment_document.invoke({
            "issue_data": issue_data,
            "subtasks": approved_subtasks,
            "thread_id": thread_id
        })

        if result.get("success"):
            return {
                "deployment_document": result.get("document"),
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
            }
        else:
            return {"error": result.get("error", "Document generation failed")}
    except Exception as e:
        logger.error(f"[ASSEMBLER-{thread_id}] Document generation failed: {e}")
        return {"error": str(e)}


def build_assembler_graph():
    """Build the assembler LangGraph workflow"""
    graph = StateGraph(AssemblerState)

    # Add single node
    graph.add_node("generate_document", _generate_document_node)

    # Define edges
    graph.add_edge(START, "generate_document")

    graph.add_conditional_edges(
        "generate_document",
        _route_success_or_error,
        {"success": END, "error": END}
    )

    return graph.compile()