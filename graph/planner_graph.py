# Updated graph/planner_graph.py
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from tools.planner_tools import generate_got_subtasks, score_subtasks_with_llm, merge_subtasks, perform_hitl_validation
from ui.ui import workflow_status, workflow_status_lock
import logging
import os
from dotenv import load_dotenv
import queue
from threading import Thread

logger = logging.getLogger(__name__)


class PlannerState(TypedDict):
    """State for the planner sub-graph"""
    issue_data: Dict[str, Any]
    thread_id: str
    subtasks_graph: Optional[Dict[str, Any]]
    scored_subtasks: List[Dict[str, Any]]
    merged_subtasks: List[Dict[str, Any]]
    approved_subtasks: List[Dict[str, Any]]
    overall_subtask_score: float
    needs_human: bool
    human_decision: Optional[str]
    error: str
    tokens_used: int


def _route_success_or_error(state: PlannerState) -> str:
    return "error" if state.get("error") else "success"


def _check_overall_score(state: PlannerState) -> str:
    if state.get("error"):
        return "error"
    overall = state.get("overall_subtask_score", 0.0)
    threshold = float(os.getenv("GOT_SCORE_THRESHOLD", "7.0")) # Adapted from config
    if overall >= threshold:
        return "proceed"
    return "review"


def _generate_subtasks_node(state: PlannerState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "PlannerAgent"
    thread_id = state.get("thread_id", "unknown")
    issue_data = state.get("issue_data", {})
    logger.info(f"[PLANNER-{thread_id}] Generating subtasks...")
    try:
        result = generate_got_subtasks.invoke({
            "issue_data": issue_data,
            "thread_id": thread_id
        })
        if result.get("success"):
            from agents.planner_agent import PlannerAgent # Moved import inside function
            PlannerAgent._store_to_mongodb(
                issue_key=issue_data.get('key', 'UNKNOWN'),
                subtasks=result.get("subtasks_graph")["nodes"],
                model=os.getenv("PLANNER_LLM_MODEL", "unknown"),
                description=issue_data.get('description', ''),
                scores=None, # No scores yet
                tokens_used=result.get("tokens_used", 0)
            )
            return {
                "subtasks_graph": result.get("subtasks_graph"),
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
            }
        else:
            return {"error": result.get("error", "Subtask generation failed")}
    except Exception as e:
        logger.error(f"[PLANNER-{thread_id}] Subtask generation failed: {e}")
        return {"error": str(e)}


def _score_subtasks_node(state: PlannerState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "PlannerAgent"
    thread_id = state.get("thread_id", "unknown")
    subtasks_graph = state.get("subtasks_graph", {})
    issue_data = state.get("issue_data", {})
    logger.info(f"[PLANNER-{thread_id}] Scoring subtasks...")
    try:
        result = score_subtasks_with_llm.invoke({
            "subtasks_graph": subtasks_graph,
            "requirements": {
                "project_description": issue_data.get('summary', ''),
                "requirements": [issue_data.get('description', '')],
                "reasoning": "Derived from issue data"
            },
            "thread_id": thread_id
        })
        if result.get("success"):
            scored_subtasks = result.get("scored_subtasks", [])
            if scored_subtasks:
                overall = sum(s['score'] for s in scored_subtasks) / len(scored_subtasks)
            else:
                overall = 0.0
            # Log overall score first
            logger.info(f"[PLANNER-{thread_id}] Overall subtask score: {overall:.1f}")
            # Then log all subtasks with scores
            for subtask in scored_subtasks:
                logger.info(
                    f"[PLANNER-{thread_id}] Subtask {subtask['id']}: Score {subtask['score']:.1f} - {subtask['description']}")
            # NEW: Store scores (update existing or new doc)
            from agents.planner_agent import PlannerAgent # Moved import inside function
            PlannerAgent._store_to_mongodb(
                issue_key=state["issue_data"].get('key', 'UNKNOWN'),
                subtasks=subtasks_graph["nodes"], # Original subtasks
                model=os.getenv("PLANNER_LLM_MODEL", "unknown"),
                description=state["issue_data"].get('description', ''),
                scores=scored_subtasks,
                tokens_used=result.get("tokens_used", 0)
            )
            return {
                "scored_subtasks": scored_subtasks,
                "overall_subtask_score": overall,
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
            }
        else:
            return {"error": result.get("error", "Subtask scoring failed")}
    except Exception as e:
        logger.error(f"[PLANNER-{thread_id}] Subtask scoring failed: {e}")
        return {"error": str(e)}


def _merge_subtasks_node(state: PlannerState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "PlannerAgent"
    thread_id = state.get("thread_id", "unknown")
    scored_subtasks = state.get("scored_subtasks", [])
    jira_description = state.get("issue_data", {}).get("description", "")

    logger.info(f"[PLANNER-{thread_id}] Merging subtasks...")

    try:
        result = merge_subtasks.invoke({
            "scored_subtasks": scored_subtasks,
            "jira_description": jira_description,
            "thread_id": thread_id
        })

        if result.get("success"):
            return {
                "merged_subtasks": result.get("merged_subtasks"),
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
            }
        else:
            return {"error": result.get("error", "Subtask merging failed")}
    except Exception as e:
        logger.error(f"[PLANNER-{thread_id}] Subtask merging failed: {e}")
        return {"error": str(e)}


def _set_approved_subtasks_node(state: PlannerState) -> Dict[str, Any]:
    """Node: Set approved subtasks for high-scoring tasks"""
    state["approved_subtasks"] = state.get("merged_subtasks", [])  # Use merged subtasks
    state["needs_human"] = False
    return state


def _hitl_validation_node(state: PlannerState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "PlannerAgent"
    thread_id = state.get("thread_id", "unknown")
    scored_subtasks = state.get("scored_subtasks", [])
    overall = state.get("overall_subtask_score", 0.0)
    threshold = float(os.getenv("GOT_SCORE_THRESHOLD", "7.0")) # Adapted from config
    timeout_seconds = int(os.getenv("HITL_TIMEOUT_SECONDS", "30")) # Adapted from config
    logger.info(f"[PLANNER-{thread_id}] Overall score {overall:.1f} < {threshold:.1f} - HITL validation required")
    q = queue.Queue()
    def get_input(q):
        try:
            resp = input(
                f"Approve subtasks (score {overall:.1f}/{threshold:.1f})? (Y/N) [default Y]: ").strip().upper() or "Y"
            q.put(resp)
        except EOFError:
            q.put("Y")
    thread = Thread(target=get_input, args=(q,))
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        approval = "Y" # Auto-approve on timeout
        logger.info(
            f"[PLANNER-{thread_id}] HITL timeout after {timeout_seconds}s - auto-approving subtasks")
    else:
        approval = q.get()
    if approval == "Y":
        state["approved_subtasks"] = state.get("merged_subtasks", [])  # Use merged after approval
        state["needs_human"] = False
    else:
        state["needs_human"] = True
        state["human_decision"] = "reject"
        state["error"] = "Subtasks rejected by human - rebuild required"
    return state


def _handle_error_node(state: PlannerState) -> Dict[str, Any]:
    """Node: Handle errors"""
    thread_id = state.get("thread_id", "unknown")
    error_msg = state.get("error", "Unknown error")
    logger.error(f"[PLANNER-{thread_id}] Workflow error: {error_msg}")
    state["needs_human"] = True
    return state


def build_planner_graph():
    graph = StateGraph(PlannerState)
    # Add merge node
    graph.add_node("generate_subtasks", _generate_subtasks_node)
    graph.add_node("score_subtasks", _score_subtasks_node)
    graph.add_node("merge_subtasks", _merge_subtasks_node)
    graph.add_node("set_approved_subtasks", _set_approved_subtasks_node)
    graph.add_node("hitl_validation", _hitl_validation_node)
    graph.add_node("handle_error", _handle_error_node)
    # Edges
    graph.add_edge(START, "generate_subtasks")
    graph.add_conditional_edges("generate_subtasks", _route_success_or_error,
                                {"success": "score_subtasks", "error": "handle_error"})
    graph.add_conditional_edges("score_subtasks", _route_success_or_error,
                                {"success": "merge_subtasks", "error": "handle_error"})
    graph.add_conditional_edges("merge_subtasks", _route_success_or_error,
                                {"success": "set_approved_subtasks", "error": "handle_error"})
    graph.add_conditional_edges("set_approved_subtasks", _check_overall_score,
                                {"proceed": END, "review": "hitl_validation",
                                 "error": "handle_error"})
    graph.add_conditional_edges("hitl_validation", _route_success_or_error,
                                {"success": END, "error": "handle_error"})
    graph.add_edge("handle_error", END)
    return graph.compile()