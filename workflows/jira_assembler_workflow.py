"""
JIRA-Specific Assembler Workflow
This file contains JIRA-specific integration logic that uses the CoreAssemblerAgent.
It handles:
- JIRA issue data extraction
- MongoDB storage for JIRA issues
- UI integration for JIRA workflow
- Local markdown file storage

This keeps JIRA-specific logic separate from the core assembly logic.
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pymongo import MongoClient

from agents.core_assembler_agent import CoreAssemblerAgent
from config.settings import config as app_config

logger = logging.getLogger(__name__)


class JiraAssemblerWorkflow:
    """
    JIRA-specific workflow wrapper for CoreAssemblerAgent
    Handles JIRA issue processing, MongoDB storage, and UI integration
    """

    def __init__(self, config):
        self.config = config
        self.core_assembler = CoreAssemblerAgent(config)

        # Initialize MongoDB for JIRA-specific storage
        self.mongo_client = None
        self.mongo_collection = None
        self._initialize_mongodb()

        logger.info("JIRA Assembler Workflow initialized")

    def _initialize_mongodb(self):
        """Initialize MongoDB connection for JIRA feedback storage"""
        try:
            conn_str = app_config.MONGODB_CONNECTION_STRING
            if not conn_str:
                logger.warning("MONGODB_CONNECTION_STRING not set - JIRA assembler storage disabled")
                return

            self.mongo_client = MongoClient(conn_str)
            db_name = app_config.MONGODB_DATABASE
            coll_name = app_config.ASSEMBLER_FEEDBACK
            db = self.mongo_client[db_name]
            self.mongo_collection = db[coll_name]

            logger.info(f"JIRA Assembler MongoDB ready - Collection: {coll_name}")
        except Exception as e:
            logger.error(f"JIRA Assembler MongoDB init failed: {e}")
            self.mongo_collection = None

    def _store_to_mongodb(self, issue_key: str, deployment_doc: Dict, tokens_used: int):
        """Store JIRA-specific deployment document to MongoDB"""
        if self.mongo_collection is None:
            logger.warning("MongoDB not available - Skipping JIRA assembler storage")
            return

        try:
            document = {
                "agent_type": "assembler",
                "issue_key": issue_key,
                "deployment_document": deployment_doc,
                "timestamp": datetime.now(),
                "date": datetime.now().date().isoformat(),
                "llm_model": app_config.ASSEMBLER_LLM_MODEL or "unknown",
                "tokens_used": tokens_used
            }

            result = self.mongo_collection.insert_one(document)
            logger.info(f"[JIRA-ASSEMBLER] Stored document for {issue_key} in MongoDB: ID {result.inserted_id}")
        except Exception as e:
            logger.error(f"[JIRA-ASSEMBLER] Failed to store in MongoDB: {e}")

    def _save_markdown_locally(self, issue_key: str, markdown_content: str):
        """Save markdown document to local folder"""
        try:
            local_folder = "deployment_documents"
            os.makedirs(local_folder, exist_ok=True)
            md_path = os.path.join(local_folder, f"{issue_key}.md")

            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            logger.info(f"[JIRA-ASSEMBLER] Saved markdown to {md_path}")
        except Exception as e:
            logger.error(f"[JIRA-ASSEMBLER] Failed to save markdown: {e}")

    def _log_to_ui(self, issue_key: str, deployment_doc: Dict):
        """Log assembly results to UI"""
        try:
            import core.router
            import uuid

            # Extract document sections for UI display
            document_sections = []

            # Project Overview
            project_overview = deployment_doc.get("project_overview", {})
            if project_overview:
                desc = project_overview.get("description", "")
                proj_type = project_overview.get("project_type", "")
                arch = project_overview.get("architecture", "")
                content = f"Type: {proj_type}\nArchitecture: {arch}\n\n{desc[:200]}..." if len(desc) > 200 else f"Type: {proj_type}\nArchitecture: {arch}\n\n{desc}"
                document_sections.append({"title": "Project Overview", "content": content})

            # File Structure
            file_structure = deployment_doc.get("file_structure", {})
            if file_structure and file_structure.get("files"):
                files = file_structure.get("files", [])
                file_list = "\n".join([
                    f"• {f.get('filename', '')} ({f.get('type', '')}): {f.get('description', '')[:80]}..."
                    if len(f.get('description', '')) > 80
                    else f"• {f.get('filename', '')} ({f.get('type', '')}): {f.get('description', '')}"
                    for f in files[:5]
                ])
                if len(files) > 5:
                    file_list += f"\n... and {len(files) - 5} more files"
                document_sections.append({"title": f"File Structure ({len(files)} files)", "content": file_list})

            # Implementation Plan
            impl_plan = deployment_doc.get("implementation_plan", {})
            if impl_plan:
                phases = impl_plan.get("phases", [])
                if phases:
                    phase_text = "\n".join([f"Phase {i+1}: {p.get('name', 'Unnamed')}" for i, p in enumerate(phases[:3])])
                    if len(phases) > 3:
                        phase_text += f"\n... and {len(phases) - 3} more phases"
                    document_sections.append({"title": "Implementation Plan", "content": phase_text})

            # Technical Specifications
            tech_specs = deployment_doc.get("technical_specifications", {})
            if tech_specs:
                spec_count = len(tech_specs)
                spec_files = list(tech_specs.keys())[:3]
                spec_text = f"Specifications for {spec_count} file(s):\n" + "\n".join([f"• {f}" for f in spec_files])
                if spec_count > 3:
                    spec_text += f"\n... and {spec_count - 3} more"
                document_sections.append({"title": "Technical Specifications", "content": spec_text})

            core.router.safe_activity_log({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "agent": "AssemblerAgent",
                "action": "Document Assembly Completed",
                "details": f"Created deployment document for {issue_key}",
                "status": "success",
                "issueId": issue_key,
                "documentSections": document_sections
            })

            logger.info(f"[JIRA-ASSEMBLER] UI Log: {issue_key} - Document created with {len(document_sections)} sections")
        except Exception as e:
            logger.warning(f"[JIRA-ASSEMBLER] Failed to log to UI: {e}")

    def create_deployment_document(
        self,
        approved_subtasks: List[Dict[str, Any]],
        issue_data: Dict[str, Any],
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create deployment document for JIRA issue using CoreAssemblerAgent

        Args:
            approved_subtasks: List of approved subtasks from planner
            issue_data: JIRA issue data containing key, summary, description, etc.
            thread_id: Optional thread identifier

        Returns:
            {
                "success": bool,
                "deployment_document": Dict,
                "markdown": str,
                "tokens_used": int,
                "error": Optional[str]
            }
        """
        if not thread_id:
            thread_id = f"JIRA-ASSEMBLER-{os.getpid()}"

        issue_key = issue_data.get('key', 'UNKNOWN')
        start_time = datetime.now()

        logger.info(f"[JIRA-ASSEMBLER-{thread_id}] Starting document assembly for JIRA issue {issue_key}")

        try:
            # Extract JIRA-specific data
            requirements = issue_data.get('description', '')
            context = {
                "identifier": issue_key,
                "title": issue_data.get('summary', ''),
                "project": issue_data.get('project', {}),
                "priority": issue_data.get('priority', ''),
                "issue_type": issue_data.get('issuetype', ''),
                # Include any additional JIRA fields
                **{k: v for k, v in issue_data.items() if k not in ['description', 'key', 'summary']}
            }

            # Call core assembler
            result = self.core_assembler.assemble(
                subtasks=approved_subtasks,
                requirements=requirements,
                context=context,
                thread_id=thread_id
            )

            duration = (datetime.now() - start_time).total_seconds()

            if result.get("success"):
                deployment_doc = result.get("document", {})
                markdown = result.get("markdown", "")
                tokens = result.get("tokens_used", 0)

                # Store to MongoDB (JIRA-specific)
                self._store_to_mongodb(
                    issue_key=issue_key,
                    deployment_doc=deployment_doc,
                    tokens_used=tokens
                )

                # Save markdown locally (JIRA-specific)
                self._save_markdown_locally(issue_key, markdown)

                # Log to UI (JIRA-specific)
                self._log_to_ui(issue_key, deployment_doc)

                logger.info(f"[JIRA-ASSEMBLER-{thread_id}] Completed for {issue_key} in {duration:.1f}s")

                return {
                    "success": True,
                    "deployment_document": deployment_doc,
                    "markdown": markdown,
                    "tokens_used": tokens
                }
            else:
                logger.error(f"[JIRA-ASSEMBLER-{thread_id}] Assembly failed for {issue_key}: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error"),
                    "tokens_used": result.get("tokens_used", 0)
                }

        except Exception as e:
            logger.error(f"[JIRA-ASSEMBLER-{thread_id}] Exception for {issue_key}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tokens_used": 0
            }

    def create_langgraph_node(self):
        """
        Returns a LangGraph node function for JIRA workflow integration

        Usage:
            jira_assembler = JiraAssemblerWorkflow(config)
            workflow.add_node("assemble_document", jira_assembler.create_langgraph_node())
        """
        def jira_assembler_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """LangGraph node wrapper for JIRA assembler"""
            approved_subtasks = state.get("approved_subtasks", [])
            issue_data = state.get("current_issue", {})
            thread_id = state.get("thread_id", "unknown")

            result = self.create_deployment_document(
                approved_subtasks=approved_subtasks,
                issue_data=issue_data,
                thread_id=thread_id
            )

            return {
                "assemble_result": result,
                "deployment_document": result.get("deployment_document"),
                "markdown": result.get("markdown", ""),
                "assembler_tokens": result.get("tokens_used", 0),
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0),
                "error": result.get("error") if not result.get("success") else state.get("error")
            }

        return jira_assembler_node
