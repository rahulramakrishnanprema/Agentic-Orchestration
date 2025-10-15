"""
Reviewer Agent - Backward Compatible Wrapper
This file maintains backward compatibility with the existing project.
It now uses the modular CoreReviewerAgent and JiraReviewerWorkflow internally.

IMPORTANT: This file is kept for backward compatibility.
For new workflows, use CoreReviewerAgent directly from agents.core_reviewer_agent
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from threading import Lock

# Import the new modular components
from agents.core_reviewer_agent import CoreReviewerAgent
from workflows.jira_reviewer_workflow import JiraReviewerWorkflow

logger = logging.getLogger(__name__)

# Thread-safe locks
workflow_lock = Lock()
stats_lock = Lock()


class SimplifiedReviewer:
    """
    Simplified Reviewer (Backward Compatible Wrapper)

    This class now delegates to:
    - CoreReviewerAgent: Core review logic (reusable)
    - JiraReviewerWorkflow: JIRA-specific integration
    """

    def __init__(self, config):
        """Initialize the simplified reviewer module."""
        self.config = config

        # Initialize modular components
        self.core_reviewer = CoreReviewerAgent(config)
        self.jira_workflow = JiraReviewerWorkflow(config)

        # For backward compatibility - expose the workflow and tools
        self.workflow = self.core_reviewer.graph

        # Legacy attributes for compatibility
        from tools.prompt_loader import PromptLoader
        from tools.reviewer_tool import (
            format_files_for_review, get_knowledge_base_content, analyze_code_completeness,
            analyze_code_security, analyze_coding_standards, calculate_review_scores,
            store_review_in_mongodb, analyze_python_code_with_pylint
        )

        self.prompt_loader = PromptLoader("prompts")
        self.tools = [
            format_files_for_review,
            get_knowledge_base_content,
            analyze_code_completeness,
            analyze_code_security,
            analyze_coding_standards,
            calculate_review_scores,
            store_review_in_mongodb,
            analyze_python_code_with_pylint
        ]

        # Statistics tracking - delegate to core reviewer
        self.workflow_stats = self.core_reviewer.review_stats

        logger.info("Simplified LangGraph Reviewer Agent initialized (using modular architecture)")

    def review_generated_code_with_langgraph(self, issue_key: str, files: Dict[str, str],
                                           file_types: List[str], project_description: str,
                                           iteration: int = 1, thread_id: Optional[str] = None,
                                           review_queue: Optional[Any] = None) -> Dict[str, Any]:
        """
        Main review processing method using simplified LangGraph workflow.
        (Backward compatible method - now uses modular architecture)

        Args:
            issue_key: Issue identifier
            files: Dictionary of filename -> code content
            file_types: List of file types being reviewed
            project_description: Description of the project
            iteration: Review iteration number
            thread_id: Optional thread identifier
            review_queue: Optional queue to consume files from (for parallel processing)
        """
        if not thread_id:
            thread_id = str(threading.current_thread().ident)[-6:]

        try:
            # Use JIRA workflow for issue-based reviews
            result = self.jira_workflow.review_jira_issue_code(
                issue_key=issue_key,
                files=files,
                file_types=file_types,
                project_description=project_description,
                iteration=iteration,
                thread_id=thread_id,
                review_queue=review_queue
            )

            # Update local stats reference for backward compatibility
            self.workflow_stats = self.core_reviewer.review_stats

            return result

        except Exception as error:
            logger.error(f"[{thread_id}] Review workflow failed: {error}")

            return {
                "success": False,
                "error": str(error),
                "overall_score": 0.0,
                "threshold": getattr(self.config, 'REVIEW_THRESHOLD', 70.0),
                "approved": False,
                "issues": [f"Review process failed: {error}"],
                "tokens_used": 0,
                "mongodb_stored": False,
                "iteration": iteration,
                "thread_id": thread_id,
                "langgraph_workflow_used": True
            }

    def get_reviewer_workflow_stats(self) -> Dict[str, Any]:
        """Get comprehensive reviewer workflow statistics."""
        return self.jira_workflow.get_workflow_stats()

