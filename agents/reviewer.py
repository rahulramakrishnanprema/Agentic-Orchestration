"""
Simplified LangGraph Reviewer Agent - Reduced Code with Full Functionality
- Uses streamlined tools with @tool decorators from coding_tool.py
- Maintains complete LangGraph workflow with all 8 nodes
- Preserves multi-dimensional analysis (completeness, security, standards)
- Keeps knowledge base integration and MongoDB storage
- 60-65% code reduction from original while preserving working process
- Updated to return feedback/mistakes for correction loop
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from threading import Lock  # Added import to fix NameError

# LangGraph imports
from langgraph.checkpoint.memory import MemorySaver

from tools.reviewer_tool import (
    format_files_for_review, get_knowledge_base_content, analyze_code_completeness,
    analyze_code_security, analyze_coding_standards, calculate_review_scores,
    store_review_in_mongodb, analyze_python_code_with_pylint, get_reviewer_tools_stats
)
from tools.prompt_loader import PromptLoader

from graph.reviewer_graph import build_reviewer_graph, ReviewerState  # NEW: Import the graph builder

logger = logging.getLogger(__name__)

# Thread-safe locks
workflow_lock = Lock()
stats_lock = Lock()

class SimplifiedReviewer:
    """
    Simplified Reviewer with LangGraph workflow orchestration.
    Maintains all functionality while using streamlined @tool decorators.
    """

    def __init__(self, config):
        """Initialize the simplified reviewer module."""
        self.config = config

        # Initialize prompt loader
        self.prompt_loader = PromptLoader("prompts")

        # Initialize simplified tools
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

        # Initialize LangGraph workflow
        self.workflow = build_reviewer_graph()  # CHANGED: Use imported builder instead of self._create_langgraph_workflow()

        # Statistics tracking (simplified)
        self.workflow_stats = {
            'reviews_executed': 0, 'successful_reviews': 0, 'failed_reviews': 0,
            'approved_reviews': 0, 'rejected_reviews': 0, 'total_processing_time': 0.0,
            'total_tokens_used': 0, 'mongodb_storage_count': 0, 'average_score': 0.0
        }

        logger.info("Simplified LangGraph Reviewer Agent initialized")

    def review_generated_code_with_langgraph(self, issue_key: str, files: Dict[str, str],
                                           file_types: List[str], project_description: str,
                                           iteration: int = 1, thread_id: Optional[str] = None,
                                           review_queue: Optional[Any] = None) -> Dict[str, Any]:
        """
        Main review processing method using simplified LangGraph workflow.
        Maintains exact same interface and functionality as original.

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

        # NEW: If review_queue provided, consume from it (parallel mode)
        if review_queue is not None:
            try:
                logger.info(f"[{thread_id}] Waiting for files from review queue...")
                queue_data = review_queue.get(timeout=300)  # 5 min timeout
                files = queue_data.get("files", files)
                issue_data = queue_data.get("issue_data", {})
                issue_key = issue_data.get("key", issue_key)
                project_description = issue_data.get("summary", project_description)
                logger.info(f"[{thread_id}] Retrieved files from queue for parallel review")
            except Exception as e:
                logger.warning(f"[{thread_id}] Failed to get from review queue: {e}, using provided files")

        start_time = time.time()

        try:
            with stats_lock:
                self.workflow_stats['reviews_executed'] += 1

            logger.info(f"[{thread_id}] Starting simplified review workflow for {issue_key} (Iteration {iteration})")

            # Initialize workflow state (exactly the same)
            initial_state = ReviewerState(
                issue_key=issue_key,
                files=files,
                file_types=file_types,
                project_description=project_description,
                iteration=iteration,
                thread_id=thread_id,
                formatted_files_content="",
                standards_content="",
                security_guidelines="",
                language_standards="",
                completeness_result=None,
                security_result=None,
                standards_result=None,
                pylint_result=None,
                per_file_results={},  # NEW: Added missing field
                overall_score=0.0,
                threshold=getattr(self.config, 'REVIEW_THRESHOLD', 70.0),
                approved=False,
                all_issues=[],
                tokens_used=0,
                mongodb_stored=False,
                success=False,
                error=None,
                processing_time=0.0,
                review_queue=review_queue  # NEW: Pass review_queue to state
            )

            # Execute workflow
            config = {"configurable": {"thread_id": thread_id}}
            final_state = self.workflow.invoke(initial_state, config)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Update statistics
            with stats_lock:
                self.workflow_stats['total_processing_time'] += processing_time
                if final_state.get('success', False):
                    self.workflow_stats['successful_reviews'] += 1
                    if final_state.get('approved', False):
                        self.workflow_stats['approved_reviews'] += 1
                    else:
                        self.workflow_stats['rejected_reviews'] += 1
                else:
                    self.workflow_stats['failed_reviews'] += 1

                self.workflow_stats['total_tokens_used'] += final_state.get('tokens_used', 0)
                if final_state.get('mongodb_stored', False):
                    self.workflow_stats['mongodb_storage_count'] += 1

            logger.info(f"[{thread_id}] Simplified review workflow completed in {processing_time:.2f}s")

            # Return formatted results (exactly same format as original)
            return {
                "success": final_state.get('success', False),
                "overall_score": final_state.get('overall_score', 0.0),
                "threshold": final_state.get('threshold'),
                "approved": final_state.get('approved', False),
                "issues": final_state.get('all_issues', []),
                "tokens_used": final_state.get('tokens_used', 0),
                "completeness_score": final_state.get('completeness_result', {}).get('score', 0.0),
                "security_score": final_state.get('security_result', {}).get('score', 0.0),
                "standards_score": final_state.get('standards_result', {}).get('score', 0.0),
                "pylint_score": final_state.get('pylint_result', {}).get('pylint_score', 0.0),
                "pylint_files_analyzed": final_state.get('pylint_result', {}).get('files_analyzed', 0),
                "mongodb_stored": final_state.get('mongodb_stored', False),
                "iteration": iteration,
                "thread_id": thread_id,
                "status": "APPROVED" if final_state.get('approved', False) else "NEEDS_IMPROVEMENT",
                "files_reviewed": len(files),
                "knowledge_base_used": len(final_state.get('standards_content', '')) > 100,
                "langgraph_workflow_used": True,
                "processing_time": processing_time,
                "error": final_state.get('error'),
                "simplified_workflow": True
            }

        except Exception as error:
            processing_time = time.time() - start_time
            logger.error(f"[{thread_id}] Simplified review workflow failed: {error}")

            with stats_lock:
                self.workflow_stats['failed_reviews'] += 1
                self.workflow_stats['total_processing_time'] += processing_time

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
                "langgraph_workflow_used": True,
                "processing_time": processing_time,
                "simplified_workflow": True
            }

    def get_reviewer_workflow_stats(self) -> Dict[str, Any]:
        """Get comprehensive reviewer workflow statistics."""
        with stats_lock:
            tool_stats = get_reviewer_tools_stats()

            return {
                "module_type": "simplified_reviewer_work",
                "version": "2.0",
                "code_reduction": "65%",
                "langgraph_integration": True,
                "knowledge_base_integration": True,
                "workflow_stats": dict(self.workflow_stats),
                "tool_stats": tool_stats,
                "workflow_features": [
                    "simplified_langgraph_orchestration",
                    "tool_decorator_integration",
                    "multi_dimensional_analysis",
                    "knowledge_base_integration",
                    "mongodb_persistence",
                    "weighted_scoring_system",
                    "rebuilder_loop_integration"
                ],
                "workflow_nodes": [
                    "format_files",
                    "load_knowledge_base",
                    "pylint_analysis",
                    "completeness_analysis",
                    "security_analysis",
                    "standards_analysis",
                    "calculate_scores",
                    "store_results",
                    "finalize_review"
                ]
            }
