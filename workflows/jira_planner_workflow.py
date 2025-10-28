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
from typing import Dict, Any, Optional, List
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

    def _generate_issue_summary_and_description(self, subtask: Dict[str, Any], thread_id: str) -> Dict[str, str]:
        """
        Use LLM to generate a concise summary. Description is the full subtask content.

        Args:
            subtask: Subtask dictionary with description
            thread_id: Thread identifier

        Returns:
            {"summary": str, "description": str}
        """
        from services.llm_service import LLMService
        from tools.prompt_loader import PromptLoader

        # Get subtask details
        subtask_desc = subtask.get('description', '')
        subtask_reasoning = subtask.get('score_reasoning', '')

        # Description is just the full subtask content
        description = subtask_desc
        if subtask_reasoning and subtask_reasoning != 'No additional details':
            description += f"\n\n{subtask_reasoning}"

        try:
            logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Generating summary via LLM...")

            # Format prompt
            prompt_loader = PromptLoader("prompts")
            formatted_prompt = prompt_loader.format(
                "issue_summary_generation",
                subtask_description=subtask_desc,
                subtask_reasoning='',
                priority=''
            )

            # Call LLM for summary only
            llm_service = LLMService(
                api_key=app_config.PLANNER_LLM_KEY,
                api_url=app_config.PLANNER_LLM_URL,
                model=app_config.PLANNER_LLM_MODEL,
                temperature=app_config.PLANNER_LLM_TEMPERATURE,
                max_tokens=app_config.PLANNER_LLM_MAX_TOKENS
            )

            response = llm_service.chat_completion(
                messages=[{"role": "user", "content": formatted_prompt}]
            )

            content = response.get('content', '').strip()

            # LLM outputs only the title (no prefix)
            summary = content.split('\n')[0].strip()[:255]  # First line only

            logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Summary: {summary}")

            return {"summary": summary, "description": description}

        except Exception as e:
            logger.error(f"[JIRA-PROJECT-CREATOR-{thread_id}] LLM failed: {e}")
            # Fallback: use first few words of subtask as summary
            words = subtask_desc.split()[:6]
            summary = ' '.join(words) if words else subtask_desc[:100]
            return {"summary": summary, "description": description}

    def create_project_from_subtasks(self, issue_data: Dict[str, Any], subtasks: List[Dict[str, Any]],
                                     thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new JIRA project from subtasks or add tasks to existing project.
        If project already exists, adds tasks to it instead of creating new one.

        Args:
            issue_data: Original JIRA issue data
            subtasks: List of approved subtasks
            thread_id: Optional thread identifier

        Returns:
            {
                "success": bool,
                "project_key": str,
                "created_issues": List[str],
                "error": Optional[str]
            }
        """
        from tools.jira_client import get_jira_client, create_jira_project_mcp_tool, create_jira_issue_mcp_tool

        if not thread_id:
            thread_id = f"JIRA-PROJECT-CREATOR-{threading.current_thread().ident}"

        issue_key = issue_data.get('key', 'UNKNOWN')
        issue_summary = issue_data.get('summary', 'Project')

        logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Processing {len(subtasks)} subtasks from {issue_key}")

        try:
            # Generate project key from summary
            words = issue_summary.upper().split()
            meaningful_words = [w for w in words if w not in ['THE', 'A', 'AN', 'AND', 'OR', 'FOR', 'TO', 'OF', 'IN', 'ON']]

            if len(meaningful_words) >= 2:
                project_key = ''.join([w[0] for w in meaningful_words[:4]])
            elif len(meaningful_words) == 1:
                project_key = meaningful_words[0][:4]
            else:
                project_key = ''.join([c for c in issue_summary.upper() if c.isalnum()])[:4]

            if len(project_key) < 2:
                project_key = project_key + "PR"
            project_key = project_key[:10]

            project_name = issue_summary

            # Check if project already exists
            logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Checking if project {project_key} exists...")

            try:
                jira = get_jira_client()
                existing_project = jira.project(project_key)

                # Project exists! Add tasks to it
                logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Project {project_key} already exists. Adding tasks to existing project.")
                created_project_key = project_key

            except Exception as e:
                # Project doesn't exist, create it
                logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Project doesn't exist. Creating new project: {project_name} ({project_key})")

                project_description = f"Auto-generated project from issue {issue_key}\n\n{issue_data.get('description', '')}"

                project_result = create_jira_project_mcp_tool(
                    project_name=project_name,
                    project_key=project_key,
                    description=project_description,
                    thread_id=thread_id
                )

                if not project_result.get('success'):
                    logger.error(f"[JIRA-PROJECT-CREATOR-{thread_id}] Failed to create project: {project_result.get('error')}")
                    return {
                        "success": False,
                        "error": f"Project creation failed: {project_result.get('error')}"
                    }

                created_project_key = project_result.get('project_key')
                logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Project created successfully: {created_project_key}")

            # Create issues for each subtask with LLM-generated summaries and descriptions
            created_issues = []
            for idx, subtask in enumerate(subtasks, 1):
                logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Processing subtask {idx}/{len(subtasks)}...")

                # Use LLM to generate proper summary and description
                generated = self._generate_issue_summary_and_description(subtask, thread_id)

                subtask_summary = generated["summary"]
                subtask_description = generated["description"]

                logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Creating issue {idx}/{len(subtasks)}: {subtask_summary[:50]}...")
                issue_result = create_jira_issue_mcp_tool(
                    project_key=created_project_key,
                    summary=subtask_summary,
                    description=subtask_description,
                    issue_type="Task",
                    thread_id=thread_id
                )

                if issue_result.get('success'):
                    created_issues.append(issue_result.get('issue_key'))
                    logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Created issue: {issue_result.get('issue_key')}")
                else:
                    logger.warning(f"[JIRA-PROJECT-CREATOR-{thread_id}] Failed to create issue {idx}: {issue_result.get('error')}")

            logger.info(f"[JIRA-PROJECT-CREATOR-{thread_id}] Project setup complete. Created {len(created_issues)}/{len(subtasks)} issues")

            # Log to UI
            import core.router
            import uuid
            core.router.safe_activity_log({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "agent": "PlannerAgent",
                "action": "Project Created",
                "details": f"Created new project {created_project_key} with {len(created_issues)} issues from {issue_key}",
                "status": "success",
                "issueId": issue_key,
                "newProjectKey": created_project_key,
                "createdIssues": created_issues
            })

            return {
                "success": True,
                "project_key": created_project_key,
                "project_name": project_name,
                "created_issues": created_issues,
                "total_issues": len(created_issues)
            }

        except Exception as e:
            logger.error(f"[JIRA-PROJECT-CREATOR-{thread_id}] Exception: {e}")
            return {
                "success": False,
                "error": str(e)
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
