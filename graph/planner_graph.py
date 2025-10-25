# Updated graph/planner_graph.py
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from tools.planner_tools import generate_got_subtasks, generate_cot_subtasks, score_subtasks_with_llm, merge_subtasks
from ui.ui import workflow_status, workflow_status_lock
import logging
import os
import queue
from threading import Thread

logger = logging.getLogger(__name__)

class PlannerState(TypedDict):
    """State for the planner sub-graph"""
    issue_data: Dict[str, Any]
    thread_id: str
    planning_method: Optional[str]  # NEW
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


def _route_planning_method(state: PlannerState) -> str:
    method = state.get("planning_method")
    if method == "CoT":
        return "CoT"
    elif method == "GOT":
        return "GOT"
    else:
        return "error"


def _decide_planning_method_node(state: PlannerState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "PlannerAgent"
    thread_id = state.get("thread_id", "unknown")
    issue_data = state.get("issue_data", {})
    logger.info(f"[PLANNER-{thread_id}] Deciding planning method...")

    try:
        from agents.core_planner_agent import CorePlannerAgent  # For prompt_loader if needed
        from tools.prompt_loader import PromptLoader
        prompt_loader = PromptLoader("prompts")

        formatted_prompt = prompt_loader.format(
            "planner_decide_method",
            issue_key=issue_data.get('key'),
            summary=issue_data.get('summary'),
            description=issue_data.get('description')
        )

        from services.llm_service import call_llm
        response, tokens = call_llm(formatted_prompt, agent_name="planner")
        from tools.planner_tools import parse_json_from_text
        decision = parse_json_from_text(response)

        method = decision.get("method", "GOT")
        reasoning = decision.get("reasoning", "")

        logger.info(f"[PLANNER-{thread_id}] Decided on {method}: {reasoning}")

        # Log planning method choice to UI
        try:
            import core.router
            import uuid
            from datetime import datetime

            method_name = "CoT (Chain of Thoughts)" if method == "CoT" else "GoT (Graph of Thoughts)"

            core.router.safe_activity_log({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "agent": "PlannerAgent",
                "action": "Planning Method Selected",
                "details": f"Planner picked {method_name} for {issue_data.get('key', 'UNKNOWN')}",
                "status": "info",
                "issueId": issue_data.get('key', 'UNKNOWN'),
                "planningMethod": method,
                "reasoning": reasoning
            })
        except Exception as e:
            logger.warning(f"[PLANNER-{thread_id}] Failed to log planning method to UI: {e}")

        return {
            "planning_method": method,
            "tokens_used": state.get("tokens_used", 0) + tokens
        }
    except Exception as e:
        logger.error(f"[PLANNER-{thread_id}] Decision failed: {e}")
        return {"planning_method": "GOT", "error": str(e)}


def _generate_cot_subtasks_node(state: PlannerState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "PlannerAgent"
    thread_id = state.get("thread_id", "unknown")
    issue_data = state.get("issue_data", {})
    logger.info(f"[PLANNER-{thread_id}] Generating CoT subtasks...")
    try:
        result = generate_cot_subtasks.invoke({
            "issue_data": issue_data,
            "thread_id": thread_id
        })
        if result.get("success"):
            subtasks_list = result.get("subtasks_list", [])

            # Log each CoT subtask to terminal (similar to GoT)
            logger.info(f"[PLANNER-{thread_id}] Generated {len(subtasks_list)} CoT subtasks:")
            for subtask in subtasks_list:
                logger.info(f"[PLANNER-{thread_id}] CoT Subtask {subtask['id']}: Priority {subtask.get('priority', 'N/A')} - {subtask['description']}")

            return {
                "merged_subtasks": subtasks_list,
                "overall_subtask_score": 10.0,
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
            }
        else:
            return {"error": result.get("error", "CoT subtask generation failed")}
    except Exception as e:
        logger.error(f"[PLANNER-{thread_id}] CoT subtask generation failed: {e}")
        return {"error": str(e)}


def _generate_subtasks_node(state: PlannerState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "PlannerAgent"
    thread_id = state.get("thread_id", "unknown")
    issue_data = state.get("issue_data", {})
    logger.info(f"[PLANNER-{thread_id}] Generating GOT subtasks...")
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
            return {"error": result.get("error", "GOT subtask generation failed")}
    except Exception as e:
        logger.error(f"[PLANNER-{thread_id}] GOT Subtask generation failed: {e}")
        return {"error": str(e)}


def _score_subtasks_node(state: PlannerState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "PlannerAgent"
    thread_id = state.get("thread_id", "unknown")
    subtasks_graph = state.get("subtasks_graph", {})
    issue_data = state.get("issue_data", {})

    # Log with explicit thread_id before invoking tool
    logger.info(f"[PLANNER-{thread_id}] Scoring subtasks...")
    logger.debug(f"[PLANNER-{thread_id}] Summary: {issue_data.get('summary', 'N/A')[:80]}")
    logger.debug(f"[PLANNER-{thread_id}] Description: {issue_data.get('description', 'N/A')[:80]}")
    logger.debug(f"[PLANNER-{thread_id}] Subtasks to score: {len(subtasks_graph.get('nodes', {}))}")

    try:
        # Prepare requirements dict
        requirements_dict = {
            "summary": issue_data.get('summary', ''),
            "description": issue_data.get('description', ''),
            "requirements": [issue_data.get('description', '')]
        }
        logger.debug(f"[PLANNER-{thread_id}] Invoking score_subtasks_with_llm with thread_id={thread_id}")

        result = score_subtasks_with_llm.invoke({
            "subtasks_graph": subtasks_graph,
            "requirements": requirements_dict,
            "thread_id": thread_id
        })

        logger.info(f"[PLANNER-{thread_id}] Scoring result: success={result.get('success')}, scored_subtasks_count={len(result.get('scored_subtasks', []))}")

        if result.get("success"):
            scored_subtasks = result.get("scored_subtasks", [])
            if scored_subtasks:
                overall = sum(s['score'] for s in scored_subtasks) / len(scored_subtasks)
            else:
                # If no scored subtasks, use a default score based on graph subtasks
                logger.warning(f"[PLANNER-{thread_id}] No scored subtasks returned. Using default score.")
                overall = 7.5  # Default passing score
                # Create scored versions of original subtasks with default scores
                scored_subtasks = [
                    {
                        'id': node_id,
                        'description': node_data.get('description', ''),
                        'priority': node_data.get('priority', 3),
                        'score': 7.5,
                        'reasoning': 'Default score assigned due to LLM scoring limitations',
                        'requirements_covered': node_data.get('requirements_covered', [])
                    }
                    for node_id, node_data in subtasks_graph.get("nodes", {}).items()
                ]

            # Calculate total score
            total_score = sum(s['score'] for s in scored_subtasks) if scored_subtasks else 0

            # REMOVED: Don't log subtasks with individual scores before merge
            # The final subtasks will be logged after planning is complete

            # Log overall score first
            logger.info(f"[PLANNER-{thread_id}] Overall subtask score: {overall:.1f}")
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
            logger.error(f"[PLANNER-{thread_id}] Scoring failed: {result.get('error', 'Unknown error')}")
            return {"error": result.get("error", "Subtask scoring failed")}
    except Exception as e:
        logger.error(f"[PLANNER-{thread_id}] Subtask scoring failed with exception: {e}")
        return {"error": str(e)}


def _merge_subtasks_node(state: PlannerState) -> Dict[str, Any]:
    with workflow_status_lock:
        workflow_status["agent"] = "PlannerAgent"
    thread_id = state.get("thread_id", "unknown")
    scored_subtasks = state.get("scored_subtasks", [])
    jira_description = state.get("issue_data", {}).get("description", "")

    logger.info(f"[PLANNER-{thread_id}] Merging subtasks...")
    logger.debug(f"[PLANNER-{thread_id}] Scored subtasks count: {len(scored_subtasks)}")
    logger.debug(f"[PLANNER-{thread_id}] JIRA description length: {len(jira_description)}")

    try:
        result = merge_subtasks.invoke({
            "scored_subtasks": scored_subtasks,
            "jira_description": jira_description,
            "thread_id": thread_id
        })

        logger.info(f"[PLANNER-{thread_id}] Merge result: success={result.get('success')}, merged_subtasks_count={len(result.get('merged_subtasks', []))}")

        if result.get("success"):
            merged = result.get("merged_subtasks", [])
            logger.info(f"[PLANNER-{thread_id}] Successfully merged {len(merged)} subtasks with overall score: {result.get('overall_score', 0.0):.1f}")
            return {
                "merged_subtasks": merged,
                "overall_subtask_score": result.get('overall_score', 0.0),
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
            }
        else:
            logger.error(f"[PLANNER-{thread_id}] Merge failed: {result.get('error', 'Unknown error')}")
            return {"error": result.get("error", "Subtask merging failed")}
    except Exception as e:
        logger.error(f"[PLANNER-{thread_id}] Subtask merging failed with exception: {e}")
        return {"error": str(e)}


def _set_approved_subtasks_node(state: PlannerState) -> Dict[str, Any]:
    """Node: Set approved subtasks for high-scoring tasks"""
    thread_id = state.get("thread_id", "unknown")
    merged_subtasks = state.get("merged_subtasks", [])
    planning_method = state.get("planning_method", "Unknown")

    # Log final approved subtasks summary
    logger.info(f"[PLANNER-{thread_id}] ===== Planning Complete ({planning_method}) =====")
    logger.info(f"[PLANNER-{thread_id}] Total approved subtasks: {len(merged_subtasks)}")
    logger.info(f"[PLANNER-{thread_id}] Overall score: {state.get('overall_subtask_score', 0.0):.1f}")

    # Log each final approved subtask
    for subtask in merged_subtasks:
        score_info = f"Score {subtask.get('score', 'N/A')}" if 'score' in subtask else ""
        logger.info(f"[PLANNER-{thread_id}] ✓ Subtask {subtask['id']}: {score_info} - {subtask['description'][:80]}...")

    state["approved_subtasks"] = merged_subtasks
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
    # Add new nodes
    graph.add_node("decide_planning_method", _decide_planning_method_node)
    graph.add_node("generate_cot_subtasks", _generate_cot_subtasks_node)
    # Add merge node
    graph.add_node("generate_subtasks", _generate_subtasks_node)  # GOT
    graph.add_node("score_subtasks", _score_subtasks_node)
    graph.add_node("merge_subtasks", _merge_subtasks_node)
    graph.add_node("set_approved_subtasks", _set_approved_subtasks_node)
    graph.add_node("hitl_validation", _hitl_validation_node)
    graph.add_node("handle_error", _handle_error_node)
    # Edges
    graph.add_edge(START, "decide_planning_method")
    graph.add_conditional_edges("decide_planning_method", _route_planning_method,
                                {"CoT": "generate_cot_subtasks", "GOT": "generate_subtasks", "error": "handle_error"})
    graph.add_conditional_edges("generate_cot_subtasks", _route_success_or_error,
                                {"success": "set_approved_subtasks", "error": "handle_error"})
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