# C:\Users\Rahul\Agent-flow\agents\core_developer_agent.py
"""
Core Developer Agent - Modular and Reusable
This is a standalone developer that can be integrated into any workflow.
It accepts deployment documents/requirements and outputs generated code files.

Usage:
    from agents.core_developer_agent import CoreDeveloperAgent

    developer = CoreDeveloperAgent(config)
    result = developer.develop(
        deployment_document=doc,
        context={"identifier": "TASK-001"},
        feedback=None
    )
    # Returns: {"success": True, "generated_files": {...}, "tokens_used": 100}
"""
import logging
import threading
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class CoreDeveloperAgent:
    """
    Core Developer Agent - Framework-agnostic code generation logic
    Can be used in any LangGraph workflow or standalone
    """

    def __init__(self, config=None):
        """Initialize the core developer"""
        self.config = config or {}

        # Lazy import to avoid circular dependencies
        from tools.prompt_loader import PromptLoader
        self.prompt_loader = PromptLoader("prompts")

        # NEW: Remove global_project_memory init - now handled by LangGraph checkpointer in the graph

        # Build the graph
        from graph.developer_graph import build_developer_graph
        self.graph = build_developer_graph()

        logger.debug("Core Developer Agent initialized (modular version)")

    def develop(
        self,
        deployment_document: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        feedback: Optional[List[str]] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main development method - accepts deployment document and generates code

        Args:
            deployment_document: Document containing file structure, specs, implementation plan
            context: Additional context (identifier, issue_data, project info, etc.)
            feedback: Optional feedback for code correction
            thread_id: Optional thread identifier for logging

        Returns:
            {
                "success": bool,
                "generated_files": Dict[str, str],  # filename -> code content
                "tokens_used": int,
                "error": Optional[str]
            }
        """
        if thread_id is None:
            thread_id = f"DEVELOPER-{threading.current_thread().ident}"

        context = context or {}
        issue_data = context.get("issue_data", {})
        review_queue = context.get("review_queue", None)  # Extract queue from context

        try:
            logger.info(f"[CORE-DEVELOPER-{thread_id}] Starting code generation...")

            # Import state type
            from graph.developer_graph import DeveloperState

            # Prepare initial state (WITHOUT review_queue - it cannot be serialized)
            # NEW: Remove manual memory copy - LangGraph checkpointer handles persistence
            # Provide defaults for memory fields to avoid KeyErrors
            initial_state = DeveloperState(
                deployment_document=deployment_document,
                thread_id=thread_id,
                generated_files={},
                feedback=feedback,
                error="",
                global_project_memory={
                    "all_generated_files": {},  # Default empty dict
                    "file_relationships": {},  # Default empty dict
                    "cumulative_mistakes": [],  # Default empty list
                    "resolved_mistakes": [],  # Default empty list
                    "issue_history": []  # Default empty list
                },
                related_files={},
                current_iteration_feedback=[],
                issue_data=issue_data,
                persistent_memory={
                    "all_generated_files": {},  # Default empty dict
                    "file_relationships": {},  # Default empty dict
                    "cumulative_mistakes": [],  # Default empty list
                    "resolved_mistakes": [],  # Default empty list
                    "issue_history": []  # Default empty list
                },
                memory_updated=False,
                tokens_used=0,
                files_to_generate=[]
            )

            # Execute the graph with configurable for memory isolation
            # NEW: Pass configurable with thread_id for LangGraph memory
            final_state = self.graph.invoke(initial_state, {"configurable": {"thread_id": thread_id}})

            # Check for errors
            if final_state.get("error"):
                return {
                    "success": False,
                    "error": final_state["error"],
                    "generated_files": {},
                    "tokens_used": final_state.get("tokens_used", 0)
                }

            # NEW: No need to update persistent_memory manually - checkpointer already saved it
            # Access from final_state if needed: self.global_project_memory = final_state.get("persistent_memory", {})

            generated_files = final_state.get("generated_files", {})

            # Handle review_queue AFTER graph execution (outside of state)
            if review_queue is not None:
                try:
                    review_queue.put({
                        "files": generated_files,
                        "issue_data": issue_data,
                        "thread_id": thread_id
                    })
                    logger.info(f"[CORE-DEVELOPER-{thread_id}] Pushed {len(generated_files)} files to review queue")
                except Exception as e:
                    logger.warning(f"[CORE-DEVELOPER-{thread_id}] Failed to push to review queue: {e}")

            logger.info(f"[CORE-DEVELOPER-{thread_id}] Generated {len(generated_files)} files successfully")

            return {
                "success": True,
                "generated_files": generated_files,
                "tokens_used": final_state.get("tokens_used", 0)
            }

        except Exception as e:
            logger.error(f"[CORE-DEVELOPER-{thread_id}] Development failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": {},
                "tokens_used": 0
            }

    def correct_code(
        self,
        generated_files: Dict[str, str],
        feedback: List[str],
        context: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Correct previously generated code based on feedback

        Args:
            generated_files: Previously generated files
            feedback: List of feedback/corrections to apply
            context: Additional context
            thread_id: Optional thread identifier

        Returns:
            {
                "success": bool,
                "generated_files": Dict[str, str],
                "tokens_used": int,
                "error": Optional[str]
            }
        """
        if thread_id is None:
            thread_id = f"DEVELOPER-CORRECT-{threading.current_thread().ident}"

        context = context or {}

        try:
            logger.info(f"[CORE-DEVELOPER-{thread_id}] Correcting {len(generated_files)} files with {len(feedback)} feedback items...")

            from tools.developer_tool import correct_code_with_feedback

            result = correct_code_with_feedback.invoke({
                "generated_files": generated_files,
                "feedback": feedback,
                "file_types": context.get("file_types", []),
                "issue_key": context.get("identifier", "UNKNOWN"),
                "thread_id": thread_id
            })

            if result.get("success"):
                return {
                    "success": True,
                    "generated_files": result.get("generated_files", {}),
                    "tokens_used": result.get("tokens_used", 0)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Code correction failed"),
                    "generated_files": generated_files,
                    "tokens_used": result.get("tokens_used", 0)
                }

        except Exception as e:
            logger.error(f"[CORE-DEVELOPER-{thread_id}] Correction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": generated_files,
                "tokens_used": 0
            }

    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Get current state of project memory"""
        # NEW: With checkpointer, memory is per-thread; this method may need adaptation for specific thread_id
        # For simplicity, return empty or implement query if needed
        logger.warning("get_memory_snapshot not fully supported with checkpointer - use graph state query")
        return {}

    def update_memory(self, memory_update: Dict[str, Any]):
        """Update project memory with new information"""
        # NEW: Manual update not needed with checkpointer; log warning or remove method
        logger.warning("update_memory deprecated with LangGraph checkpointer - use state updates in graph")

    def reset_memory(self):
        """Reset project memory to initial state"""
        # NEW: To reset, clear checkpointer data or use new thread_id
        logger.info("Reset not directly supported - use new thread_id for fresh state")