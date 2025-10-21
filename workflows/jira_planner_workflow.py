"""
JIRA-Specific Planner Workflow
This file contains JIRA-specific integration logic that uses the CorePlannerAgent.
It handles:
- JIRA issue data extraction
- MongoDB storage for JIRA issues
- UI integration for JIRA workflow
- Performance tracking specific to JIRA

This keeps JIRA-specific logic separate from the core planning logic.
"""
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import MongoClient

from agents.core_planner_agent import CorePlannerAgent
from config.settings import config as app_config

logger = logging.getLogger(__name__)


class JiraPlannerWorkflow:
    """
    JIRA-specific workflow wrapper for CorePlannerAgent
    Handles JIRA issue processing, MongoDB storage, and UI integration
    """

    def __init__(self, config):
        self.config = config
        self.core_planner = CorePlannerAgent(config)

        # Initialize MongoDB for JIRA-specific storage
        self.mongo_client = None
        self.mongo_collection = None
        self._initialize_mongodb()

        logger.debug("JIRA Planner Workflow initialized")

    def _initialize_mongodb(self):
        """Initialize MongoDB connection for JIRA feedback storage"""
        try:
            conn_str = app_config.MONGODB_CONNECTION_STRING
            if not conn_str:
                logger.warning("MONGODB_CONNECTION_STRING not set - JIRA feedback storage disabled")
                return

            self.mongo_client = MongoClient(conn_str)
            # Use MONGODB_PERFORMANCE_DATABASE and MONGODB_AGENT_PERFORMANCE
            db_name = app_config.MONGODB_PERFORMANCE_DATABASE
            coll_name = app_config.MONGODB_AGENT_PERFORMANCE
            db = self.mongo_client[db_name]
            self.mongo_collection = db[coll_name]

            logger.debug(f"JIRA Planner MongoDB ready - Database: {db_name}, Collection: {coll_name}")
        except Exception as e:
            logger.error(f"JIRA Planner MongoDB init failed: {e}")
            self.mongo_collection = None

    def _store_to_mongodb(self, issue_key: str, subtasks: list, model: str, description: str,
                          score: float, tokens_used: int):
        """Store JIRA-specific planning data to MongoDB"""
        if self.mongo_collection is None:
            logger.warning("MongoDB not available - Skipping JIRA planner storage")
            return

        try:
            document = {
                "agent_type": "planner",
                "issue_key": issue_key,
                "subtasks": subtasks,
                "timestamp": datetime.now(),
                "date": datetime.now().date().isoformat(),
                "llm_model": model,
                "creation_description": description,
                "overall_score": score,
                "tokens_used": tokens_used
            }

            result = self.mongo_collection.insert_one(document)
            logger.info(f"[JIRA-PLANNER] Stored data for {issue_key} in MongoDB: ID {result.inserted_id}")
        except Exception as e:
            logger.error(f"[JIRA-PLANNER] Failed to store in MongoDB: {e}")

    def _log_to_ui(self, issue_key: str, subtasks: list, score: float):
        """Log planning results to UI with detailed score information"""
        try:
            import core.router
            import uuid

            # Prepare detailed subtask information with scores
            subtask_details = []
            for subtask in subtasks:
                subtask_details.append({
                    "id": subtask.get("id"),
                    "description": subtask.get("description", ""),
                    "score": round(subtask.get("score", 0.0), 1),
                    "priority": subtask.get("priority", 0),
                    "score_reasoning": subtask.get("score_reasoning", "")
                })

            # Get threshold from config
            threshold = app_config.GOT_SCORE_THRESHOLD

            # Determine status based on score
            status = "success" if score >= threshold else "warning"

            core.router.safe_activity_log({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "agent": "PlannerAgent",
                "action": "Planning Completed",
                "details": f"Generated {len(subtasks)} subtasks for {issue_key} | Overall Score: {score:.1f}/{threshold:.1f}",
                "status": status,
                "issueId": issue_key,
                "subtasks": subtask_details,
                "subtaskCount": len(subtasks),
                "overallScore": round(score, 1),
                "scoreThreshold": threshold,
                "individualScores": [st.get("score", 0.0) for st in subtasks],
                "averageScore": round(score, 1)
            })

            logger.info(f"[JIRA-PLANNER] UI Log: {issue_key} - {len(subtasks)} subtasks, Overall Score: {score:.1f}/{threshold:.1f}")
        except Exception as e:
            logger.warning(f"[JIRA-PLANNER] Failed to log to UI: {e}")

    def plan_jira_issue(self, issue_data: Dict[str, Any], thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process JIRA issue planning using CorePlannerAgent

        Args:
            issue_data: JIRA issue data containing key, summary, description, etc.
            thread_id: Optional thread identifier

        Returns:
            {
                "success": bool,
                "approved_subtasks": List[Dict],
                "needs_human": bool,
                "tokens_used": int,
                "error": Optional[str]
            }
        """
        if not thread_id:
            thread_id = f"JIRA-PLANNER-{threading.current_thread().ident}"

        issue_key = issue_data.get('key', 'UNKNOWN')
        start_time = datetime.now()

        logger.info(f"[JIRA-PLANNER-{thread_id}] Starting planning for JIRA issue {issue_key}")

        try:
            # Extract JIRA-specific data
            content = issue_data.get('description', '')
            context = {
                "identifier": issue_key,
                "title": issue_data.get('summary', ''),
                "project": issue_data.get('project', {}),
                "priority": issue_data.get('priority', ''),
                "issue_type": issue_data.get('issuetype', ''),
                # Include any additional JIRA fields
                **{k: v for k, v in issue_data.items() if k not in ['description', 'key', 'summary']}
            }

            # Call core planner
            result = self.core_planner.plan(
                content=content,
                context=context,
                thread_id=thread_id
            )

            duration = (datetime.now() - start_time).total_seconds()

            if result.get("success"):
                subtasks = result.get("subtasks", [])
                score = result.get("score", 0.0)
                tokens = result.get("tokens_used", 0)

                # Store to MongoDB (JIRA-specific)
                self._store_to_mongodb(
                    issue_key=issue_key,
                    subtasks=subtasks,
                    model=app_config.PLANNER_LLM_MODEL or "unknown",
                    description=content,
                    score=score,
                    tokens_used=tokens
                )

                # Log to UI (JIRA-specific)
                self._log_to_ui(issue_key, subtasks, score)

                logger.info(f"[JIRA-PLANNER-{thread_id}] Completed for {issue_key} in {duration:.1f}s")

                return {
                    "success": True,
                    "approved_subtasks": subtasks,
                    "needs_human": result.get("needs_human", False),
                    "tokens_used": tokens
                }
            else:
                logger.error(f"[JIRA-PLANNER-{thread_id}] Planning failed for {issue_key}: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error"),
                    "needs_human": result.get("needs_human", False),
                    "tokens_used": result.get("tokens_used", 0)
                }

        except Exception as e:
            logger.error(f"[JIRA-PLANNER-{thread_id}] Exception for {issue_key}: {e}")
            return {
                "success": False,
                "error": str(e),
                "needs_human": True,
                "tokens_used": 0
            }

    def create_langgraph_node(self):
        """
        Returns a LangGraph node function for JIRA workflow integration

        Usage:
            jira_planner = JiraPlannerWorkflow(config)
            workflow.add_node("plan_issue", jira_planner.create_langgraph_node())
        """
        def jira_planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """LangGraph node wrapper for JIRA planner"""
            issue_data = state.get("current_issue", {})
            thread_id = state.get("thread_id", "unknown")

            result = self.plan_jira_issue(issue_data=issue_data, thread_id=thread_id)

            return {
                "planning_result": result,
                "approved_subtasks": result.get("approved_subtasks", []),
                "planner_tokens": result.get("tokens_used", 0),
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0),
                "error": result.get("error") if not result.get("success") else state.get("error"
                )
            }

        return jira_planner_node
