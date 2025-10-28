# core/graph.py (Updated with assembler support)
"""
LangGraph Workflow graph.py
Handles the graph building, nodes, edges, and conditional routing for agent connections.
"""
import logging
from typing import Dict, Any, List, Optional, TypedDict

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import core.router
# Import agents
from agents.planner_agent import PlannerAgent
from agents.assembler_agent import AssemblerAgent
from agents.developer_agent import DeveloperAgent
from agents.reviewer import SimplifiedReviewer as ReviewerAgent

# Import HITL
from core.hitl import hitl_pause

# Import JIRA client
from agents.sonarcube_review import FixedSonarQube

# Import node implementations
from core.graph_nodes import WorkflowNodes

# Import utils
from tools.utils import log_activity

# Import performance tracker
from services.performance_tracker import performance_tracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Disable httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)

# LangGraph State Definition
class RouterState(TypedDict):
    """State for the complete LangGraph workflow"""
    trigger_message: str
    thread_id: str
    todo_jira_issues: List[Dict[str, Any]]
    current_issue_index: int
    current_issue: Dict[str, Any]
    planning_result: Dict[str, Any]
    approved_subtasks: List[Dict[str, Any]]  # NEW: Added missing field
    assemble_result: Dict[str, Any]
    deployment_document: Dict[str, Any]  # NEW: Added missing field
    code_result: Dict[str, Any]
    review_result: Dict[str, Any]
    sonarqube_result: Dict[str, Any]
    rebuild_attempts: int
    code_pr_created: bool
    code_pr_url: str
    final_result: Dict[str, Any]
    error: Optional[str]
    processing_stage: str
    tokens_used: int
    needs_human: bool
    human_decision: Optional[str]
    generated_files: Dict[str, str]
    file_types: List[str]
    planner_tokens: int
    assembler_tokens: int
    developer_tokens: int
    reviewer_tokens: int
    rebuilder_tokens: int
    # NEW: Fields for recursive project creation
    create_recursive_project: bool  # Flag to enable/disable recursive project creation
    recursive_project_result: Dict[str, Any]  # Result of project creation
    recursive_project_key: Optional[str]  # Key of the created project

class LangGraphWorkflow:
    """LangGraph workflow class - Handles graph building and workflow orchestration"""

    def __init__(self, config, planner_agent, assembler_agent, developer_agent, reviewer_agent, sonarqube_agent, github_client):
        self.config = config
        self.planner_agent = planner_agent
        self.assembler_agent = assembler_agent
        self.developer_agent = developer_agent
        self.reviewer_agent = reviewer_agent
        self.sonarqube_agent = sonarqube_agent
        self.github_client = github_client
        self.workflow = None

        # Initialize node implementations
        self.nodes = WorkflowNodes(self)

        # Build the workflow
        self._build_workflow()

    def _build_workflow(self) -> None:
        """Build the complete LangGraph workflow"""
        workflow = StateGraph(RouterState)

        # Add all nodes with descriptive names for LangGraph Studio
        workflow.add_node("trigger_processor", self.nodes.node_process_trigger)
        workflow.add_node("jira_client", self.nodes.node_fetch_todo_issues)
        workflow.add_node("next_issue_processor", self.nodes.node_process_next_issue)
        workflow.add_node("planner_agent", self.nodes.node_plan_issue)
        workflow.add_node("project_creator", self.nodes.node_create_recursive_project)  # NEW: Recursive project creation
        workflow.add_node("assembler_agent", self.nodes.node_assemble_document)
        workflow.add_node("hitl", hitl_pause)
        workflow.add_node("developer_agent", self.nodes.node_develop_code)
        workflow.add_node("reviewer_agent", self.nodes.node_review_code)
        workflow.add_node("rebuilder", self.nodes.node_rebuild_code)
        workflow.add_node("pull_request", self.nodes.node_create_code_pr)
        workflow.add_node("sonarqube_analysis", self.nodes.node_sonarqube_analysis)
        workflow.add_node("finalizer", self.nodes.node_finalize_workflow)
        workflow.add_node("error_handler", self.nodes.node_handle_error)

        # Define workflow structure
        workflow.set_entry_point("trigger_processor")

        # Main flow
        workflow.add_edge("trigger_processor", "jira_client")
        workflow.add_edge("jira_client", "next_issue_processor")

        # Issue processing flow
        workflow.add_conditional_edges(
            "next_issue_processor",
            self._should_process_issue,
            {"continue": "planner_agent", "complete": "finalizer"}
        )

        workflow.add_conditional_edges("planner_agent", self._check_needs_human,
                                       {"needs_human": "hitl", "approved": "project_creator", "error": "error_handler"})

        # NEW: After planning, create recursive project, then continue to assembler
        workflow.add_edge("project_creator", "assembler_agent")

        workflow.add_edge("assembler_agent", "developer_agent")

        workflow.add_conditional_edges("hitl", self._route_human_decision,
                                       {"approve": "project_creator", "reject": "planner_agent",
                                        "error": "error_handler"})

        workflow.add_edge("developer_agent", "reviewer_agent")

        # Review-rebuild loop
        workflow.add_conditional_edges(
            "reviewer_agent",
            self._should_rebuild,
            {"rebuild": "rebuilder", "approve": "pull_request", "error": "error_handler"}
        )

        workflow.add_edge("rebuilder", "reviewer_agent")
        workflow.add_conditional_edges("pull_request", self._should_process_issue,
                                       {"continue": "next_issue_processor",
                                        "complete": "sonarqube_analysis"})

        # SonarQube after all issues/PRs
        workflow.add_edge("sonarqube_analysis", "finalizer")

        # Finalization
        workflow.add_edge("finalizer", END)
        workflow.add_edge("error_handler", END)

        # Compile workflow with memory checkpointing
        self.workflow = workflow.compile(checkpointer=MemorySaver())

        log_activity("LangGraph workflow built successfully")

    # ==================== CONDITIONAL EDGE METHODS ====================

    def _check_needs_human(self, state: RouterState) -> str:
        """Check if human intervention is needed"""
        if state.get("error"):
            return "error"
        return "needs_human" if state.get("needs_human", False) else "approved"

    def _route_human_decision(self, state: RouterState) -> str:
        """Route based on human decision"""
        if state.get("error"):
            return "error"
        decision = state.get("human_decision", "approve")
        return decision

    def _should_rebuild(self, state: RouterState) -> str:
        """Determine if code should be rebuilt"""
        if state.get("error"):
            return "error"

        review_result = state.get("review_result", {})
        rebuild_attempts = state.get("rebuild_attempts", 0)

        if not review_result.get('success', False):
            return "error"

        if review_result.get('approved', False):
            return "approve"

        if rebuild_attempts >= self.config.MAX_REBUILD_ATTEMPTS:
            return "error"

        return "rebuild"

    def _should_process_issue(self, state: RouterState) -> str:
        """Determine if we should process next issue or complete"""
        if state.get("error"):
            return "error"

        todo_issues = state.get("todo_jira_issues", [])
        current_index = state.get("current_issue_index", 0)

        return "complete" if current_index >= len(todo_issues) else "continue"
