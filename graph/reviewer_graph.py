#Agent-flow\graph\reviewer_graph.py
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from tools.reviewer_tool import (
    format_files_for_review, get_knowledge_base_content, analyze_code_completeness,
    analyze_code_security, analyze_coding_standards, calculate_review_scores,
    store_review_in_mongodb, analyze_python_code_with_pylint
)
from ui.ui import workflow_status, workflow_status_lock
import logging
from threading import Lock
import queue  # NEW: Add import for queue

logger = logging.getLogger(__name__)

stats_lock = Lock()

class ReviewerState(TypedDict):
    """State structure for the LangGraph reviewer workflow."""
    # Input data
    issue_key: str
    files: Annotated[Dict[str, str], lambda x, y: {**x, **y}]  # NEW: Reducer for merging files
    file_types: List[str]
    project_description: str
    iteration: int
    thread_id: str

    # Processing data
    formatted_files_content: str
    standards_content: str
    security_guidelines: str
    language_standards: str

    # Analysis results
    completeness_result: Optional[Dict[str, Any]]
    security_result: Optional[Dict[str, Any]]
    standards_result: Optional[Dict[str, Any]]
    pylint_result: Optional[Dict[str, Any]]  # NEW: Pylint analysis result

    # NEW: Per-file results aggregation
    per_file_results: Annotated[Dict[str, Dict], lambda x, y: {**x, **y}]  # Reducer for merging dicts

    # Final results
    overall_score: float
    threshold: float
    approved: bool
    all_issues: List[str]
    tokens_used: Annotated[int, lambda x, y: x + y]  # NEW: Reducer for summing tokens
    mongodb_stored: bool

    # Metadata
    success: bool
    error: Optional[str]
    processing_time: float

    # NEW: Queue for receiving files from developer
    review_queue: Optional[queue.Queue]

def _node_format_files(state: ReviewerState) -> ReviewerState:
    """LangGraph node: Format files for review processing."""
    try:
        logger.info(f"[{state['thread_id']}] Node: Formatting files for review")

        with workflow_status_lock:
            workflow_status["agent"] = "ReviewerAgent"

        # Call simplified tool
        result = format_files_for_review.invoke({"files": state['files']})

        if result.get('success', False):
            state['formatted_files_content'] = result['formatted_content']
            logger.info(f"[{state['thread_id']}] Files formatted: {result['files_processed']} files")
        else:
            state['error'] = f"File formatting failed: {result.get('error', 'Unknown error')}"

        return state

    except Exception as error:
        state['error'] = f"File formatting node error: {error}"
        return state

def _node_load_knowledge_base(state: ReviewerState) -> ReviewerState:
    """LangGraph node: Load knowledge base content."""
    try:
        logger.info(f"[{state['thread_id']}] Node: Loading knowledge base content")

        with workflow_status_lock:
            workflow_status["agent"] = "ReviewerAgent"

        if state.get('error'):
            return state

        # Get standards content using simplified tool
        standards_result = get_knowledge_base_content.invoke({
            "operation": "get_standards_content",
            "file_types": state['file_types']
        })

        # Get security guidelines
        security_result = get_knowledge_base_content.invoke({"operation": "get_security_guidelines"})

        # Get language standards
        language_result = get_knowledge_base_content.invoke({
            "operation": "get_language_standards",
            "file_types": state['file_types']
        })

        if standards_result.get('success', False):
            state['standards_content'] = standards_result['content']

        if security_result.get('success', False):
            state['security_guidelines'] = security_result['content']

        if language_result.get('success', False):
            state['language_standards'] = language_result['content']

        logger.info(f"[{state['thread_id']}] Knowledge base content loaded successfully")

        return state

    except Exception as error:
        state['error'] = f"Knowledge base loading node error: {error}"
        return state

def _node_pylint_analysis(state: ReviewerState) -> ReviewerState:
    """LangGraph node: Pylint static analysis for Python files."""
    try:
        logger.info(f"[{state['thread_id']}] Node: Pylint analysis")

        with workflow_status_lock:
            workflow_status["agent"] = "ReviewerAgent"

        if state.get('error'):
            return state

        # Call Pylint analysis tool
        result = analyze_python_code_with_pylint.invoke({
            "files_content": {filename: content for filename, content in state['files'].items()},
            "thread_id": state['thread_id']
        })

        state['pylint_result'] = result

        if result.get('success', False):
            tokens = result.get('tokens_used', 0)
            state['tokens_used'] = tokens  # FIXED: Just assign, don't add (Annotated reducer handles it)
            logger.info(f"[{state['thread_id']}] Pylint analysis: {result['pylint_score']:.1f}/10 score, {result['files_analyzed']} files")
        else:
            logger.warning(f"[{state['thread_id']}] Pylint analysis failed: {result.get('error')}")

        return state

    except Exception as error:
        state['error'] = f"Pylint analysis node error: {error}"
        return state

