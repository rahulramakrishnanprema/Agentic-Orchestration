"""
JIRA-Specific Reviewer Workflow
This file contains JIRA-specific integration logic that uses the CoreReviewerAgent.
It handles:
- JIRA issue data extraction
- MongoDB storage for JIRA issues
- UI integration for JIRA workflow
- Performance tracking specific to JIRA
- Review queue management for parallel processing

This keeps JIRA-specific logic separate from the core review logic.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

from agents.core_reviewer_agent import CoreReviewerAgent
from config.settings import config as app_config

logger = logging.getLogger(__name__)


class JiraReviewerWorkflow:
    """
    JIRA-specific workflow wrapper for CoreReviewerAgent
    Handles JIRA issue processing, queue management, and UI integration
    """

    def __init__(self, config):
        self.config = config
        self.core_reviewer = CoreReviewerAgent(config)

        logger.debug("JIRA Reviewer Workflow initialized")

    def _log_to_ui(self, issue_key: str, score: float, approved: bool, thread_id: str):
        """Log review results to UI"""
        try:
            import core.router
            import uuid

            status = "success" if approved else "warning"
            threshold = app_config.REVIEW_THRESHOLD

            core.router.safe_activity_log({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "agent": "ReviewerAgent",
                "action": "Code Review Completed",
                "details": f"Review score: {score:.1f}% (Threshold: {threshold:.1f}%) - {'APPROVED' if approved else 'NEEDS_IMPROVEMENT'}",
                "status": status,
                "issueId": issue_key,
                "score": round(score, 1),
                "threshold": threshold,
                "approved": approved,
                "threadId": thread_id
            })

            logger.info(f"[JIRA-REVIEWER] UI Log: {issue_key} - Score: {score:.1f}%, Approved: {approved}")
        except Exception as e:
            logger.warning(f"[JIRA-REVIEWER] Failed to log to UI: {e}")

    def review_jira_issue_code(
        self,
        issue_key: str,
        files: Dict[str, str],
        file_types: List[str],
        project_description: str,
        iteration: int = 1,
        thread_id: Optional[str] = None,
        review_queue: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Review code for a JIRA issue using CoreReviewerAgent

        Args:
            issue_key: JIRA issue key
            files: Dictionary of filename -> code content
            file_types: List of file types being reviewed
            project_description: Description of the project
            iteration: Review iteration number
            thread_id: Optional thread identifier
            review_queue: Optional queue to consume files from (for parallel processing)

        Returns:
            {
                "success": bool,
                "overall_score": float,
                "approved": bool,
                "issues": List[str],
                "tokens_used": int,
                "processing_time": float,
                ...
            }
        """
        if not thread_id:
            thread_id = f"JIRA-REVIEWER-{threading.current_thread().ident}"

        # Handle review queue if provided (parallel processing)
        if review_queue is not None:
            try:
                logger.info(f"[{thread_id}] Waiting for files from review queue...")
                queue_data = review_queue.get(timeout=300)  # 5 min timeout
                files = queue_data.get("files", files)
                issue_data = queue_data.get("issue_data", {})
                issue_key = issue_data.get("key", issue_key)
                project_description = issue_data.get("summary", project_description)
                retrieved_thread_id = queue_data.get("thread_id", thread_id)
                logger.info(f"[{thread_id}] Retrieved {len(files)} files from queue for parallel review (original thread: {retrieved_thread_id})")
            except Exception as e:
                logger.warning(f"[{thread_id}] Failed to get from review queue: {e}, using provided files")

        start_time = time.time()

        try:
            logger.info(f"[{thread_id}] Starting JIRA review for {issue_key} (Iteration {iteration})...")

            # Prepare context with JIRA-specific data
            context = {
                "identifier": issue_key,
                "project_description": project_description,
                "file_types": file_types,
                "iteration": iteration,
                "threshold": getattr(self.config, 'REVIEW_THRESHOLD', 70.0)
            }

            # Call core reviewer (without queue - handled externally)
            result = self.core_reviewer.review(
                files=files,
                context=context,
                thread_id=thread_id
            )

            processing_time = time.time() - start_time

            if not result.get("success"):
                logger.error(f"[{thread_id}] Review failed for {issue_key}: {result.get('error')}")
                return {
                    **result,
                    "iteration": iteration,
                    "thread_id": thread_id,
                    "processing_time": processing_time,
                    "langgraph_workflow_used": True,
                    "knowledge_base_used": True
                }

            # JIRA-specific post-processing
            score = result.get("overall_score", 0.0)
            approved = result.get("approved", False)

            self._log_to_ui(issue_key, score, approved, thread_id)

            elapsed_time = time.time() - start_time
            logger.info(f"[{thread_id}] Completed {issue_key} in {elapsed_time:.2f}s - Score: {score:.1f}%, Approved: {approved}")

            # Return formatted results with JIRA-specific fields
            return {
                **result,
                "iteration": iteration,
                "thread_id": thread_id,
                "processing_time": processing_time,
                "langgraph_workflow_used": True,
                "knowledge_base_used": True,
                "simplified_workflow": True
            }

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[{thread_id}] JIRA review failed for {issue_key}: {e}")

            return {
                "success": False,
                "error": str(e),
                "overall_score": 0.0,
                "threshold": getattr(self.config, 'REVIEW_THRESHOLD', 70.0),
                "approved": False,
                "issues": [f"Review process failed: {e}"],
                "tokens_used": 0,
                "mongodb_stored": False,
                "iteration": iteration,
                "thread_id": thread_id,
                "processing_time": processing_time,
                "langgraph_workflow_used": True
            }

    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get comprehensive workflow statistics"""
        from tools.reviewer_tool import get_reviewer_tools_stats

        core_stats = self.core_reviewer.get_review_stats()
        tool_stats = get_reviewer_tools_stats()

        return {
            "module_type": "jira_reviewer_workflow",
            "version": "2.0_modular",
            "workflow_stats": core_stats,
            "tool_stats": tool_stats,
            "workflow_features": [
                "modular_architecture",
                "core_reviewer_integration",
                "jira_specific_processing",
                "parallel_queue_support",
                "ui_integration",
                "mongodb_persistence",
                "multi_dimensional_analysis",
                "knowledge_base_integration"
            ]
        }
