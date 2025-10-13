# core/graph_nodes.py
"""
LangGraph Workflow Node Implementations
Contains all node methods for the workflow including:
- Trigger processing
- JIRA issue fetching and processing
- Planning, assembling, development, review, and rebuild nodes
- PR creation and SonarQube analysis
- MongoDB updates and GitHub integration
"""
import os
import uuid
import time
from datetime import datetime
from typing import Dict, Any, TYPE_CHECKING
import queue  # NEW: Add import
import threading  # NEW: Add import

if TYPE_CHECKING:
    from core.graph import RouterState, LangGraphWorkflow

import core.router
from tools.jira_client import get_todo_issues_mcp_tool, transition_issue
from tools.utils import log_activity
from services.performance_tracker import performance_tracker

# GitHub integration
try:
    from github import GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    GithubException = Exception

import logging
logger = logging.getLogger(__name__)


class WorkflowNodes:
    """Contains all node implementation methods for the LangGraph workflow"""

    def __init__(self, workflow_instance: 'LangGraphWorkflow'):
        """Initialize with reference to the workflow instance"""
        self.workflow = workflow_instance
        self.config = workflow_instance.config
        self.planner_agent = workflow_instance.planner_agent
        self.assembler_agent = workflow_instance.assembler_agent
        self.developer_agent = workflow_instance.developer_agent
        self.reviewer_agent = workflow_instance.reviewer_agent
        self.sonarqube_agent = workflow_instance.sonarqube_agent
        self.github_client = workflow_instance.github_client

    # ==================== NODE IMPLEMENTATIONS ====================

    def node_process_trigger(self, state: 'RouterState') -> 'RouterState':
        """Process workflow trigger and initialize thread"""
        thread_id = str(uuid.uuid4())[:8]
        state["thread_id"] = thread_id
        state["processing_stage"] = "trigger_processing"

        log_activity(f"Workflow triggered by message: {state['trigger_message']}", thread_id)
        log_activity("Starting complete AI development workflow...", thread_id)

        core.router.safe_stats_update({'workflows_executed': 1})
        return state

    def node_fetch_todo_issues(self, state: 'RouterState') -> 'RouterState':
        """Fetch TODO issues from JIRA"""
        thread_id = state["thread_id"]
        state["processing_stage"] = "fetching_todo_issues"

        if state.get("error"):
            return state

        log_activity("Fetching TODO issues for code generation...", thread_id)

        try:
            jira_result = get_todo_issues_mcp_tool(thread_id)

            if jira_result.get('success', False):
                state["todo_jira_issues"] = jira_result['issues']
                state["current_issue_index"] = 0
                log_activity(f"Found {len(state['todo_jira_issues'])} TODO issues", thread_id)
            else:
                state["error"] = f"TODO issues fetch failed: {jira_result.get('error', 'Unknown error')}"

            return state

        except Exception as error:
            state["error"] = f"TODO issues fetch error: {error}"
            return state

    def node_process_next_issue(self, state: 'RouterState') -> 'RouterState':
        """Process the next issue from the queue"""
        thread_id = state["thread_id"]

        if state.get("error"):
            return state

        todo_issues = state.get("todo_jira_issues", [])
        current_index = state.get("current_issue_index", 0)

        if current_index >= len(todo_issues):
            state["processing_stage"] = "workflow_complete"
            log_activity("All TODO issues processed", thread_id)
            return state

        # Get next issue
        current_issue = todo_issues[current_index]
        state["current_issue"] = current_issue
        state["processing_stage"] = f"processing_issue_{current_issue['key']}"
        state["rebuild_attempts"] = 0

        log_activity(f"Processing TODO issue: {current_issue['key']} - {current_issue['summary']}", thread_id)
        core.router.safe_stats_update({'issues_processed': 1})

        # Increment pending tasks when starting an issue
        with core.router.stats_lock:
            core.router.pending_tasks += 1
            core.router.processing_stats['tasks_pending'] = core.router.pending_tasks

        # Transition to In Progress
        if transition_issue(current_issue['key'], 'Start Progress', thread_id):
            log_activity(f"Transitioned {current_issue['key']} to In Progress", thread_id)
        else:
            log_activity(f"Failed to transition {current_issue['key']} to In Progress", thread_id)

        return state

    def node_plan_issue(self, state: 'RouterState') -> 'RouterState':
        """Plan the issue using Planner Agent"""
        thread_id = state["thread_id"]
        current_issue = state["current_issue"]

        if state.get("error"):
            return state

        log_activity(f"Planning for issue: {current_issue['key']}", thread_id)

        # Log: Planner Started
        core.router.safe_activity_log({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": "PlannerAgent",
            "action": "Started",
            "details": f"Planner Agent started for {current_issue['key']}",
            "status": "starting",
            "issueId": current_issue['key']
        })

        # Wait 2 seconds before processing
        time.sleep(2)

        # Log: Planner Processing
        core.router.safe_activity_log({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": "PlannerAgent",
            "action": "Processing",
            "details": f"Planner Agent processing planning for {current_issue['key']}",
            "status": "info",
            "issueId": current_issue['key']
        })

        try:
            start_time = time.time()
            planning_result = self.planner_agent.plan_issue(
                issue_data=current_issue,
                thread_id=thread_id
            )
            duration = time.time() - start_time

            state["planning_result"] = planning_result
            state["planner_tokens"] = planning_result.get("tokens_used", 0)

            if planning_result.get("success"):
                state["approved_subtasks"] = planning_result.get("approved_subtasks", [])
                state["needs_human"] = planning_result.get("needs_human", False)
                state["file_types"] = planning_result.get("file_requirements", {}).get("file_types", [])
                log_activity(f"Planning completed for {current_issue['key']}", thread_id)
                state["tokens_used"] += planning_result.get("tokens_used", 0)
                core.router.safe_stats_update({'planner_tokens': planning_result.get("tokens_used", 0)})

                # Print metrics
                print(f"Planner Agent Tokens Used: {planning_result.get('tokens_used', 0)}")
                print(f"Planner Agent Time Taken: {duration:.2f} seconds")
                print(f"Overall Tokens Used: {state['tokens_used']}")

                # Calculate total score from approved subtasks
                approved_subtasks = planning_result.get("approved_subtasks", [])
                total_score = sum(subtask.get("score", 0) for subtask in approved_subtasks)
                avg_score = total_score / len(approved_subtasks) if approved_subtasks else 0

                # Log detailed subtask information
                core.router.safe_activity_log({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "agent": "PlannerAgent",
                    "action": "Subtasks Generated",
                    "details": f"Generated {len(approved_subtasks)} subtasks for {current_issue['key']}",
                    "status": "success",
                    "issueId": current_issue['key'],
                    "subtasks": approved_subtasks,
                    "totalScore": round(total_score, 2),
                    "averageScore": round(avg_score, 2)
                })

                # Log: Planner Completed
                core.router.safe_activity_log({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "agent": "PlannerAgent",
                    "action": "Planning Completed",
                    "details": f"Planner Agent planning completed for {current_issue['key']}",
                    "status": "success",
                    "issueId": current_issue['key']
                })

            else:
                state["error"] = f"Planning failed: {planning_result.get('error')}"

            return state

        except Exception as error:
            state["error"] = f"Planning error: {error}"
            return state

    def node_assemble_document(self, state: 'RouterState') -> 'RouterState':
        """Assemble deployment document using Assembler Agent"""
        thread_id = state["thread_id"]
        current_issue = state["current_issue"]
        approved_subtasks = state.get("planning_result", {}).get("approved_subtasks", [])

        if state.get("error"):
            return state

        log_activity(f"Assembling document for issue: {current_issue['key']}", thread_id)

        # Log: Assembler Started
        core.router.safe_activity_log({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": "AssemblerAgent",
            "action": "Started",
            "details": f"Assembler Agent started for {current_issue['key']}",
            "status": "starting",
            "issueId": current_issue['key']
        })

        # Wait 2 seconds before processing
        time.sleep(2)

        # Log: Assembler Processing
        core.router.safe_activity_log({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": "AssemblerAgent",
            "action": "Processing",
            "details": f"Assembler Agent processing document assembly for {current_issue['key']}",
            "status": "info",
            "issueId": current_issue['key']
        })

        try:
            start_time = time.time()
            assemble_result = self.assembler_agent.create_deployment_document(
                approved_subtasks=approved_subtasks,
                issue_data=current_issue,
                thread_id=thread_id
            )
            duration = time.time() - start_time

            state["assemble_result"] = assemble_result
            state["assembler_tokens"] = assemble_result.get("tokens_used", 0)

            if assemble_result.get("success"):
                state["deployment_document"] = assemble_result.get("deployment_document", {})
                log_activity(f"Document assembled for {current_issue['key']}", thread_id)
                state["tokens_used"] += assemble_result.get("tokens_used", 0)
                core.router.safe_stats_update({'assembler_tokens': assemble_result.get("tokens_used", 0)})

                # Print metrics
                print(f"Assembler Agent Tokens Used: {assemble_result.get('tokens_used', 0)}")
                print(f"Assembler Agent Time Taken: {duration:.2f} seconds")
                print(f"Overall Tokens Used: {state['tokens_used']}")

                core.router.safe_stats_update({'assembler_generations': 1})

                # Log: Assembler Completed
                core.router.safe_activity_log({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "agent": "AssemblerAgent",
                    "action": "Document Assembly Completed",
                    "details": f"Assembler Agent document assembly completed for {current_issue['key']}",
                    "status": "success",
                    "issueId": current_issue['key']
                })

            else:
                state["error"] = f"Document assembly failed: {assemble_result.get('error')}"

            return state

        except Exception as error:
            state["error"] = f"Document assembly error: {error}"
            return state

    def node_develop_code(self, state: 'RouterState') -> 'RouterState':
        """Generate code using Developer Agent"""
        thread_id = state["thread_id"]
        current_issue = state["current_issue"]
        deployment_document = state.get("assemble_result", {}).get("deployment_document", {})

        if state.get("error"):
            return state

        log_activity(f"Developing code for issue: {current_issue['key']}", thread_id)

        # Log: Developer Started
        core.router.safe_activity_log({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": "DeveloperAgent",
            "action": "Started",
            "details": f"Developer Agent started for {current_issue['key']}",
            "status": "info",
            "issueId": current_issue['key']
        })

        # Log: Developer Processing
        core.router.safe_activity_log({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": "DeveloperAgent",
            "action": "Processing",
            "details": f"Developer Agent processing code generation for {current_issue['key']}",
            "status": "info",
            "issueId": current_issue['key']
        })

        try:
            start_time = time.time()

            # NEW: Create queue for file handoff
            review_queue = queue.Queue()
            state["review_queue"] = review_queue  # Pass to state for reviewer

            # Run developer with queue
            code_result = self.developer_agent.generate_code(
                deployment_document=deployment_document,
                issue_data=current_issue,
                thread_id=thread_id,
                review_queue=review_queue  # NEW: Pass queue
            )
            duration = time.time() - start_time

            state["developer_tokens"] = code_result.get("tokens_used", 0)

            if code_result.get("success"):
                state["generated_files"] = code_result.get("generated_files", {})
                log_activity(f"Code developed for {current_issue['key']}", thread_id)
                state["tokens_used"] += code_result.get("tokens_used", 0)
                core.router.safe_stats_update({'developer_tokens': code_result.get("tokens_used", 0)})

                # Print metrics
                print(f"Developer Agent Tokens Used: {code_result.get('tokens_used', 0)}")
                print(f"Developer Agent Time Taken: {duration:.2f} seconds")
                print(f"Overall Tokens Used: {state['tokens_used']}")

                core.router.safe_stats_update({'developer_generations': 1})

                # Log: Developer Completed
                core.router.safe_activity_log({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "agent": "DeveloperAgent",
                    "action": "Code Generation Completed",
                    "details": f"Developer Agent code generation completed for {current_issue['key']}. Files: {len(code_result.get('generated_files', {}))}",
                    "status": "success",
                    "issueId": current_issue['key']
                })

            else:
                state["error"] = f"Code development failed: {code_result.get('error')}"

            return state

        except Exception as error:
            state["error"] = f"Code development error: {error}"
            return state

    def node_review_code(self, state: 'RouterState') -> 'RouterState':
        """Review generated code using Reviewer Agent"""
        thread_id = state["thread_id"]
        current_issue = state["current_issue"]
        generated_files = state.get("generated_files", {})

        if state.get("error"):
            return state

        log_activity(f"Reviewing code for issue: {current_issue['key']}", thread_id)

        # Log: Reviewer Started
        core.router.safe_activity_log({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": "ReviewerAgent",
            "action": "Started",
            "details": f"Reviewer Agent started for {current_issue['key']}",
            "status": "starting",
            "issueId": current_issue['key']
        })

        # Wait 2 seconds before processing
        time.sleep(2)

        # Log: Reviewer Processing
        core.router.safe_activity_log({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": "ReviewerAgent",
            "action": "Processing",
            "details": f"Reviewer Agent processing code review for {current_issue['key']}",
            "status": "info",
            "issueId": current_issue['key']
        })

        try:
            start_time = time.time()
            review_result = self.reviewer_agent.review_generated_code_with_langgraph(
                issue_key=current_issue['key'],
                files=generated_files,
                file_types=state["file_types"],
                project_description=current_issue['summary'],
                iteration=state.get("rebuild_attempts", 0) + 1,
                thread_id=thread_id
            )
            duration = time.time() - start_time

            state["review_result"] = review_result
            state["reviewer_tokens"] = review_result.get("tokens_used", 0)

            if review_result.get('success', False):
                log_activity(f"Review completed: {review_result.get('overall_score', 0)}%", thread_id)
                state["tokens_used"] += review_result.get("tokens_used", 0)
                core.router.safe_stats_update({'reviewer_tokens': review_result.get("tokens_used", 0)})

                # Print metrics
                print(f"Reviewer Agent Tokens Used: {review_result.get('tokens_used', 0)}")
                print(f"Reviewer Agent Time Taken: {duration:.2f} seconds")
                print(f"Overall Tokens Used: {state['tokens_used']}")

                core.router.safe_stats_update({'successful_reviews': 1, 'reviewer_generations': 1})

                status = "success" if review_result.get('approved', False) else "warning"

                # Log: Reviewer Completed
                core.router.safe_activity_log({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "agent": "ReviewerAgent",
                    "action": "Code Review Completed",
                    "details": f"Reviewer Agent code review completed for {current_issue['key']}: Score {review_result.get('overall_score', 0)}%. Approved: {review_result.get('approved', False)}",
                    "status": status,
                    "issueId": current_issue['key']
                })

            else:
                log_activity(f"Review failed: {review_result.get('error', 'Unknown error')}", thread_id)

            return state

        except Exception as error:
            state["error"] = f"Code review error: {error}"
            return state

    def node_rebuild_code(self, state: 'RouterState') -> 'RouterState':
        """Rebuild code based on review feedback"""
        thread_id = state["thread_id"]
        current_issue = state["current_issue"]
        rebuild_attempts = state.get("rebuild_attempts", 0) + 1

        if state.get("error"):
            return state

        log_activity(f"Rebuilding code (attempt {rebuild_attempts}) for issue: {current_issue['key']}", thread_id)

        try:
            start_time = time.time()
            deployment_document = state.get("assemble_result", {}).get("deployment_document", {})
            feedback = state["review_result"].get("all_issues", [])

            code_result = self.developer_agent.generate_code(
                deployment_document=deployment_document,
                issue_data=current_issue,
                thread_id=thread_id,
                feedback=feedback
            )
            duration = time.time() - start_time

            state["generated_files"] = code_result.get("generated_files", {})
            state["rebuild_attempts"] = rebuild_attempts
            state["tokens_used"] += code_result.get("tokens_used", 0)
            state["rebuilder_tokens"] = state.get("rebuilder_tokens", 0) + code_result.get("tokens_used", 0)
            core.router.safe_stats_update({'rebuilder_tokens': code_result.get("tokens_used", 0)})

            if code_result.get("success"):
                log_activity(f"Rebuild completed for {current_issue['key']}", thread_id)

                # Print metrics
                print(f"Rebuilder Agent Tokens Used: {code_result.get('tokens_used', 0)}")
                print(f"Rebuilder Agent Time Taken: {duration:.2f} seconds")
                print(f"Overall Tokens Used: {state['tokens_used']}")

                core.router.safe_stats_update({'rebuilder_generations': 1, 'rebuild_cycles': 1})
                core.router.safe_activity_log({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "agent": "RebuilderAgent",
                    "action": "Code Rebuilt",
                    "details": f"Rebuilt code for {current_issue['key']} (attempt {rebuild_attempts})",
                    "status": "success",
                    "issueId": current_issue['key']
                })

            else:
                state["error"] = f"Code rebuild failed: {code_result.get('error')}"

            return state

        except Exception as error:
            state["error"] = f"Code rebuild error: {error}"
            return state

    def node_create_code_pr(self, state: 'RouterState') -> 'RouterState':
        """Create GitHub PR for approved code"""
        thread_id = state["thread_id"]
        current_issue = state["current_issue"]

        if state.get("error"):
            return state

        if not GITHUB_AVAILABLE or self.github_client is None:
            log_activity("GitHub integration not available or client not initialized - skipping PR creation", thread_id)
            state["code_pr_created"] = False
            self.update_mongodb_after_pr(state, thread_id, success=False)
            state["current_issue_index"] = state.get("current_issue_index", 0) + 1
            return state

        log_activity(f"Creating GitHub PR for approved code: {current_issue['key']}", thread_id)

        try:
            pr_created, pr_url = self.create_github_pr(
                issue_key=current_issue['key'],
                files=state.get("generated_files", {}),
                branch_name=self.config.REVIEW_BRANCH_NAME,
                thread_id=thread_id
            )

            state["code_pr_created"] = pr_created
            state["code_pr_url"] = pr_url
            if pr_created:
                core.router.safe_stats_update({'code_prs_created': 1})
                log_activity(f"GitHub PR created/updated successfully: {pr_url}", thread_id)

                # Transition to Done
                if transition_issue(current_issue['key'], 'Done', thread_id):
                    log_activity(f"Transitioned {current_issue['key']} to Done", thread_id)
                else:
                    log_activity(f"Failed to transition {current_issue['key']} to Done", thread_id)

                self.update_mongodb_after_pr(state, thread_id, success=True)

                core.router.safe_activity_log({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "agent": "GitHubAgent",  # FIXED: Changed from TaskAgent to GitHubAgent for PR creation
                    "action": "PR Created",
                    "details": f"Created/updated PR for {current_issue['key']}: {pr_url}",
                    "status": "success",
                    "issueId": current_issue['key']
                })
            else:
                log_activity("GitHub PR creation failed - continuing without PR", thread_id)
                self.update_mongodb_after_pr(state, thread_id, success=False)

            state["current_issue_index"] = state.get("current_issue_index", 0) + 1
            return state

        except GithubException as error:
            log_activity(f"GitHub PR exception: {str(error)} - continuing without PR", thread_id)
            state["code_pr_created"] = False
            self.update_mongodb_after_pr(state, thread_id, success=False)
            state["current_issue_index"] = state.get("current_issue_index", 0) + 1
            return state
        except Exception as error:
            log_activity(f"PR creation error: {str(error)}", thread_id)
            state["code_pr_created"] = False
            self.update_mongodb_after_pr(state, thread_id, success=False)
            state["current_issue_index"] = state.get("current_issue_index", 0) + 1
            return state

    def node_sonarqube_analysis(self, state: 'RouterState') -> 'RouterState':
        """Run SonarQube analysis on the PR"""
        thread_id = state["thread_id"]

        if state.get("error"):
            return state

        log_activity(f"Running SonarQube analysis for PR", thread_id)

        try:
            sonarqube_result = self.sonarqube_agent.analyze_latest_pr(thread_id)
            state["sonarqube_result"] = sonarqube_result
            state["tokens_used"] += sonarqube_result.get("tokens_used", 0)

            if sonarqube_result.get('success', False):
                log_activity(f"SonarQube analysis completed: Score {sonarqube_result.get('overall_score', 0.0)}",
                             thread_id)

                performance_tracker.increment_daily_metrics({
                    "code_quality_score": sonarqube_result.get('overall_score', 0.0)
                })

                score = sonarqube_result.get('overall_score', 0.0)
                core.router.safe_stats_update({
                    'total_sonar_scores': score,
                    'sonar_score_count': 1
                })

                with core.router.stats_lock:
                    if core.router.processing_stats['sonar_score_count'] > 0:
                        core.router.processing_stats['average_sonar_score'] = round(
                            core.router.processing_stats['total_sonar_scores'] / core.router.processing_stats['sonar_score_count'],
                            1
                        )

                core.router.safe_activity_log({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "agent": "SonarQubeAgent",
                    "action": "Analysis Completed",
                    "details": f"SonarQube score: {sonarqube_result.get('overall_score', 0.0)}%",
                    "status": "success"
                })

            else:
                state["error"] = f"SonarQube analysis failed: {sonarqube_result.get('error', 'Unknown error')}"

            return state

        except Exception as error:
            state["error"] = f"SonarQube analysis error: {error}"
            return state

    def node_finalize_workflow(self, state: 'RouterState') -> 'RouterState':
        """Finalize the complete workflow"""
        thread_id = state["thread_id"]

        log_activity("Finalizing complete workflow", thread_id)

        state["final_result"] = {
            "success": not state.get("error"),
            "trigger_message": state["trigger_message"],
            "issues_processed": state.get("current_issue_index", 0),
            "code_prs_created": state.get("code_pr_created", False),
            "tokens_used": state.get("tokens_used", 0),
            "processing_time": "completed",
            "error": state.get("error")
        }

        core.router.safe_stats_update({'tokens_used': state.get("tokens_used", 0)})
        log_activity("Workflow completed successfully", thread_id)
        return state

    def node_handle_error(self, state: 'RouterState') -> 'RouterState':
        """Handle errors in the workflow"""
        thread_id = state["thread_id"]
        error_msg = state.get("error", "Unknown error")

        log_activity(f"Workflow error: {error_msg}", thread_id)
        core.router.safe_stats_update({'errors': 1})

        core.router.safe_activity_log({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": "System",
            "action": "Error Occurred",
            "details": error_msg,
            "status": "error"
        })

        state["final_result"] = {
            "success": False,
            "error": error_msg,
            "trigger_message": state["trigger_message"]
        }

        return state

    # ==================== HELPER METHODS ====================

    def update_mongodb_after_pr(self, state: 'RouterState', thread_id: str, success: bool = True):
        """Update MongoDB with daily metrics after PR creation"""
        try:
            agent_metrics = {
                "PlannerAgent": {
                    "Task_completed": 1,
                    "LLM_model_used": os.getenv("PLANNER_LLM_MODEL", "unknown"),
                    "tokens_used": state.get("planner_tokens", 0)
                },
                "AssemblerAgent": {
                    "Task_completed": 1,
                    "LLM_model_used": os.getenv("ASSEMBLER_LLM_MODEL", "unknown"),
                    "tokens_used": state.get("assembler_tokens", 0)
                },
                "DeveloperAgent": {
                    "Task_completed": 1,
                    "LLM_model_used": os.getenv("DEVELOPER_LLM_MODEL", "unknown"),
                    "tokens_used": state.get("developer_tokens", 0)
                },
                "ReviewerAgent": {
                    "Task_completed": 1,
                    "LLM_model_used": os.getenv("REVIEWER_LLM_MODEL", "unknown"),
                    "tokens_used": state.get("reviewer_tokens", 0)
                }
            }

            if state.get("rebuild_attempts", 0) > 0:
                agent_metrics["RebuilderAgent"] = {
                    "Task_completed": state.get("rebuild_attempts", 0),
                    "LLM_model_used": os.getenv("DEVELOPER_LLM_MODEL", "unknown"),
                    "tokens_used": state.get("rebuilder_tokens", 0)
                }

            code_quality_score = state.get("review_result", {}).get("overall_score", 0.0)

            pr_data = {
                "issue_key": state["current_issue"]["key"],
                "pr_url": state.get("code_pr_url", ""),
                "files_count": len(state.get("generated_files", {}))
            }

            update_success = performance_tracker.update_daily_metrics_after_pr(
                pr_data=pr_data,
                agent_metrics=agent_metrics,
                sonarqube_score=code_quality_score,
                success=success,
                thread_id=thread_id
            )

            if update_success:
                log_activity(f"MongoDB daily metrics updated for {pr_data['issue_key']}", thread_id)
            else:
                log_activity(f"MongoDB update failed for {pr_data['issue_key']}", thread_id)

        except Exception as e:
            logger.error(f"[{thread_id}] Error updating MongoDB after PR: {e}")

    def create_github_pr(self, issue_key: str, files: Dict[str, str], branch_name: str, thread_id: str) -> tuple[bool, str]:
        """Create or update GitHub PR with generated files"""
        try:
            if not self.github_client:
                raise ValueError("GitHub client not initialized")

            repo = self.github_client.get_repo(f"{self.config.GITHUB_REPO_OWNER}/{self.config.GITHUB_REPO_NAME}")

            # Create or get branch
            try:
                branch = repo.get_branch(branch_name)
                log_activity(f"Branch {branch_name} exists", thread_id)
            except GithubException:
                main_branch = repo.get_branch(repo.default_branch)
                repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_branch.commit.sha)
                log_activity(f"Created branch {branch_name}", thread_id)
                branch = repo.get_branch(branch_name)

            # Commit files to branch
            for filename, content in files.items():
                try:
                    try:
                        existing = repo.get_contents(filename, ref=branch_name)
                        repo.update_file(
                            path=filename,
                            message=f"Update {filename} for {issue_key}",
                            content=content,
                            sha=existing.sha,
                            branch=branch_name
                        )
                        log_activity(f"Updated {filename}", thread_id)
                    except GithubException:
                        repo.create_file(
                            path=filename,
                            message=f"Add {filename} for {issue_key}",
                            content=content,
                            branch=branch_name
                        )
                        log_activity(f"Created {filename}", thread_id)
                except GithubException as e:
                    log_activity(f"Failed to commit {filename}: {e}", thread_id)
                    continue

            # Create or update PR
            pr_title = f"Code for {issue_key}: {list(files.keys())}"
            pr_body = f"Generated code for JIRA issue {issue_key}.\nFiles: {', '.join(files.keys())}"

            prs = repo.get_pulls(state='open', head=branch_name, base=repo.default_branch)
            if prs.totalCount > 0:
                pr = prs[0]
                pr.edit(title=pr_title, body=pr_body)
                log_activity(f"Updated existing PR #{pr.number}", thread_id)
            else:
                pr = repo.create_pull(
                    title=pr_title,
                    body=pr_body,
                    head=branch_name,
                    base=repo.default_branch
                )
                log_activity(f"Created new PR #{pr.number}", thread_id)

            return True, pr.html_url

        except GithubException as e:
            log_activity(f"GitHub PR operation failed: {e}", thread_id)
            return False, ""
        except Exception as e:
            log_activity(f"Unexpected error in PR creation: {e}", thread_id)
            return False, ""