def _node_completeness_analysis(state: ReviewerState) -> ReviewerState:
    """LangGraph node: Completeness analysis."""
    try:
        logger.info(f"[{state['thread_id']}] Node: Completeness analysis")

        with workflow_status_lock:
            workflow_status["agent"] = "ReviewerAgent"

        if state.get('error'):
            return state

        # Call simplified completeness analysis tool
        result = analyze_code_completeness.invoke({
            "issue_key": state['issue_key'],
            "project_description": state['project_description'],
            "files_content": state['formatted_files_content'],
            "standards_content": state['standards_content'],
            "thread_id": state['thread_id']
        })

        state['completeness_result'] = result

        if result.get('success', False):
            tokens = result.get('tokens_used', 0)
            state['tokens_used'] = tokens  # FIXED: Just assign, don't add
            logger.info(f"[{state['thread_id']}] Completeness analysis: {result['score']}% score")
        else:
            logger.warning(f"[{state['thread_id']}] Completeness analysis failed: {result.get('error')}")

        return state

    except Exception as error:
        state['error'] = f"Completeness analysis node error: {error}"
        return state

def _node_security_analysis(state: ReviewerState) -> ReviewerState:
    """LangGraph node: Security analysis."""
    try:
        logger.info(f"[{state['thread_id']}] Node: Security analysis")

        with workflow_status_lock:
            workflow_status["agent"] = "ReviewerAgent"

        if state.get('error'):
            return state

        # Call simplified security analysis tool - FIXED: Changed files_content to file_content
        result = analyze_code_security.invoke({
            "issue_key": state['issue_key'],
            "file_content": state['formatted_files_content'],  # FIXED: Changed to file_content (singular)
            "security_standards": state['security_guidelines'],
            "thread_id": state['thread_id']
        })

        state['security_result'] = result

        if result.get('success', False):
            tokens = result.get('tokens_used', 0)
            state['tokens_used'] = tokens  # FIXED: Just assign, don't add
            logger.info(f"[{state['thread_id']}] Security analysis: {result['score']}% score")
        else:
            logger.warning(f"[{state['thread_id']}] Security analysis failed: {result.get('error')}")

        return state

    except Exception as error:
        state['error'] = f"Security analysis node error: {error}"
        return state

def _node_standards_analysis(state: ReviewerState) -> ReviewerState:
    """LangGraph node: Standards analysis."""
    try:
        logger.info(f"[{state['thread_id']}] Node: Standards analysis")

        with workflow_status_lock:
            workflow_status["agent"] = "ReviewerAgent"

        if state.get('error'):
            return state

        # Call simplified standards analysis tool - FIXED: Changed files_content to file_content
        result = analyze_coding_standards.invoke({
            "file_types": state['file_types'],
            "file_content": state['formatted_files_content'],  # FIXED: Changed to file_content (singular)
            "language_standards": state['language_standards'],
            "thread_id": state['thread_id']
        })

        state['standards_result'] = result

        if result.get('success', False):
            tokens = result.get('tokens_used', 0)
            state['tokens_used'] = tokens  # FIXED: Just assign, don't add
            logger.info(f"[{state['thread_id']}] Standards analysis: {result['score']}% score")
        else:
            logger.warning(f"[{state['thread_id']}] Standards analysis failed: {result.get('error')}")

        return state

    except Exception as error:
        state['error'] = f"Standards analysis node error: {error}"
        return state

def _node_calculate_scores(state: ReviewerState) -> ReviewerState:
    """LangGraph node: Calculate overall scores and approval status."""
    try:
        logger.info(f"[{state['thread_id']}] Node: Calculating overall scores")

        with workflow_status_lock:
            workflow_status["agent"] = "ReviewerAgent"

        if state.get('error'):
            return state

        # Get individual scores with proper fallback handling
        completeness_result = state.get('completeness_result', {})
        security_result = state.get('security_result', {})
        standards_result = state.get('standards_result', {})

        # Check if at least one analysis succeeded
        has_valid_analysis = (
            (completeness_result and completeness_result.get('success', False)) or
            (security_result and security_result.get('success', False)) or
            (standards_result and standards_result.get('success', False))
        )

        if not has_valid_analysis:
            state['error'] = "All review analyses failed - cannot calculate scores"
            logger.error(f"[{state['thread_id']}] All review analyses failed")
            return state

        # Extract scores with fallbacks
        completeness_score = completeness_result.get('score', 0.0) if completeness_result and completeness_result.get('success') else 0.0
        security_score = security_result.get('score', 0.0) if security_result and security_result.get('success') else 0.0
        standards_score = standards_result.get('score', 0.0) if standards_result and standards_result.get('success') else 0.0

        # Call simplified tool
        result = calculate_review_scores.invoke({
            "completeness_score": completeness_score,
            "security_score": security_score,
            "standards_score": standards_score,
            "custom_threshold": state.get('threshold')
        })

        if result.get('success', False):
            state['overall_score'] = result['overall_score']
            state['approved'] = result['approved']

            # Collect all issues from successful analyses
            all_issues = []
            if completeness_result and completeness_result.get('success'):
                all_issues.extend(completeness_result.get('mistakes', []))
            if security_result and security_result.get('success'):
                all_issues.extend(security_result.get('mistakes', []))
            if standards_result and standards_result.get('success'):
                all_issues.extend(standards_result.get('mistakes', []))

            state['all_issues'] = all_issues

            status = "APPROVED" if result['approved'] else "NEEDS_IMPROVEMENT"
            logger.info(f"[{state['thread_id']}] Score calculation complete: {result['overall_score']:.1f}% ({status})")
        else:
            state['error'] = f"Score calculation failed: {result.get('error')}"

        return state

    except Exception as error:
        state['error'] = f"Score calculation node error: {error}"
        return state

