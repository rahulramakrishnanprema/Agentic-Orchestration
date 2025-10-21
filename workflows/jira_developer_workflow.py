# C:\Users\Rahul\Agent-flow\workflows\jira_developer_workflow.py
"""
JIRA-Specific Developer Workflow
This file contains JIRA-specific integration logic that uses the CoreDeveloperAgent.
It handles:
- JIRA issue data extraction
- MongoDB storage for JIRA issues
- UI integration for JIRA workflow
- Performance tracking specific to JIRA
- Review queue management

This keeps JIRA-specific logic separate from the core development logic.
"""
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import MongoClient

from agents.core_developer_agent import CoreDeveloperAgent
from config.settings import config as app_config

logger = logging.getLogger(__name__)


class JiraDeveloperWorkflow:
    """
    JIRA-specific workflow wrapper for CoreDeveloperAgent
    Handles JIRA issue processing, MongoDB storage, and UI integration
    """

    def __init__(self, config):
        self.config = config
        self.core_developer = CoreDeveloperAgent(config)

        # Initialize MongoDB for JIRA-specific storage
        self.mongo_client = None
        self.mongo_collection = None
        self._initialize_mongodb()

        logger.debug("JIRA Developer Workflow initialized")

    def _initialize_mongodb(self):
        """Initialize MongoDB connection for JIRA feedback storage"""
        try:
            conn_str = app_config.MONGODB_CONNECTION_STRING
            if not conn_str:
                logger.warning("MONGODB_CONNECTION_STRING not set - JIRA developer storage disabled")
                return

            self.mongo_client = MongoClient(conn_str)
            db_name = app_config.MONGODB_PERFORMANCE_DATABASE
            coll_name = app_config.MONGODB_AGENT_PERFORMANCE

            db = self.mongo_client[db_name]
            self.mongo_collection = db[coll_name]
            logger.debug(f"JIRA Developer MongoDB ready - Database: {db_name}, Collection: {coll_name}")
        except Exception as e:
            logger.error(f"JIRA Developer MongoDB init failed: {e}")
            self.mongo_collection = None

    def _store_to_mongodb(self, issue_key: str, tokens_used: int = 0):
        """Store JIRA-specific developer data to MongoDB"""
        if self.mongo_collection is None:
            logger.warning("MongoDB not available - Skipping JIRA developer storage")
            return

        try:
            document = {
                "agent_type": "developer",
                "issue_key": issue_key,
                "timestamp": datetime.now(),
                "date": datetime.now().date().isoformat(),
                "tokens_used": tokens_used,
                "llm_model": app_config.DEVELOPER_LLM_MODEL or "unknown"
            }

            result = self.mongo_collection.insert_one(document)
            logger.info(f"[JIRA-DEVELOPER] Stored data for {issue_key} in MongoDB: ID {result.inserted_id}")
        except Exception as e:
            logger.error(f"[JIRA-DEVELOPER] Failed to store in MongoDB: {e}")

    def _log_to_ui(self, issue_key: str, file_count: int, thread_id: str):
        """Log development results to UI"""
        try:
            import core.router
            import uuid

            core.router.safe_activity_log({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "agent": "DeveloperAgent",
                "action": "Code Generation Completed",
                "details": f"Generated {file_count} files for {issue_key}",
                "status": "success",
                "issueId": issue_key,
                "fileCount": file_count,
                "threadId": thread_id
            })

            logger.info(f"[JIRA-DEVELOPER] UI Log: {issue_key} - {file_count} files generated")
        except Exception as e:
            logger.warning(f"[JIRA-DEVELOPER] Failed to log to UI: {e}")

    def _save_files_locally(self, generated_files: Dict[str, str], issue_key: str):
        """Save generated files to local filesystem"""
        try:
            from tools.developer_tool import save_files_locally
            save_files_locally(generated_files, issue_key)
            logger.info(f"[JIRA-DEVELOPER] Saved {len(generated_files)} files locally for {issue_key}")
        except Exception as e:
            logger.warning(f"[JIRA-DEVELOPER] Failed to save files locally: {e}")

    def generate_code_for_jira_issue(
        self,
        deployment_document: Dict[str, Any],
        issue_data: Dict[str, Any],
        thread_id: Optional[str] = None,
        feedback: Optional[list] = None,
        review_queue: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generate code for a JIRA issue using CoreDeveloperAgent

        Args:
            deployment_document: Document with requirements and specifications
            issue_data: JIRA issue data (key, summary, description, etc.)
            thread_id: Optional thread identifier
            feedback: Optional feedback for code correction
            review_queue: Optional queue for parallel reviewer handoff

        Returns:
            {
                "success": bool,
                "generated_files": Dict[str, str],
                "tokens_used": int,
                "error": Optional[str]
            }
        """
        if not thread_id:
            thread_id = f"JIRA-DEVELOPER-{threading.current_thread().ident}"

        issue_key = issue_data.get('key', 'UNKNOWN')
        start_time = datetime.now()

        try:
            logger.info(f"[JIRA-DEVELOPER-{thread_id}] Starting code generation for {issue_key}...")

            # Prepare context with JIRA-specific data
            context = {
                "issue_data": issue_data,
                "identifier": issue_key,
                "review_queue": review_queue
            }

            # Call core developer
            result = self.core_developer.develop(
                deployment_document=deployment_document,
                context=context,
                feedback=feedback,
                thread_id=thread_id
            )

            if not result.get("success"):
                logger.error(f"[JIRA-DEVELOPER-{thread_id}] Code generation failed for {issue_key}: {result.get('error')}")
                return result

            generated_files = result.get("generated_files", {})
            tokens_used = result.get("tokens_used", 0)

            # JIRA-specific post-processing
            self._save_files_locally(generated_files, issue_key)
            self._store_to_mongodb(issue_key, tokens_used)
            self._log_to_ui(issue_key, len(generated_files), thread_id)

            # If review queue provided, push files for parallel review
            if review_queue is not None:
                try:
                    review_queue.put({
                        "files": generated_files,
                        "issue_data": issue_data,
                        "thread_id": thread_id
                    })
                    logger.info(f"[JIRA-DEVELOPER-{thread_id}] Pushed files to review queue for {issue_key}")
                except Exception as e:
                    logger.warning(f"[JIRA-DEVELOPER-{thread_id}] Failed to push to review queue: {e}")

            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[JIRA-DEVELOPER-{thread_id}] Completed {issue_key} in {elapsed_time:.2f}s - {len(generated_files)} files, {tokens_used} tokens")

            return {
                "success": True,
                "generated_files": generated_files,
                "tokens_used": tokens_used,
                "elapsed_time": elapsed_time
            }

        except Exception as e:
            logger.error(f"[JIRA-DEVELOPER-{thread_id}] Failed for {issue_key}: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": {},
                "tokens_used": 0
            }

    def correct_code_for_jira_issue(
        self,
        generated_files: Dict[str, str],
        feedback: list,
        issue_data: Dict[str, Any],
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Correct code for a JIRA issue based on feedback

        Args:
            generated_files: Previously generated files
            feedback: List of feedback items
            issue_data: JIRA issue data
            thread_id: Optional thread identifier

        Returns:
            {
                "success": bool,
                "generated_files": Dict[str, str],
                "tokens_used": int,
                "error": Optional[str]
            }
        """
        if not thread_id:
            thread_id = f"JIRA-DEVELOPER-CORRECT-{threading.current_thread().ident}"

        issue_key = issue_data.get('key', 'UNKNOWN')

        try:
            logger.info(f"[JIRA-DEVELOPER-{thread_id}] Correcting code for {issue_key}...")

            context = {
                "issue_data": issue_data,
                "identifier": issue_key,
                "file_types": []  # Can be extracted from generated_files if needed
            }

            result = self.core_developer.correct_code(
                generated_files=generated_files,
                feedback=feedback,
                context=context,
                thread_id=thread_id
            )

            if result.get("success"):
                corrected_files = result.get("generated_files", {})
                tokens_used = result.get("tokens_used", 0)

                # Save corrected files
                self._save_files_locally(corrected_files, issue_key)
                self._store_to_mongodb(issue_key, tokens_used)
                self._log_to_ui(issue_key, len(corrected_files), thread_id)

                logger.info(f"[JIRA-DEVELOPER-{thread_id}] Correction completed for {issue_key}")

            return result

        except Exception as e:
            logger.error(f"[JIRA-DEVELOPER-{thread_id}] Correction failed for {issue_key}: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": generated_files,
                "tokens_used": 0
            }