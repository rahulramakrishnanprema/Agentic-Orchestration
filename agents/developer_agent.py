"""
Developer Agent - Backward Compatible Wrapper
This file maintains backward compatibility with the existing project.
It now uses the modular CoreDeveloperAgent and JiraDeveloperWorkflow internally.

IMPORTANT: This file is kept for backward compatibility.
For new workflows, use CoreDeveloperAgent directly from agents.core_developer_agent
"""
import logging
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from pymongo import MongoClient

# Import the new modular components
from agents.core_developer_agent import CoreDeveloperAgent
from workflows.jira_developer_workflow import JiraDeveloperWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeveloperAgent:
    """
    LangGraph-based Developer Agent (Backward Compatible Wrapper)

    This class now delegates to:
    - CoreDeveloperAgent: Core development logic (reusable)
    - JiraDeveloperWorkflow: JIRA-specific integration
    """

    def __init__(self, config):
        self.config = config

        # Initialize modular components
        self.core_developer = CoreDeveloperAgent(config)
        self.jira_workflow = JiraDeveloperWorkflow(config)

        # For backward compatibility - expose the graph and memory
        self.graph = self.core_developer.graph
        self.global_project_memory = self.core_developer.global_project_memory

        # Legacy attributes for compatibility
        from tools.prompt_loader import PromptLoader
        from tools.developer_tool import generate_code_files, correct_code_with_feedback

        self.prompt_loader = PromptLoader("prompts")
        self.tools = [
            generate_code_files,
            correct_code_with_feedback
        ]

        # MongoDB - delegate to workflow
        self.mongo_client = self.jira_workflow.mongo_client
        self.mongo_collection = self.jira_workflow.mongo_collection

        logger.debug("Developer Agent initialized (using modular architecture)")

    def _initialize_mongodb(self):
        """Legacy method - now handled by JiraDeveloperWorkflow"""
        pass  # Kept for backward compatibility

    @staticmethod
    def _store_to_mongodb(issue_key: str, tokens_used: int = 0):
        """
        Legacy MongoDB storage method - kept for backward compatibility
        Now delegates to JiraDeveloperWorkflow
        """
        load_dotenv()
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        if not conn_str:
            logger.warning("MongoDB not available - Skipping developer feedback storage")
            return

        try:
            mongo_client = MongoClient(conn_str)
            db_name = os.getenv("MONGODB_PERFORMANCE_DATABASE", "aristotle_performance")
            coll_name = os.getenv("MONGODB_AGENT_PERFORMANCE", "agent_performance")
            mongo_collection = mongo_client[db_name][coll_name]

            document = {
                "agent_type": "developer",
                "issue_key": issue_key,
                "timestamp": datetime.now(),
                "date": datetime.now().date().isoformat(),
                "tokens_used": tokens_used,
                "llm_model": os.getenv("DEVELOPER_LLM_MODEL", "unknown")
            }

            result = mongo_collection.insert_one(document)
            logger.info(f"[DEVELOPER] Stored data for {issue_key} in MongoDB: ID {result.inserted_id}")
        except Exception as e:
            logger.error(f"[DEVELOPER] Failed to store data in MongoDB: {e}")

    def generate_code(self, deployment_document: Dict[str, Any],
                      issue_data: Optional[Dict[str, Any]] = None, thread_id: Optional[str] = None,
                      feedback: Optional[List[str]] = None, review_queue: Optional[Any] = None) -> Dict[str, Any]:
        """
        Run the code generation sub-graph using deployment document
        (Backward compatible method - now uses modular architecture)

        Args:
            deployment_document: Document with requirements
            issue_data: Optional issue information
            thread_id: Optional thread identifier
            feedback: Optional feedback for correction
            review_queue: Optional queue for parallel reviewer handoff
        """
        if not thread_id:
            thread_id = f"DEVELOPER-{threading.current_thread().ident}"

        try:
            # If issue_data provided, use JIRA workflow
            if issue_data and issue_data.get('key'):
                result = self.jira_workflow.generate_code_for_jira_issue(
                    deployment_document=deployment_document,
                    issue_data=issue_data,
                    thread_id=thread_id,
                    feedback=feedback,
                    review_queue=review_queue
                )
            else:
                # Use core developer directly for non-JIRA workflows
                context = {"review_queue": review_queue}
                result = self.core_developer.develop(
                    deployment_document=deployment_document,
                    context=context,
                    feedback=feedback,
                    thread_id=thread_id
                )

            # Update local memory reference for backward compatibility
            self.global_project_memory = self.core_developer.global_project_memory

            return result

        except Exception as e:
            logger.error(f"[DEVELOPER-{thread_id}] Code generation failed: {e}")
            return {"success": False, "error": str(e)}
