"""
Core Assembler Agent - Modular and Reusable
This is a standalone assembler that can be integrated into any workflow.
It accepts subtasks and requirements, outputs deployment documents.

Usage:
    from agents.core_assembler_agent import CoreAssemblerAgent

    assembler = CoreAssemblerAgent(config)
    result = assembler.assemble(
        subtasks=[...],
        requirements="Your project requirements",
        context={"key": "value"}
    )
    # Returns: {"success": True, "document": {...}, "markdown": "...", "tokens_used": 100}
"""
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class CoreAssemblerAgent:
    """
    Core Assembler Agent - Framework-agnostic document assembly logic
    Can be used in any LangGraph workflow or standalone
    """

    def __init__(self, config=None):
        """Initialize the core assembler"""
        self.config = config or {}

        # Lazy import to avoid circular dependencies
        from tools.prompt_loader import PromptLoader
        self.prompt_loader = PromptLoader("prompts")

        # Build the graph
        self.graph = self._build_graph()
        logger.debug("Core Assembler Agent initialized (modular version)")

    def _build_graph(self):
        """Build the core assembler LangGraph"""
        graph = StateGraph(dict)

        # Add nodes
        graph.add_node("generate_document", self._generate_document_node)
        graph.add_node("handle_error", self._handle_error_node)

        # Define edges
        graph.add_edge(START, "generate_document")
        graph.add_conditional_edges(
            "generate_document",
            self._route_success_or_error,
            {"success": END, "error": "handle_error"}
        )
        graph.add_edge("handle_error", END)

        return graph.compile()

    def _route_success_or_error(self, state: Dict[str, Any]) -> str:
        """Route based on error state"""
        return "error" if state.get("error") else "success"

    def _generate_document_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete deployment document"""
        thread_id = state.get("thread_id", "unknown")
        subtasks = state.get("subtasks", [])
        requirements = state.get("requirements", "")
        context = state.get("context", {})

        logger.info(f"[CORE-ASSEMBLER-{thread_id}] Generating deployment document...")

        try:
            from tools.assembler_tool import generate_deployment_document

            # Convert generic input to issue_data format for tool compatibility
            issue_data = {
                "key": context.get("identifier", "DOC-001"),
                "summary": context.get("title", "Project"),
                "description": requirements,
                **context  # Include any additional context
            }

            result = generate_deployment_document.invoke({
                "issue_data": issue_data,
                "subtasks": subtasks,
                "thread_id": thread_id
            })

            if result.get("success"):
                logger.info(f"[CORE-ASSEMBLER-{thread_id}] Document generated successfully")
                return {
                    "deployment_document": result.get("document"),
                    "markdown": result.get("markdown", ""),
                    "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0)
                }
            else:
                return {"error": result.get("error", "Document generation failed")}

        except Exception as e:
            logger.error(f"[CORE-ASSEMBLER-{thread_id}] Generation failed: {e}")
            return {"error": str(e)}

    def _handle_error_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors in the workflow"""
        thread_id = state.get("thread_id", "unknown")
        error = state.get("error", "Unknown error")
        logger.error(f"[CORE-ASSEMBLER-{thread_id}] Error: {error}")
        return state

    # ==================== PUBLIC API ====================

    def assemble(
        self,
        subtasks: List[Dict[str, Any]],
        requirements: str,
        context: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main assembly method - accepts subtasks and requirements, returns deployment document

        Args:
            subtasks: List of subtasks to assemble into a document
            requirements: Project requirements/description
            context: Additional context (identifier, title, metadata, etc.)
            thread_id: Optional thread identifier for logging

        Returns:
            {
                "success": bool,
                "document": Dict,  # Complete deployment document
                "markdown": str,   # Markdown version of document
                "tokens_used": int,
                "error": Optional[str]
            }
        """
        import threading

        if thread_id is None:
            thread_id = f"ASSEMBLER-{threading.current_thread().ident}"

        context = context or {}
        start_time = datetime.now()

        logger.info(f"[CORE-ASSEMBLER-{thread_id}] Starting document assembly")

        try:
            # Initialize state
            initial_state = {
                "subtasks": subtasks,
                "requirements": requirements,
                "context": context,
                "thread_id": thread_id,
                "deployment_document": None,
                "markdown": None,
                "error": "",
                "tokens_used": 0
            }

            # Execute workflow
            final_state = self.graph.invoke(initial_state)

            duration = (datetime.now() - start_time).total_seconds()

            if final_state.get("error"):
                logger.error(f"[CORE-ASSEMBLER-{thread_id}] Assembly failed: {final_state.get('error')}")
                return {
                    "success": False,
                    "error": final_state.get("error"),
                    "tokens_used": final_state.get("tokens_used", 0),
                    "document": None,
                    "markdown": ""
                }

            logger.info(f"[CORE-ASSEMBLER-{thread_id}] Assembly completed in {duration:.1f}s")

            return {
                "success": True,
                "document": final_state.get("deployment_document"),
                "markdown": final_state.get("markdown", ""),
                "tokens_used": final_state.get("tokens_used", 0),
                "error": None
            }

        except Exception as e:
            logger.error(f"[CORE-ASSEMBLER-{thread_id}] Assembly execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tokens_used": 0,
                "document": None,
                "markdown": ""
            }

    def create_langgraph_node(self):
        """
        Returns a LangGraph node function that can be added to any workflow

        Usage in another workflow:
            assembler = CoreAssemblerAgent(config)
            workflow.add_node("assemble", assembler.create_langgraph_node())
        """
        def assembler_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """LangGraph node wrapper for core assembler"""
            subtasks = state.get("approved_subtasks") or state.get("subtasks", [])
            requirements = state.get("requirements") or state.get("description", "")
            context = state.get("context", {})
            thread_id = state.get("thread_id", "unknown")

            result = self.assemble(
                subtasks=subtasks,
                requirements=requirements,
                context=context,
                thread_id=thread_id
            )

            # Update state with assembly results
            return {
                "assemble_result": result,
                "deployment_document": result.get("document"),
                "markdown": result.get("markdown", ""),
                "assembler_tokens": result.get("tokens_used", 0),
                "tokens_used": state.get("tokens_used", 0) + result.get("tokens_used", 0),
                "error": result.get("error") if not result.get("success") else state.get("error")
            }

        return assembler_node
