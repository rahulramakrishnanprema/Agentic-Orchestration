"""
Enhanced AI Development System - LangGraph Router and Controller
A complete LangGraph-based orchestration system featuring:
- LangGraph workflow connecting all agents (Planner, Assembler, Developer, Reviewer)
- Trigger-based initiation
- Complete JIRA issue processing pipeline
- Conditional edges for review-rebuild loops
- GitHub PR creation for code
"""
import os
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List
from threading import Lock

# Import configuration from settings
from config.settings import config

# Import the graph workflow (split out)
from core.graph import LangGraphWorkflow, RouterState

# Import agents
from agents.planner_agent import PlannerAgent
from agents.assembler_agent import AssemblerAgent
from agents.developer_agent import DeveloperAgent
from agents.reviewer import SimplifiedReviewer as ReviewerAgent

# Import JIRA client
from agents.sonarcube_review import FixedSonarQube

# GitHub integration
GITHUB_AVAILABLE = False
Github = None
GithubException = None
try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    pass

# Import threading for automation control
import threading

# Initialize tools globally
from tools.planner_tools import initialize_planner_tools
from tools.assembler_tool import initialize_assembler_tools
from tools.developer_tool import initialize_developer_tools
from tools.prompt_loader import PromptLoader
from tools.utils import log_activity

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Disable httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)


# Global components
github_client = None
planner_agent = None
assembler_agent = None
developer_agent = None
reviewer_agent = None
sonarqube_agent = None  # NEW: SonarQube agent
server_running = True

# NEW: Automation control
automation_running = False
automation_thread = None
automation_lock = Lock()

# NEW: Pending tasks counter
pending_tasks = 0

# Enhanced statistics tracking with per-agent details
processing_stats = {
    'workflows_executed': 0,
    'code_prs_created': 0,
    'issues_processed': 0,
    'successful_reviews': 0,
    'rebuild_cycles': 0,
    'tokens_used': 0,
    'planner_tokens': 0,  # NEW
    'assembler_tokens': 0,  # NEW
    'developer_tokens': 0,  # NEW
    'reviewer_tokens': 0,  # NEW
    'rebuilder_tokens': 0,  # NEW
    'errors': 0,
    'taskagent_generations': 0,
    'assembler_generations': 0,  # NEW: Added for Assembler Agent
    'developer_generations': 0,
    'reviewer_generations': 0,
    'rebuilder_generations': 0,
    'tasks_completed': 0,
    'tasks_failed': 0,
    'tasks_pending': 0,
    'tasks_moved_to_hitl': 0,
    'average_sonar_score': 0.0,
    'total_sonar_scores': 0.0,  # NEW: Track total scores for averaging
    'sonar_score_count': 0  # NEW: Track count for averaging
}

# Global activity logs
activity_logs: List[Dict[str, Any]] = []

stats_lock = Lock()
activity_lock = Lock()


def safe_stats_update(updates: Dict[str, Any]) -> None:
    """Thread-safe statistics update"""
    with stats_lock:
        for key, value in updates.items():
            if key in processing_stats:
                processing_stats[key] += value


def safe_activity_log(entry: Dict[str, Any]) -> None:
    """Thread-safe activity log append"""
    with activity_lock:
        activity_logs.insert(0, entry)  # Insert at beginning for reverse chronological
        if len(activity_logs) > 50:  # Keep last 50 logs
            activity_logs.pop()


