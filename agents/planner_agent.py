# Updated agents/planner_agent.py
"""
Planner Agent - LangGraph Sub-graph for Planning Phase
Handles:
- Collect and normalize task description
- Generate initial GOT plan with detailed thoughts
- Score subtasks
- Merge into three main subtasks covering complete JIRA description
- HITL validation if low score
Outputs approved subtasks
"""
import logging
import os
import queue
import threading
from datetime import datetime
from threading import Thread
from typing import Dict, Any, List, Optional, TypedDict
from dotenv import load_dotenv
from pymongo import MongoClient
from tools.planner_tools import generate_got_subtasks, score_subtasks_with_llm, merge_subtasks, perform_hitl_validation
from tools.prompt_loader import PromptLoader
from graph.planner_graph import build_planner_graph, PlannerState

logger = logging.getLogger(__name__)


class PlannerAgent:
    """LangGraph-based Planner Agent"""

    def __init__(self, config):
        self.config = config
        self.config.GOT_SCORE_THRESHOLD = float(os.getenv("GOT_SCORE_THRESHOLD", "7.0"))
        self.config.HITL_TIMEOUT_SECONDS = int(os.getenv("HITL_TIMEOUT_SECONDS", "30"))
        self.prompt_loader = PromptLoader("prompts")
        # Updated tools - added merge_subtasks
        self.tools = [
            generate_got_subtasks,
            score_subtasks_with_llm,
            merge_subtasks,
            perform_hitl_validation
        ]
        # NEW: Initialize MongoDB
        load_dotenv()
        self.mongo_client = None
        self.mongo_collection = None
        self._initialize_mongodb()
        # Initialize LangGraph sub-graph
        self.graph = build_planner_graph()
        logger.info("Planner Agent initialized")

    def _initialize_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            conn_str = os.getenv("MONGODB_CONNECTION_STRING")
            if not conn_str:
                logger.warning("MONGODB_CONNECTION_STRING not set - Planner feedback storage disabled")
                return
            self.mongo_client = MongoClient(conn_str)
            db_name = os.getenv("MONGODB_DATABASE", "code_review")
            coll_name = os.getenv("PLANNER_FEEDBACK", "planner-feedback")
            db = self.mongo_client[db_name]
            self.mongo_collection = db[coll_name]
            logger.info(f"Planner MongoDB ready - Collection: {coll_name}")
        except Exception as e:
            logger.error(f"Planner MongoDB init failed: {e}")
            self.mongo_collection = None

    @staticmethod
    def _store_to_mongodb(issue_key: str, subtasks: Dict, model: str, description: str, scores: Optional[List] = None, tokens_used: int = 0):
        """Store subtasks and scores in MongoDB"""
        load_dotenv() # Ensure env is loaded
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        if not conn_str:
            logger.warning("MongoDB not available - Skipping planner feedback storage")
            return
        try:
            mongo_client = MongoClient(conn_str)
            db_name = os.getenv("MONGODB_DATABASE", "code_review")
            coll_name = os.getenv("PLANNER_FEEDBACK", "planner-feedback")
            mongo_collection = mongo_client[db_name][coll_name]
            # Prepare subtasks list
            subtasks_list = []
            for node_id, node_data in subtasks.items():
                subtask = {
                    "id": int(node_id),
                    "description": node_data.get("description", ""),
                    "priority": node_data.get("priority", 0),
                    "requirements_covered": node_data.get("requirements_covered", []),
                    "reasoning": node_data.get("reasoning", ""),
                    "score": None,
                    "score_reasoning": ""
                }
                if scores:
                    for scored in scores:
                        if scored["id"] == subtask["id"]:
                            subtask["score"] = scored.get("score")
                            subtask["score_reasoning"] = scored.get("reasoning", "")
                            break
                subtasks_list.append(subtask)
            document = {
                "issue_key": issue_key,
                "subtasks": subtasks_list,
                "model_name": model,
                "creation_description": description,
                "timestamp": datetime.now().isoformat(),
                "overall_score": sum(s.get("score", 0) for s in subtasks_list) / len(subtasks_list) if subtasks_list and scores else None,
                "tokens_used": tokens_used
            }
            result = mongo_collection.insert_one(document)
            logger.info(f"[PLANNER] Stored feedback for {issue_key} in MongoDB: ID {result.inserted_id}")
        except Exception as e:
            logger.error(f"[PLANNER] Failed to store feedback in MongoDB: {e}")

    def plan_issue(self, issue_data: Dict[str, Any], thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Process issue planning using LangGraph workflow"""
        if not thread_id:
            thread_id = f"PLANNER-{threading.current_thread().ident}"
        start_time = datetime.now()
        issue_key = issue_data.get('key', 'UNKNOWN')
        try:
            logger.info(f"[PLANNER-{thread_id}] Starting planning workflow for issue {issue_key}")
            # Initialize state
            initial_state = PlannerState(
                issue_data=issue_data,
                thread_id=thread_id,
                subtasks_graph=None,
                scored_subtasks=[],
                approved_subtasks=[],
                overall_subtask_score=0.0,
                needs_human=False,
                human_decision=None,
                error="",
                tokens_used=0
            )
            # Execute workflow
            final_state = self.graph.invoke(initial_state)
            duration = (datetime.now() - start_time).total_seconds()
            if final_state.get("error"):
                logger.error(f"[PLANNER-{thread_id}] Planning failed for {issue_key}: {final_state.get('error')}")
                return {
                    "success": False,
                    "error": final_state.get("error"),
                    "needs_human": final_state.get("needs_human", False),
                    "tokens_used": final_state.get("tokens_used", 0)
                }
            logger.info(f"[PLANNER-{thread_id}] Planning completed for {issue_key} in {duration:.1f}s")
            return {
                "success": True,
                "approved_subtasks": final_state.get("approved_subtasks", []),
                "needs_human": final_state.get("needs_human", False),
                "tokens_used": final_state.get("tokens_used", 0)
            }
        except Exception as e:
            logger.error(f"[PLANNER-{thread_id}] Planning execution failed for {issue_key}: {e}")
            return {
                "success": False,
                "error": str(e),
                "needs_human": True,
                "tokens_used": 0
            }