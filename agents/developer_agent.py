# Updated agents/developer_agent.py
"""
Developer Agent - LangGraph Sub-graph for Code Generation
- Uses memory for coherent multi-file generation
- Generates complete project code as single connected file
"""
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict
import re
from dotenv import load_dotenv
from pymongo import MongoClient
from tools.developer_tool import generate_code_files, correct_code_with_feedback, \
    save_files_locally
from tools.prompt_loader import PromptLoader
from tools.utils import log_activity
from graph.developer_graph import build_developer_graph, DeveloperState  # NEW: Import the graph builder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeveloperAgent:
    """LangGraph-based Developer Agent for Code Generation"""

    def __init__(self, config):
        self.config = config
        self.prompt_loader = PromptLoader("prompts")

        # Tools for developer (removed merge_subtasks_to_prompts since using document directly)
        self.tools = [
            generate_code_files,
            correct_code_with_feedback
        ]

        # Initialize LangGraph sub-graph
        self.graph = build_developer_graph()  # CHANGED: Use imported builder instead of self._build_graph()

        # Global Project Memory
        self.global_project_memory = {
            "all_generated_files": {},  # filename -> {"metadata": {}, "content": str}
            "file_relationships": {},  # filename -> list of imported/referenced files
            "cumulative_mistakes": [],  # list of unique mistakes
            "resolved_mistakes": [],  # list of resolved mistakes
            "issue_history": []  # list of processed issue keys
        }

        # NEW: Initialize MongoDB
        load_dotenv()
        self.mongo_client = None
        self.mongo_collection = None
        self._initialize_mongodb()

        logger.info("Developer Agent initialized")

    def _initialize_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            conn_str = os.getenv("MONGODB_CONNECTION_STRING")
            if not conn_str:
                logger.warning("MONGODB_CONNECTION_STRING not set - Developer feedback storage disabled")
                return

            self.mongo_client = MongoClient(conn_str)
            db_name = os.getenv("MONGODB_PERFORMANCE_DATABASE", "aristotle_performance")
            coll_name = os.getenv("MONGODB_AGENT_PERFORMANCE", "agent_performance")

            db = self.mongo_client[db_name]
            self.mongo_collection = db[coll_name]
            logger.info(f"Developer MongoDB ready - Database: {db_name}, Collection: {coll_name}")
        except Exception as e:
            logger.error(f"Developer MongoDB init failed: {e}")
            self.mongo_collection = None

    @staticmethod
    def _store_to_mongodb(issue_key: str, tokens_used: int = 0):
        """Store developer data in MongoDB"""
        load_dotenv()  # Ensure env is loaded
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
            logger.info(f"[DEVELOPER-{thread_id}] Starting code generation...")

            initial_state = DeveloperState(
                deployment_document=deployment_document,
                thread_id=thread_id,
                generated_files={},
                feedback=feedback,  # NEW: Pass feedback to state
                error="",
                global_project_memory=self.global_project_memory.copy(),
                related_files={},
                current_iteration_feedback=[],
                issue_data=issue_data or {},
                persistent_memory=self.global_project_memory.copy(),
                memory_updated=False,
                tokens_used=0  # NEW: Initialize tokens
            )

            final_state = self.graph.invoke(initial_state)

            if final_state.get("error"):
                return {"success": False, "error": final_state["error"]}

            generated_files = final_state.get("generated_files", {})

            # NEW: If review_queue provided, push files for parallel review
            if review_queue is not None:
                try:
                    review_queue.put({
                        "files": generated_files,
                        "issue_data": issue_data,
                        "thread_id": thread_id
                    })
                    logger.info(f"[DEVELOPER-{thread_id}] Pushed files to review queue for parallel processing")
                except Exception as e:
                    logger.warning(f"[DEVELOPER-{thread_id}] Failed to push to review queue: {e}")

            return {
                "success": True,
                "generated_files": generated_files,
                "tokens_used": final_state.get("tokens_used", 0)
            }

        except Exception as e:
            logger.error(f"[DEVELOPER-{thread_id}] Code generation failed: {e}")
            return {"success": False, "error": str(e)}
