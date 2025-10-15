"""
Planner Agent - Backward Compatible Wrapper
This file maintains backward compatibility with the existing project.
It now uses the modular CorePlannerAgent and JiraPlannerWorkflow internally.

IMPORTANT: This file is kept for backward compatibility.
For new workflows, use CorePlannerAgent directly from agents.core_planner_agent
"""
import logging
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Import the new modular components
from agents.core_planner_agent import CorePlannerAgent
from workflows.jira_planner_workflow import JiraPlannerWorkflow

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    LangGraph-based Planner Agent (Backward Compatible Wrapper)

    This class now delegates to:
    - CorePlannerAgent: Core planning logic (reusable)
    - JiraPlannerWorkflow: JIRA-specific integration
    """

    def __init__(self, config):
        self.config = config
        self.config.GOT_SCORE_THRESHOLD = float(os.getenv("GOT_SCORE_THRESHOLD", "7.0"))
        self.config.HITL_TIMEOUT_SECONDS = int(os.getenv("HITL_TIMEOUT_SECONDS", "30"))

        # Initialize modular components
        self.core_planner = CorePlannerAgent(config)
        self.jira_workflow = JiraPlannerWorkflow(config)

        # For backward compatibility - expose the graph
        self.graph = self.jira_workflow.core_planner.graph

        # Legacy attributes for compatibility
        from tools.prompt_loader import PromptLoader
        from tools.planner_tools import generate_got_subtasks, score_subtasks_with_llm, merge_subtasks, perform_hitl_validation

        self.prompt_loader = PromptLoader("prompts")
        self.tools = [
            generate_got_subtasks,
            score_subtasks_with_llm,
            merge_subtasks,
            perform_hitl_validation
        ]

        logger.info("Planner Agent initialized (using modular architecture)")

    @staticmethod
    def _store_to_mongodb(issue_key: str, subtasks: Dict, model: str, description: str,
                          scores: Optional[List] = None, tokens_used: int = 0):
        """
        Legacy MongoDB storage method - kept for backward compatibility
        Now delegates to JiraPlannerWorkflow
        """
        load_dotenv()
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        if not conn_str:
            logger.warning("MongoDB not available - Skipping planner feedback storage")
            return

        try:
            from pymongo import MongoClient

            mongo_client = MongoClient(conn_str)
            db_name = os.getenv("MONGODB_PERFORMANCE_DATABASE", "aristotle_performance")
            coll_name = os.getenv("MONGODB_AGENT_PERFORMANCE", "agent_performance")
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
                "agent_type": "planner",
                "issue_key": issue_key,
                "subtasks": subtasks_list,
                "timestamp": datetime.now(),
                "date": datetime.now().date().isoformat(),
                "llm_model": model,
                "creation_description": description,
                "overall_score": sum(s.get("score", 0) for s in subtasks_list) / len(subtasks_list) if subtasks_list and scores else None,
                "tokens_used": tokens_used
            }

            result = mongo_collection.insert_one(document)
            logger.info(f"[PLANNER] Stored data for {issue_key} in MongoDB: ID {result.inserted_id}")
        except Exception as e:
            logger.error(f"[PLANNER] Failed to store feedback in MongoDB: {e}")

    def plan_issue(self, issue_data: Dict[str, Any], thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process issue planning using modular workflow (Backward Compatible)

        This method maintains the exact same interface as before but uses
        the new modular architecture internally.
        """
        if not thread_id:
            thread_id = f"PLANNER-{threading.current_thread().ident}"

        # Delegate to JIRA workflow
        result = self.jira_workflow.plan_jira_issue(issue_data, thread_id)

        # Log planning method for debugging (new)
        logger.info(f"[PLANNER-{thread_id}] Used planning method: {result.get('planning_method', 'Unknown')}")

        # Return in the same format as before for backward compatibility
        return result