class LangGraphRouter:
    """LangGraph-based router orchestrating the complete workflow"""

    def __init__(self, config):
        self.config = config
        self.workflow = None
        self.graph = None
        self._initialize_agents()
        self._initialize_github()
        self._initialize_sonarqube()  # NEW
        self.graph = LangGraphWorkflow(config, planner_agent, assembler_agent, developer_agent, reviewer_agent, sonarqube_agent, github_client)
        self.workflow = self.graph.workflow

    def _initialize_agents(self) -> bool:
        """Initialize all AI agents"""
        global planner_agent, assembler_agent, developer_agent, reviewer_agent

        try:
            log_activity("Initializing agents...")

            prompt_loader = PromptLoader("prompts")
            initialize_planner_tools(config, prompt_loader)
            initialize_assembler_tools(config, prompt_loader)
            initialize_developer_tools(config, prompt_loader)

            planner_agent = PlannerAgent(self.config)
            log_activity("Planner Agent initialized")

            assembler_agent = AssemblerAgent(self.config)
            log_activity("Assembler Agent initialized")

            developer_agent = DeveloperAgent(self.config)
            log_activity("Developer Agent initialized")

            reviewer_agent = ReviewerAgent(self.config)
            log_activity("Reviewer Agent initialized")

            return True

        except Exception as error:
            log_activity(f"Agent initialization failed: {error}")
            return False

    def _initialize_github(self) -> bool:
        """Initialize GitHub client"""
        global github_client

        if not GITHUB_AVAILABLE:
            log_activity("GitHub library not available")
            return False

        try:
            if self.config.GITHUB_TOKEN and self.config.GITHUB_REPO_OWNER and self.config.GITHUB_REPO_NAME:
                github_client = Github(self.config.GITHUB_TOKEN)
                user = github_client.get_user()
                log_activity(f"GitHub client initialized for user: {user.login}")
                return True
            else:
                log_activity("GitHub configuration incomplete")
                return False
        except Exception as error:
            log_activity(f"GitHub client initialization failed: {error}")
            return False

    def _initialize_sonarqube(self) -> bool:
        """Initialize SonarQube agent"""
        global sonarqube_agent

        try:
            sonarqube_agent = FixedSonarQube(self.config)
            log_activity("SonarQube Agent initialized")
            return True
        except Exception as error:
            log_activity(f"SonarQube initialization failed: {error}")
            return False

    def process_trigger(self, trigger_message: str) -> Dict[str, Any]:
        """Main entry point - process any trigger message through the complete workflow"""
        thread_id = str(uuid.uuid4())[:8]

        try:
            log_activity(f"Processing trigger: {trigger_message}", thread_id)

            # Initialize state
            initial_state = RouterState(
                trigger_message=trigger_message,
                thread_id=thread_id,
                todo_jira_issues=[],
                current_issue_index=0,
                current_issue={},
                planning_result={},
                assemble_result={},
                code_result={},
                review_result={},
                sonarqube_result={},  # NEW
                rebuild_attempts=0,
                code_pr_created=False,
                code_pr_url="",
                final_result={},
                error=None,
                processing_stage="initialized",
                tokens_used=0,
                needs_human=False,
                human_decision=None,
                generated_files={},
                file_types=[]
            )

            # Execute workflow
            final_state = self.workflow.invoke(initial_state, {"configurable": {"thread_id": thread_id}})

            return final_state.get("final_result", {"success": False, "error": "No final result"})

        except Exception as error:
            log_activity(f"Workflow execution failed: {error}", thread_id)
            return {"success": False, "error": str(error)}

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with stats_lock:
            return {
                "router_type": "langgraph_router",
                "workflow": "trigger_processor → jira_client → next_issue_processor → planner_agent → [hitl] → assembler_agent → developer_agent → reviewer_agent → [rebuilder → reviewer] → pull_request → finalizer",
                "stats": dict(processing_stats),
                "agents_initialized": {
                    "planner_agent": planner_agent is not None,
                    "assembler_agent": assembler_agent is not None,
                    "developer_agent": developer_agent is not None,
                    "reviewer_agent": reviewer_agent is not None,
                    "github_client": github_client is not None
                },
                "llm_config": {
                    "provider": "OpenRouter",
                    "model": config.ASSEMBLER_LLM_MODEL,
                    "api_url": config.LLM_API_URL
                }
            }

    def get_current_agent_stats(self) -> List[Dict[str, Any]]:
        """Get current session agent stats for Agentic_UI Agents tab"""
        with stats_lock:
            agents = [
                {
                    "agent": "PlannerAgent",
                    "tasks_processed": processing_stats['issues_processed'],
                    "tokens_used": processing_stats['planner_tokens'],
                    "success_rate": (processing_stats['successful_reviews'] / max(1, processing_stats['issues_processed'])) * 100,
                    "model_used": config.PLANNER_LLM_MODEL
                },
                {
                    "agent": "AssemblerAgent",
                    "tasks_processed": processing_stats['issues_processed'],
                    "tokens_used": processing_stats['assembler_tokens'],
                    "success_rate": (processing_stats['successful_reviews'] / max(1, processing_stats['issues_processed'])) * 100,
                    "model_used": config.ASSEMBLER_LLM_MODEL
                },
                {
                    "agent": "DeveloperAgent",
                    "tasks_processed": processing_stats['developer_generations'],
                    "tokens_used": processing_stats['developer_tokens'],
                    "success_rate": (processing_stats['successful_reviews'] / max(1, processing_stats['developer_generations'])) * 100,
                    "model_used": config.DEVELOPER_LLM_MODEL
                },
                {
                    "agent": "ReviewerAgent",
                    "tasks_processed": processing_stats['reviewer_generations'],
                    "tokens_used": processing_stats['reviewer_tokens'],
                    "success_rate": (processing_stats['successful_reviews'] / max(1, processing_stats['reviewer_generations'])) * 100,
                    "model_used": config.REVIEWER_LLM_MODEL
                },
                {
                    "agent": "RebuilderAgent",
                    "tasks_processed": processing_stats['rebuilder_generations'],
                    "tokens_used": processing_stats['rebuilder_tokens'],
                    "success_rate": (processing_stats['rebuild_cycles'] / max(1, processing_stats['rebuilder_generations'])) * 100,
                    "model_used": config.DEVELOPER_LLM_MODEL  # Rebuilder uses developer model
                }
            ]
            return agents