def _node_store_results(state: ReviewerState) -> ReviewerState:
    try:
        logger.info(f"[{state['thread_id']}] Node: Storing results in MongoDB")

        with workflow_status_lock:
            workflow_status["agent"] = "ReviewerAgent"

        if state.get('error'):
            return state

        # Get individual scores
        completeness_score = state['completeness_result'].get('score', 75.0) if state['completeness_result'] else 75.0
        security_score = state['security_result'].get('score', 70.0) if state['security_result'] else 70.0
        standards_score = state['standards_result'].get('score', 80.0) if state['standards_result'] else 80.0

        # Call simplified MongoDB storage tool
        result = store_review_in_mongodb.invoke({
            "issue_key": state['issue_key'],
            "issues": state['all_issues'],
            "completeness_score": completeness_score,
            "security_score": security_score,
            "standards_score": standards_score,
            "overall_score": state['overall_score'],
            "iteration": state['iteration'],
            "thread_id": state['thread_id'],
            "tokens_used": state['tokens_used']
        })

        state['mongodb_stored'] = result.get('success', False)

        if result.get('success', False):
            logger.info(f"[{state['thread_id']}] MongoDB storage successful: {result.get('document_id')}")
        else:
            logger.warning(f"[{state['thread_id']}] MongoDB storage failed: {result.get('error')}")

        return state

    except Exception as error:
        state['error'] = f"MongoDB storage node error: {error}"
        return state

def _node_finalize_review(state: ReviewerState) -> ReviewerState:
    """LangGraph node: Finalize review results."""
    try:
        logger.info(f"[{state['thread_id']}] Node: Finalizing review results")

        # Check if workflow was successful
        if not state.get('error'):
            state['success'] = True

            logger.info(f"[{state['thread_id']}] Review finalized successfully: {state['overall_score']}%")
        else:
            state['success'] = False
            logger.error(f"[{state['thread_id']}] Review failed: {state.get('error')}")

        return state

    except Exception as error:
        state['error'] = f"Finalization node error: {error}"
        state['success'] = False
        return state

def build_reviewer_graph():
    """Create the LangGraph workflow with nodes and edges (preserved structure)."""
    workflow = StateGraph(ReviewerState)

    # Add nodes for each step (same as original)
    workflow.add_node("format_files", _node_format_files)
    workflow.add_node("load_knowledge_base", _node_load_knowledge_base)
    workflow.add_node("pylint_analysis", _node_pylint_analysis)
    workflow.add_node("completeness_analysis", _node_completeness_analysis)
    workflow.add_node("security_analysis", _node_security_analysis)
    workflow.add_node("standards_analysis", _node_standards_analysis)
    workflow.add_node("calculate_scores", _node_calculate_scores)
    workflow.add_node("store_results", _node_store_results)
    workflow.add_node("finalize_review", _node_finalize_review)

    # Define workflow edges (exactly the same)
    workflow.set_entry_point("format_files")
    workflow.add_edge("format_files", "load_knowledge_base")
    workflow.add_edge("load_knowledge_base", "pylint_analysis")
    workflow.add_edge("pylint_analysis", "completeness_analysis")
    workflow.add_edge("completeness_analysis", "security_analysis")
    workflow.add_edge("security_analysis", "standards_analysis")
    workflow.add_edge("standards_analysis", "calculate_scores")
    workflow.add_edge("calculate_scores", "store_results")
    workflow.add_edge("store_results", "finalize_review")
    workflow.add_edge("finalize_review", END)

    # Compile workflow with memory checkpointing
    compiled_workflow = workflow.compile(checkpointer=MemorySaver())

    logger.info("Simplified LangGraph reviewer workflow created with 9 nodes")
    return compiled_workflow