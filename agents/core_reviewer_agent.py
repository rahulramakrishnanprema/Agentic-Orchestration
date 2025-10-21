"""
Core Reviewer Agent - Modular and Reusable
This is a standalone reviewer that can be integrated into any workflow.
It accepts generated code files and outputs review results with scores and feedback.

Usage:
    from agents.core_reviewer_agent import CoreReviewerAgent

    reviewer = CoreReviewerAgent(config)
    result = reviewer.review(
        files={"main.py": "code content..."},
        context={"identifier": "TASK-001", "project_description": "..."}
    )
    # Returns: {"success": True, "overall_score": 85.0, "approved": True, "issues": [...]}
"""
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CoreReviewerAgent:
    """
    Core Reviewer Agent - Framework-agnostic code review logic
    Can be used in any LangGraph workflow or standalone
    """

    def __init__(self, config=None):
        """Initialize the core reviewer"""
        self.config = config or {}

        # Lazy import to avoid circular dependencies
        from tools.prompt_loader import PromptLoader
        self.prompt_loader = PromptLoader("prompts")

        # Initialize reviewer tools with MongoDB connection
        from tools.reviewer_tool import initialize_reviewer_tools
        initialize_reviewer_tools(self.config, self.prompt_loader, None)
        logger.debug("Core Reviewer tools initialized")

        # Build the graph
        from graph.reviewer_graph import build_reviewer_graph
        self.graph = build_reviewer_graph()

        # Statistics tracking
        self.review_stats = {
            'reviews_executed': 0,
            'successful_reviews': 0,
            'failed_reviews': 0,
            'approved_reviews': 0,
            'rejected_reviews': 0,
            'total_tokens_used': 0,
            'average_score': 0.0
        }

        logger.debug("Core Reviewer Agent initialized (modular version)")

    def review(
        self,
        files: Dict[str, str],
        context: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main review method - accepts code files and returns review results

        Args:
            files: Dictionary of filename -> code content
            context: Additional context (identifier, project_description, file_types, etc.)
            thread_id: Optional thread identifier for logging

        Returns:
            {
                "success": bool,
                "overall_score": float,
                "approved": bool,
                "issues": List[str],
                "completeness_score": float,
                "security_score": float,
                "standards_score": float,
                "pylint_score": float,
                "tokens_used": int,
                "error": Optional[str]
            }
        """
        if thread_id is None:
            thread_id = f"REVIEWER-{threading.current_thread().ident}"

        context = context or {}
        identifier = context.get("identifier", "UNKNOWN")
        project_description = context.get("project_description", "Code review")
        file_types = context.get("file_types", self._infer_file_types(files))
        iteration = context.get("iteration", 1)
        threshold = context.get("threshold", getattr(self.config, 'REVIEW_THRESHOLD', 70.0))

        try:
            logger.info(f"[CORE-REVIEWER-{thread_id}] Starting code review for {identifier}...")

            # Update stats
            self.review_stats['reviews_executed'] += 1

            # Import state type
            from graph.reviewer_graph import ReviewerState

            # Prepare initial state (WITHOUT review_queue - it cannot be serialized)
            initial_state = ReviewerState(
                issue_key=identifier,
                files=files,
                file_types=file_types,
                project_description=project_description,
                iteration=iteration,
                thread_id=thread_id,
                formatted_files_content="",
                standards_content="",
                security_guidelines="",
                language_standards="",
                analyses={},
                pylint_result=None,
                per_file_results={},
                overall_score=0.0,
                threshold=threshold,
                approved=False,
                all_issues=[],
                tokens_used=0,
                mongodb_stored=False,
                success=False,
                error=None,
                processing_time=0.0,
                review_queue=None
            )

            # Execute the graph
            config_dict = {"configurable": {"thread_id": thread_id}}
            final_state = self.graph.invoke(initial_state, config_dict)

            # Update stats
            if final_state.get('success', False):
                self.review_stats['successful_reviews'] += 1
                if final_state.get('approved', False):
                    self.review_stats['approved_reviews'] += 1
                else:
                    self.review_stats['rejected_reviews'] += 1
            else:
                self.review_stats['failed_reviews'] += 1

            self.review_stats['total_tokens_used'] += final_state.get('tokens_used', 0)

            # Extract analysis results
            analyses = final_state.get('analyses', {})
            completeness_result = analyses.get('completeness', {})
            security_result = analyses.get('security', {})
            standards_result = analyses.get('standards', {})
            pylint_result = final_state.get('pylint_result', {})

            logger.info(f"[CORE-REVIEWER-{thread_id}] Review completed - Score: {final_state.get('overall_score', 0.0):.1f}%, Approved: {final_state.get('approved', False)}")

            return {
                "success": final_state.get('success', False),
                "overall_score": final_state.get('overall_score', 0.0),
                "threshold": threshold,
                "approved": final_state.get('approved', False),
                "issues": final_state.get('all_issues', []),
                "completeness_score": completeness_result.get('score', 0.0) if completeness_result else 0.0,
                "security_score": security_result.get('score', 0.0) if security_result else 0.0,
                "standards_score": standards_result.get('score', 0.0) if standards_result else 0.0,
                "pylint_score": pylint_result.get('pylint_score', 0.0) if pylint_result else 0.0,
                "pylint_files_analyzed": pylint_result.get('files_analyzed', 0) if pylint_result else 0,
                "tokens_used": final_state.get('tokens_used', 0),
                "mongodb_stored": final_state.get('mongodb_stored', False),
                "files_reviewed": len(files),
                "error": final_state.get('error'),
                "status": "APPROVED" if final_state.get('approved', False) else "NEEDS_IMPROVEMENT"
            }

        except Exception as e:
            logger.error(f"[CORE-REVIEWER-{thread_id}] Review failed: {e}")
            self.review_stats['failed_reviews'] += 1

            return {
                "success": False,
                "error": str(e),
                "overall_score": 0.0,
                "threshold": threshold,
                "approved": False,
                "issues": [f"Review process failed: {e}"],
                "tokens_used": 0,
                "files_reviewed": len(files),
                "status": "ERROR"
            }

    def _infer_file_types(self, files: Dict[str, str]) -> List[str]:
        """Infer file types from filenames"""
        file_types = set()
        for filename in files.keys():
            if filename.endswith('.py'):
                file_types.add('python')
            elif filename.endswith(('.js', '.jsx', '.ts', '.tsx')):
                file_types.add('javascript')
            elif filename.endswith('.java'):
                file_types.add('java')
            elif filename.endswith(('.cpp', '.cc', '.c', '.h')):
                file_types.add('cpp')
            elif filename.endswith('.go'):
                file_types.add('go')
            elif filename.endswith('.rs'):
                file_types.add('rust')
            else:
                file_types.add('general')
        return list(file_types)

    def get_review_stats(self) -> Dict[str, Any]:
        """Get review statistics"""
        stats = self.review_stats.copy()
        if stats['successful_reviews'] > 0:
            stats['approval_rate'] = (stats['approved_reviews'] / stats['successful_reviews']) * 100
        else:
            stats['approval_rate'] = 0.0
        return stats

    def reset_stats(self):
        """Reset review statistics"""
        self.review_stats = {
            'reviews_executed': 0,
            'successful_reviews': 0,
            'failed_reviews': 0,
            'approved_reviews': 0,
            'rejected_reviews': 0,
            'total_tokens_used': 0,
            'average_score': 0.0
        }
        logger.info("Core Reviewer stats reset")