# Global router instance
router_instance = None
app_graph = None  # For LangGraph Studio


def initialize_system() -> bool:
    """Initialize the LangGraph router system"""
    global router_instance, app_graph

    try:
        router_instance = LangGraphRouter(config)
        app_graph = router_instance.workflow
        log_activity("LangGraph router system initialized successfully")
        return True
    except Exception as error:
        log_activity(f"System initialization failed: {error}")
        return False


def process_trigger_message(trigger_message: str) -> Dict[str, Any]:
    """Process any trigger message through the complete workflow"""
    if not router_instance:
        return {"success": False, "error": "Router not initialized"}

    return router_instance.process_trigger(trigger_message)


def get_system_status() -> Dict[str, Any]:
    """Get system status for Agentic_UI"""
    if not router_instance:
        return {"system_status": "NOT_INITIALIZED"}

    status = router_instance.get_stats()
    with stats_lock:
        return {
            "system_status": "RUNNING" if automation_running else "STOPPED",
            "active_issues": processing_stats['issues_processed'],
            "queue_size": 0,  # TODO: Track queue
            "running_tasks": processing_stats['workflows_executed'],
            "agents_ready": {
                "task_agent": True,  # Assuming JIRA client
                "planner_agent": planner_agent is not None,
                "assembler_agent": assembler_agent is not None,  # Added
                "developer_agent": developer_agent is not None,
                "reviewer_agent": reviewer_agent is not None,
                "rebuilder_agent": True,  # Part of developer
                "jira_client": True
            },
            "configuration": {
                "model": config.ASSEMBLER_LLM_MODEL,
                "mcp_endpoint": config.JIRA_SERVER,
                "project_key": config.PROJECT_KEY,
                "review_threshold": config.REVIEW_THRESHOLD
            },
            "current_stage": "idle",  # TODO: Track current stage
            "system_running": automation_running,
            "timestamp": datetime.now().isoformat()
        }


def get_system_stats() -> Dict[str, Any]:
    with stats_lock:
        total_tasks = processing_stats['issues_processed']
        success_rate = (processing_stats['successful_reviews'] / max(1, total_tasks)) * 100 if total_tasks > 0 else 0
        return {
            "totalPullRequests": processing_stats['code_prs_created'],
            "prAccepted": processing_stats['successful_reviews'],
            "tokensUsed": processing_stats['tokens_used'],
            "tasksCompleted": processing_stats['successful_reviews'],
            "tasksFailed": processing_stats['errors'],
            "tasksPending": pending_tasks,  # NEW: Use dynamic pending_tasks
            "tasksMovedToHITL": 0,  # TODO
            "averageSonarQubeScore": processing_stats['average_sonar_score'],
            "successRate": round(success_rate, 1),
            "taskagent_generations": processing_stats['issues_processed'],
            "developer_generations": processing_stats['issues_processed'],
            "reviewer_generations": processing_stats['successful_reviews'],
            "rebuilder_generations": processing_stats['rebuild_cycles'],
            "planner_tokens": processing_stats['planner_tokens'],  # NEW
            "assembler_tokens": processing_stats['assembler_tokens'],  # NEW
            "developer_tokens": processing_stats['developer_tokens'],  # NEW
            "reviewer_tokens": processing_stats['reviewer_tokens'],  # NEW
            "rebuilder_tokens": processing_stats['rebuilder_tokens'],  # NEW
            "last_updated": datetime.now().isoformat(),
            "system_status": "RUNNING" if automation_running else "STOPPED"
        }


def get_system_activity() -> Dict[str, Any]:
    with activity_lock:
        return {
            "activity": list(activity_logs)  # Return copy
        }


def get_system_config() -> Dict[str, Any]:
    return {"config": "LangGraph based"}


def get_system_env_vars() -> Dict[str, str]:
    return {key: getattr(config, key, "") for key in dir(config) if not key.startswith('_')}


