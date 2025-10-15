"""
Assembler Agent - Creates Comprehensive Deployment Documents
Bridges the gap between Planner's subtasks and Developer's code generation
"""
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from pymongo import MongoClient

from tools.assembler_tool import (
    generate_deployment_document  # Only keep this tool
)
from tools.prompt_loader import PromptLoader
from graph.assembler_graph import build_assembler_graph, AssemblerState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AssemblerAgent:
    """LangGraph-based Assembler Agent for Deployment Document Creation"""

    def __init__(self, config):
        self.config = config
        self.prompt_loader = PromptLoader("prompts")

        # Tools for assembler (removed validate_deployment_document)
        self.tools = [
            generate_deployment_document
        ]

        # Initialize MongoDB
        load_dotenv()
        self.mongo_client = None
        self.mongo_collection = None
        self._initialize_mongodb()

        # Initialize LangGraph sub-graph
        self.graph = build_assembler_graph()

        logger.info("Assembler Agent initialized")

    def _initialize_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            conn_str = os.getenv("MONGODB_CONNECTION_STRING")
            if not conn_str:
                logger.warning("MONGODB_CONNECTION_STRING not set - Assembler storage disabled")
                return

            self.mongo_client = MongoClient(conn_str)
            db_name = os.getenv("MONGODB_DATABASE", "code_review")
            coll_name = os.getenv("ASSEMBLER_FEEDBACK", "assembler-documents")

            db = self.mongo_client[db_name]
            self.mongo_collection = db[coll_name]

            logger.info(f"Assembler MongoDB ready - Collection: {coll_name}")
        except Exception as e:
            logger.error(f"Assembler MongoDB init failed: {e}")
            self.mongo_collection = None

    @staticmethod
    def _store_to_mongodb(issue_key: str, deployment_doc: Dict, tokens_used: int = 0):
        """Store deployment document in MongoDB"""
        load_dotenv()
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        if not conn_str:
            logger.warning("MongoDB not available - Skipping assembler storage")
            return

        try:
            mongo_client = MongoClient(conn_str)
            db_name = os.getenv("MONGODB_PERFORMANCE_DATABASE", "aristotle_performance")
            coll_name = os.getenv("MONGODB_AGENT_PERFORMANCE", "agent_performance")
            mongo_collection = mongo_client[db_name][coll_name]

            document = {
                "agent_type": "assembler",
                "issue_key": issue_key,
                "deployment_document": deployment_doc,
                "timestamp": datetime.now(),
                "date": datetime.now().date().isoformat(),
                "llm_model": os.getenv("ASSEMBLER_LLM_MODEL", "unknown"),
                "tokens_used": tokens_used
            }

            result = mongo_collection.insert_one(document)
            logger.info(f"[ASSEMBLER] Stored document for {issue_key} in MongoDB: ID {result.inserted_id}")
        except Exception as e:
            logger.error(f"[ASSEMBLER] Failed to store document in MongoDB: {e}")

    def create_deployment_document(
            self,
            approved_subtasks: List[Dict[str, Any]],
            issue_data: Dict[str, Any],
            thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create comprehensive deployment document from approved subtasks

        Args:
            approved_subtasks: List of approved subtasks from Planner
            issue_data: Original JIRA issue data
            thread_id: Thread identifier

        Returns:
            Dict with deployment_document and metadata
        """
        if not thread_id:
            thread_id = f"ASSEMBLER-{os.getpid()}"

        try:
            logger.info(f"[ASSEMBLER-{thread_id}] Creating deployment document...")

            initial_state = AssemblerState(
                issue_data=issue_data,
                approved_subtasks=approved_subtasks,
                thread_id=thread_id,
                deployment_document=None,
                markdown=None,  # Add markdown to initial state
                error="",
                tokens_used=0
            )

            final_state = self.graph.invoke(initial_state)

            if final_state.get("error"):
                return {"success": False, "error": final_state["error"]}

            # Store to MongoDB
            deployment_doc = final_state.get("deployment_document", {})
            self._store_to_mongodb(
                issue_key=issue_data.get('key', 'UNKNOWN'),
                deployment_doc=deployment_doc,
                tokens_used=final_state.get("tokens_used", 0)
            )

            return {
                "success": True,
                "deployment_document": deployment_doc,
                "markdown": final_state.get("markdown", ""),  # Include markdown in return
                "tokens_used": final_state.get("tokens_used", 0)
            }

        except Exception as e:
            logger.error(f"[ASSEMBLER-{thread_id}] Document creation failed: {e}")
            return {"success": False, "error": str(e)}

