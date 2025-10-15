"""
Core Planner Agent - Modular and Reusable
This is a standalone planner that can be integrated into any workflow.
It accepts any content/requirements and outputs subtasks.

Usage:
    from agents.core_planner_agent import CorePlannerAgent

    planner = CorePlannerAgent(config)
    result = planner.plan(content="Your requirements here", context={"key": "value"})
    # Returns: {"success": True, "subtasks": [...], "tokens_used": 100}
"""
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class CorePlannerState(dict):
    """State for the core planner workflow - Generic and reusable"""
    planning_method: Optional[str]  # NEW: "CoT" or "GOT"


class CorePlannerAgent:
    """
    Core Planner Agent - Framework-agnostic planning logic
    Can be used in any LangGraph workflow or standalone
    """

    def __init__(self, config=None):
        """Initialize the core planner"""
        self.config = config or {}
        self.score_threshold = float(os.getenv("GOT_SCORE_THRESHOLD", "7.0"))
        self.hitl_timeout = int(os.getenv("HITL_TIMEOUT_SECONDS", "30"))

        # Lazy import to avoid circular dependencies
        from tools.prompt_loader import PromptLoader
        self.prompt_loader = PromptLoader("prompts")

        # Build the graph
        self.graph = self._build_graph()
        logger.debug("Core Planner Agent initialized (modular version)")

    def _build_graph(self):
        """Build the core planner LangGraph"""
        graph = StateGraph(dict)

        # Add new decision node
        graph.add_node("decide_planning_method", self._decide_planning_method_node)

        # Add CoT generation node
        graph.add_node("generate_cot_subtasks", self._generate_cot_subtasks_node)

        # Existing nodes (GOT path)
        graph.add_node("generate_got_subtasks", self._generate_got_subtasks_node)
        graph.add_node("score_subtasks", self._score_subtasks_node)
        graph.add_node("merge_subtasks", self._merge_subtasks_node)
        graph.add_node("set_approved", self._set_approved_node)
        graph.add_node("hitl_validation", self._hitl_validation_node)
        graph.add_node("handle_error", self._handle_error_node)

        # New edges
        graph.add_edge(START, "decide_planning_method")
        graph.add_conditional_edges(
            "decide_planning_method",
            self._route_planning_method,
            {"CoT": "generate_cot_subtasks", "GOT": "generate_got_subtasks", "error": "handle_error"}
        )
        graph.add_conditional_edges(
            "generate_cot_subtasks",
            self._route_success_or_error,
            {"success": "set_approved", "error": "handle_error"}  # Directly to approve for CoT
        )

        # Existing edges for GOT
        graph.add_conditional_edges(
            "generate_got_subtasks",
            self._route_success_or_error,
            {"success": "score_subtasks", "error": "handle_error"}
        )
        graph.add_conditional_edges(
            "score_subtasks",
            self._route_success_or_error,
            {"success": "merge_subtasks", "error": "handle_error"}
        )
        graph.add_conditional_edges(
            "merge_subtasks",
            self._route_success_or_error,
            {"success": "set_approved", "error": "handle_error"}
        )
        graph.add_conditional_edges(
            "set_approved",
            self._check_score,
            {"proceed": END, "review": "hitl_validation", "error": "handle_error"}
        )
        graph.add_conditional_edges(
            "hitl_validation",
            self._route_success_or_error,
            {"success": END, "error": "handle_error"}
        )
        graph.add_edge("handle_error", END)

        return graph.compile()

    def _route_success_or_error(self, state: Dict[str, Any]) -> str:
        """Route based on error state"""
        return "error" if state.get("error") else "success"

    def _check_score(self, state: Dict[str, Any]) -> str:
        """Check if score meets threshold"""
        if state.get("error"):
            return "error"
        score = state.get("overall_subtask_score", 0.0)
        return "proceed" if score >= self.score_threshold else "review"

    def _route_planning_method(self, state: Dict[str, Any]) -> str:
        """Route based on decided method"""
        method = state.get("planning_method")
        if method == "CoT":
            return "CoT"
        elif method == "GOT":
            return "GOT"
        else:
            return "error"  # Default to error/handle

    def _decide_planning_method_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Decide between CoT and GOT using LLM"""
        thread_id = state.get("thread_id", "unknown")
        content = state.get("content", "")
        context = state.get("context", {})
        logger.info(f"[CORE-PLANNER-{thread_id}] Deciding planning method...")

        try:
            # Convert to issue_data for consistency
            issue_data = {
                "key": context.get("identifier", "TASK-001"),
                "summary": context.get("title", "Task"),
                "description": content,
                **context
            }

            formatted_prompt = self.prompt_loader.format(
                "planner_decide_method",
                issue_key=issue_data.get('key'),
                summary=issue_data.get('summary'),
                description=issue_data.get('description')
            )

            from services.llm_service import call_llm  # Assume this is your LLM call
            response, tokens = call_llm(formatted_prompt, agent_name="planner")
            from tools.planner_tools import parse_json_from_text  # Reuse parser
            decision = parse_json_from_text(response)

            method = decision.get("method", "GOT")  # Default to GOT if invalid
            reasoning = decision.get("reasoning", "")

            logger.info(f"[CORE-PLANNER-{thread_id}] Decided on {method}: {reasoning}")

            # Log planning method choice to UI
            try:
                import core.router
                import uuid

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
                logger.warning(f"[CORE-PLANNER-{thread_id}] Failed to log planning method to UI: {e}")

            return {
                "planning_method": method,
                "tokens_used": state.get("tokens_used", 0) + tokens
            }
        except Exception as e:
            logger.error(f"[CORE-PLANNER-{thread_id}] Decision failed: {e}")
            return {"planning_method": "GOT", "error": str(e)}  # Default to GOT on error

    def _generate_cot_subtasks_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate subtasks using CoT"""
        thread_id = state.get("thread_id", "unknown")
        content = state.get("content", "")
        context = state.get("context", {})

        logger.info(f"[CORE-PLANNER-{thread_id}] Generating CoT subtasks...")

        try:
            from tools.planner_tools import generate_cot_subtasks

            issue_data = {
                "key": context.get("identifier", "TASK-001"),
                "summary": context.get("title", "Task"),
                "description": content,
                **context
            }

            result = generate_cot_subtasks.invoke({
                "issue_data": issue_data,
                "thread_id": thread_id
            })

            if result.get("success"):
                subtasks_list = result.get("subtasks_list", [])

                # Log each CoT subtask to terminal (similar to GoT)
                logger.info(f"[CORE-PLANNER-{thread_id}] Generated {len(subtasks_list)} CoT subtasks:")
                for subtask in subtasks_list:
                    logger.info(f"[CORE-PLANNER-{thread_id}] CoT Subtask {subtask['id']}: Priority {subtask.get('priority', 'N/A')} - {subtask['description']}")

                return {
                    "merged_subtasks": subtasks_list,
                    "overall_subtask_score": 10.0,  # High score since no scoring needed
                    "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
                }
            else:
                return {"error": result.get("error", "CoT subtask generation failed")}
        except Exception as e:
            logger.error(f"[CORE-PLANNER-{thread_id}] CoT generation failed: {e}")
            return {"error": str(e)}

    def _generate_got_subtasks_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate subtasks from content (GOT)"""
        thread_id = state.get("thread_id", "unknown")
        content = state.get("content", "")
        context = state.get("context", {})

        logger.info(f"[CORE-PLANNER-{thread_id}] Generating GOT subtasks...")

        try:
            from tools.planner_tools import generate_got_subtasks

            # Convert generic content to issue_data format for tool compatibility
            issue_data = {
                "key": context.get("identifier", "TASK-001"),
                "summary": context.get("title", "Task"),
                "description": content,
                **context  # Include any additional context
            }

            result = generate_got_subtasks.invoke({
                "issue_data": issue_data,
                "thread_id": thread_id
            })

            if result.get("success"):
                return {
                    "subtasks_graph": result.get("subtasks_graph"),
                    "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
                }
            else:
                return {"error": result.get("error", "GOT subtask generation failed")}

        except Exception as e:
            logger.error(f"[CORE-PLANNER-{thread_id}] GOT Generation failed: {e}")
            return {"error": str(e)}

    def _score_subtasks_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Score generated subtasks"""
        thread_id = state.get("thread_id", "unknown")
        subtasks_graph = state.get("subtasks_graph", {})
        content = state.get("content", "")
        context = state.get("context", {})

        logger.info(f"[CORE-PLANNER-{thread_id}] Scoring subtasks...")

        try:
            from tools.planner_tools import score_subtasks_with_llm

            result = score_subtasks_with_llm.invoke({
                "subtasks_graph": subtasks_graph,
                "requirements": {
                    "project_description": context.get("title", "Task"),
                    "requirements": [content],
                    "reasoning": "Derived from input content"
                },
                "thread_id": thread_id
            })

            if result.get("success"):
                scored_subtasks = result.get("scored_subtasks", [])
                overall = sum(s['score'] for s in scored_subtasks) / len(scored_subtasks) if scored_subtasks else 0.0

                for subtask in scored_subtasks:
                    logger.info(f"[CORE-PLANNER-{thread_id}] Subtask {subtask['id']}: Score {subtask['score']:.1f} - {subtask['description']}")

                return {
                    "scored_subtasks": scored_subtasks,
                    "overall_subtask_score": overall,
                    "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
                }
            else:
                return {"error": result.get("error", "Subtask scoring failed")}

        except Exception as e:
            logger.error(f"[CORE-PLANNER-{thread_id}] Scoring failed: {e}")
            return {"error": str(e)}

    def _merge_subtasks_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Merge subtasks into main tasks"""
        thread_id = state.get("thread_id", "unknown")
        scored_subtasks = state.get("scored_subtasks", [])
        content = state.get("content", "")

        logger.info(f"[CORE-PLANNER-{thread_id}] Merging subtasks...")

        try:
            from tools.planner_tools import merge_subtasks

            result = merge_subtasks.invoke({
                "scored_subtasks": scored_subtasks,
                "jira_description": content,
                "thread_id": thread_id
            })

            if result.get("success"):
                merged_subtasks = result.get("merged_subtasks", [])
                # Get the overall score from merge result
                overall_score = result.get("overall_score", 0.0)

                # If overall_score not in merge result, calculate it from merged subtasks
                if overall_score == 0.0 and merged_subtasks:
                    overall_score = sum(st.get('score', 0.0) for st in merged_subtasks) / len(merged_subtasks)

                logger.info(f"[CORE-PLANNER-{thread_id}] Merged {len(merged_subtasks)} subtasks, Overall Score: {overall_score:.1f}")

                # Log individual merged subtask scores
                for subtask in merged_subtasks:
                    logger.info(f"[CORE-PLANNER-{thread_id}] Merged Subtask {subtask['id']}: Score {subtask.get('score', 0.0):.1f} - {subtask['description'][:60]}...")

                return {
                    "merged_subtasks": merged_subtasks,
                    "overall_subtask_score": overall_score,  # Update the overall score
                    "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
                }
            else:
                return {"error": result.get("error", "Subtask merging failed")}

        except Exception as e:
            logger.error(f"[CORE-PLANNER-{thread_id}] Merging failed: {e}")
            return {"error": str(e)}

    def _set_approved_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Set approved subtasks for high-scoring tasks"""
        state["approved_subtasks"] = state.get("merged_subtasks", [])
        state["needs_human"] = False
        return state

    def _hitl_validation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Human-in-the-loop validation for low-scoring subtasks"""
        import queue
        from threading import Thread

        thread_id = state.get("thread_id", "unknown")
        score = state.get("overall_subtask_score", 0.0)

        logger.info(f"[CORE-PLANNER-{thread_id}] Score {score:.1f} < {self.score_threshold:.1f} - HITL required")

        q = queue.Queue()
        def get_input(q):
            try:
                resp = input(f"Approve subtasks (score {score:.1f}/{self.score_threshold:.1f})? (Y/N) [default Y]: ").strip().upper() or "Y"
                q.put(resp)
            except EOFError:
                q.put("Y")

        thread = Thread(target=get_input, args=(q,))
        thread.start()
        thread.join(self.hitl_timeout)

        if thread.is_alive():
            approval = "Y"
            logger.info(f"[CORE-PLANNER-{thread_id}] HITL timeout - auto-approving")
        else:
            approval = q.get()

        if approval == "Y":
            state["approved_subtasks"] = state.get("merged_subtasks", [])
            state["needs_human"] = False
        else:
            state["needs_human"] = True
            state["human_decision"] = "reject"
            state["error"] = "Subtasks rejected by human"

        return state

    def _handle_error_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors in the workflow"""
        thread_id = state.get("thread_id", "unknown")
        error = state.get("error", "Unknown error")
        logger.error(f"[CORE-PLANNER-{thread_id}] Error: {error}")
        state["needs_human"] = True
        return state

    # ==================== PUBLIC API ====================

    def plan(self, content: str, context: Optional[Dict[str, Any]] = None, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main planning method - accepts any content and returns subtasks

        Args:
            content: The requirement/description to plan (can be JIRA, user story, etc.)
            context: Additional context (project info, identifier, title, etc.)
            thread_id: Optional thread identifier for logging

        Returns:
            {
                "success": bool,
                "subtasks": List[Dict],  # Approved subtasks
                "score": float,
                "tokens_used": int,
                "needs_human": bool,
                "error": Optional[str],
                "planning_method": str  # NEW: For logging/tracking
            }
        """
        import threading

        if thread_id is None:
            thread_id = f"PLANNER-{threading.current_thread().ident}"

        context = context or {}
        start_time = datetime.now()

        logger.info(f"[CORE-PLANNER-{thread_id}] Starting planning for content")

        try:
            # Initialize state
            initial_state = {
                "content": content,
                "context": context,
                "thread_id": thread_id,
                "planning_method": None,  # NEW
                "subtasks_graph": None,
                "scored_subtasks": [],
                "merged_subtasks": [],
                "approved_subtasks": [],
                "overall_subtask_score": 0.0,
                "needs_human": False,
                "human_decision": None,
                "error": "",
                "tokens_used": 0
            }

            # Execute workflow
            final_state = self.graph.invoke(initial_state)

            duration = (datetime.now() - start_time).total_seconds()

            if final_state.get("error"):
                logger.error(f"[CORE-PLANNER-{thread_id}] Planning failed: {final_state.get('error')}")
                return {
                    "success": False,
                    "error": final_state.get("error"),
                    "needs_human": final_state.get("needs_human", False),
                    "tokens_used": final_state.get("tokens_used", 0),
                    "subtasks": [],
                    "planning_method": final_state.get("planning_method", "Unknown")
                }

            logger.info(f"[CORE-PLANNER-{thread_id}] Planning completed in {duration:.1f}s")

            return {
                "success": True,
                "subtasks": final_state.get("approved_subtasks", []),
                "score": final_state.get("overall_subtask_score", 0.0),
                "tokens_used": final_state.get("tokens_used", 0),
                "needs_human": final_state.get("needs_human", False),
                "error": None,
                "planning_method": final_state.get("planning_method", "Unknown")
            }

        except Exception as e:
            logger.error(f"[CORE-PLANNER-{thread_id}] Planning execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "needs_human": True,
                "tokens_used": 0,
                "subtasks": [],
                "planning_method": "Unknown"
            }

    def create_langgraph_node(self):
        """
        Returns a LangGraph node function that can be added to any workflow

        Usage in another workflow:
            planner = CorePlannerAgent(config)
            workflow.add_node("planning", planner.create_langgraph_node())
        """
        def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """LangGraph node wrapper for core planner"""
            content = state.get("content") or state.get("description") or state.get("requirements", "")
            context = state.get("context", {})
            thread_id = state.get("thread_id", "unknown")

            result = self.plan(content=content, context=context, thread_id=thread_id)

            # Update state with planning results
            return {
                "planning_result": result,
                "approved_subtasks": result.get("subtasks", []),
                "planner_tokens": result.get("tokens_used", 0),
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0),
                "error": result.get("error") if not result.get("success") else state.get("error"),
                "planning_method": result.get("planning_method")  # NEW
            }

        return planner_node