def handle_ui_automation_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Agentic_UI automation request - start automation from ui"""
    # Start automation instead of just processing one trigger
    return start_automation()


def stop_ui_automation() -> Dict[str, Any]:
    """Handle Agentic_UI stop automation request"""
    return stop_automation()


def reset_system_stats() -> Dict[str, Any]:
    """Reset system statistics"""
    with stats_lock:
        processing_stats.update({
            'workflows_executed': 0,
            'code_prs_created': 0,
            'issues_processed': 0,
            'successful_reviews': 0,
            'rebuild_cycles': 0,
            'tokens_used': 0,
            'planner_tokens': 0,  # NEW
            'assembler_tokens': 0,  # NEW
            'developer_tokens': 0,  # NEW
            'reviewer_tokens': 0,  # NEW
            'rebuilder_tokens': 0,  # NEW
            'errors': 0,
            'taskagent_generations': 0,
            'assembler_generations': 0,  # NEW: Reset Assembler Agent generations
            'developer_generations': 0,
            'reviewer_generations': 0,
            'rebuilder_generations': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_pending': 0,
            'tasks_moved_to_hitl': 0,
            'average_sonar_score': 0.0,
            'total_sonar_scores': 0.0,  # NEW: Reset total sonar scores
            'sonar_score_count': 0  # NEW: Reset sonar score count
        })
    global pending_tasks
    pending_tasks = 0
    with activity_lock:
        activity_logs.clear()
    return {"success": True, "message": "Statistics reset"}


def start_automation() -> Dict[str, Any]:
    """Start the automation process from ui"""
    global automation_running, automation_thread

    with automation_lock:
        if automation_running:
            return {"success": False, "message": "Automation is already running"}

        if not router_instance:
            return {"success": False, "message": "Router not initialized"}

        automation_running = True
        log_activity("Automation started from ui")

        # Start automation in a separate thread
        automation_thread = threading.Thread(target=_automation_worker, daemon=True, name="AutomationWorker")
        automation_thread.start()

        return {"success": True, "message": "Automation started successfully"}


def stop_automation() -> Dict[str, Any]:
    """Stop the automation process from ui"""
    global automation_running, automation_thread

    with automation_lock:
        if not automation_running:
            return {"success": False, "message": "Automation is not running"}

        automation_running = False
        log_activity("Automation stopped from ui")

        # Wait for thread to finish (with timeout)
        if automation_thread and automation_thread.is_alive():
            automation_thread.join(timeout=5.0)

        automation_thread = None

        return {"success": True, "message": "Automation stopped successfully"}


def _automation_worker():
    """Worker function that processes automation in background"""
    global automation_running

    log_activity("Automation worker thread started")

    try:
        # Process trigger when automation starts
        if router_instance and automation_running:
            result = router_instance.process_trigger("ui triggered automation start")
            log_activity(f"Automation trigger result: {result.get('success', False)}")

        # Keep running and process any queued tasks
        while automation_running and server_running:
            time.sleep(5)
            # Here you can add logic to check for new tasks/triggers

    except Exception as e:
        log_activity(f"Automation worker error: {e}")
        automation_running = False

    log_activity("Automation worker thread stopped")


def get_automation_status() -> bool:
    """Get current automation status"""
    return automation_running


def run_system() -> None:
    """Run the main system loop - wait for ui trigger"""
    log_activity("LangGraph router system ready - waiting for ui trigger")

    # Keep system running and wait for automation commands from ui
    while server_running:
        time.sleep(1)


def shutdown_system() -> None:
    """Shutdown the system"""
    global server_running, automation_running

    # Stop automation if running
    if automation_running:
        stop_automation()

    server_running = False
    log_activity("LangGraph router system shutdown")


# Do NOT auto-initialize on import for LangGraph Studio
# Comment out to prevent startup failures in Studio
# initialize_system()


if __name__ == "__main__":
    # Initialize only when running as script
    initialize_system()

    print("=" * 100)
    print("LANGGRAPH AI DEVELOPMENT SYSTEM ROUTER")
    print("Workflow: Trigger → JIRA → Planner → [HITL] → Assembler → Developer → Reviewer → [Rebuild → Reviewer]* → PR")
    print(f"Using LLM: {config.DEVELOPER_LLM_MODEL} via {config.LLM_API_URL}")
    print("=" * 100)

    if router_instance:  # Already initialized
        try:
            run_system()
        except KeyboardInterrupt:
            shutdown_system()
    else:
        print("System initialization failed")

# For LangGraph Studio compatibility
app_graph = LangGraphRouter(config).workflow if 'LANGGRAPH_STUDIO' in os.environ else None
